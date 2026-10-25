import json
import math

from arena.services.judge_scoring import MULTI_DIMENSIONS, ranking_key, weighted_score


class JudgeFormatError(ValueError):
    pass


def extract_json(text: str) -> dict:
    decoder = json.JSONDecoder()
    # Tolerate fences and commentary, without evaluating Python or executing content.
    for index, char in enumerate(text):
        if char == "{":
            try:
                data, _ = decoder.raw_decode(text[index:])
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                continue
    raise JudgeFormatError("未找到有效的 JSON 对象")


def score(value) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 10:
        raise JudgeFormatError("评分必须在 0–10 之间")
    return round(float(value), 1)


def validate_judge(data: dict, candidates: dict[str, str]) -> dict:
    if not candidates:
        raise JudgeFormatError("缺少候选译文")
    cards = data.get("candidates")
    if not isinstance(cards, dict):
        raise JudgeFormatError("缺少多维评分")
    if set(cards) != set(candidates):
        raise JudgeFormatError("候选评分与提供的译文不一致")
    clean = {}
    for key in candidates:
        card = cards.get(key)
        if not isinstance(card, dict):
            raise JudgeFormatError("候选评分不完整")
        if any(dim not in card for dim in MULTI_DIMENSIONS):
            raise JudgeFormatError("候选维度评分不完整")
        item = {dim: None if dim == "terminology" and card[dim] is None else score(card[dim])
                for dim in MULTI_DIMENSIONS}
        clean[key] = item
    if len({card["terminology"] is None for card in clean.values()}) != 1:
        raise JudgeFormatError("术语维度的适用性必须对全部候选一致")
    final = data.get("final_translation")
    if not isinstance(final, str) or not final.strip():
        raise JudgeFormatError("缺少最终译文")
    winner = max(clean, key=lambda key: ranking_key(clean[key]))
    # Select from the original candidates so model edits or an inconsistent selection cannot alter the final.
    return {"winner": winner, "candidates": clean,
            "scores": {key: float(weighted_score(card)) for key, card in clean.items()},
            "final_translation": candidates[winner]}

