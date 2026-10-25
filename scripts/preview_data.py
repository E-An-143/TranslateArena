"""Explicit QA fixtures; never used by a normal application launch or live translation."""
from arena.models import AgentConfig, TranslationRecord
from arena.services.judge_scoring import MULTI_DIMENSIONS
from arena.services.judge_validation import validate_judge

SOURCE = "好的翻译不只是转换词语，而是让同一个想法在另一种语言里自然生长。我们希望保留原文的事实、语气与细微差别，同时让读者忘记这是一篇译文。"


def install_preview(bridge):
    configs = [AgentConfig(id="A",route="literal",cultural_direction="foreignizing"),
               AgentConfig(id="B",route="free",cultural_direction="foreignizing"),
               AgentConfig(id="C",route="free",cultural_direction="domesticating")]
    record = TranslationRecord(SOURCE,"en",configs,demo=True)
    texts = {
        "A": "A good translation is more than converting words. It allows the same idea to grow naturally in another language. We aim to preserve the facts, tone, and subtle nuances of the original, while making readers forget that they are reading a translation.",
        "B": "Good translation goes beyond replacing words: it lets an idea take root naturally in another language. Our aim is to preserve the original’s facts, tone, and nuances, while making the writing feel as though it were never translated.",
        "C": "A good translation does more than change the words. It gives the same idea a natural home in another language. We want to preserve the original’s facts, tone, and nuances—and make readers forget they’re reading a translation.",
    }
    for key,text in texts.items():
        candidate=record.candidates[key]
        candidate.text=candidate.preview=text
        candidate.reasoning=f"示例 API 思考内容 {key}：保留事实与细微差别，结合目标语言调整表达"
        candidate.status="success"
        candidate.usage={"total_tokens":350}
    record.judge=validate_judge({
        "candidates": {key: {dim: score for dim in MULTI_DIMENSIONS}
                       for key, score in {"A":8.7,"B":9.3,"C":9.0}.items()},
        "final_translation":texts["B"],
    }, texts)
    record.final=record.judge["final_translation"]; record.stage="completed"; record.elapsed=6.8; record.call_count=4
    record.judge_latency=1.9; record.judge_usage={"total_tokens":850}
    bridge.source=SOURCE; bridge.target_language="en"
    bridge.draft_agents=[a.__dict__.copy() for a in configs]
    bridge.record=record.to_dict()
    bridge.db.save_record(bridge.record)
    bridge._refresh()
