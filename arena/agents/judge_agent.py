from arena.config import DEFAULT_MODEL
from arena.providers.base_provider import Completion, ProviderError
from arena.services.judge_validation import JudgeFormatError, extract_json, validate_judge
from arena.services.prompt_builder import judge_messages


class JudgeAgent:
    def __init__(self, provider, key):
        self.provider, self.key = provider, key

    async def judge(self, record, candidates, on_delta=None, on_attempt=None):
        messages = judge_messages(record, candidates)
        usage, latency, requests = {}, 0.0, 0
        for attempt in range(2):
            if on_attempt:
                on_attempt(attempt + 1)
            try:
                response = await self.provider.stream_complete(key=self.key, model=DEFAULT_MODEL,
                    messages=messages, json_output=True, on_delta=on_delta or (lambda _: None))
            except ProviderError as exc:
                exc.requests += requests
                exc.latency += latency
                exc.usage = {name: usage.get(name, 0) + exc.usage.get(name, 0)
                             for name in usage.keys() | exc.usage.keys()}
                raise
            requests += response.requests
            latency += response.latency
            for key, value in response.usage.items():
                usage[key] = usage.get(key, 0) + value
            try:
                verdict = validate_judge(extract_json(response.text), candidates)
                return verdict, Completion(response.text, usage, latency, requests, response.reasoning)
            except JudgeFormatError as exc:
                if attempt == 1:
                    raise ProviderError("裁决返回的格式仍不完整。候选译文已保留，可重新生成译文后评审。",
                                        requests=requests, usage=usage, latency=latency) from None
                messages += [{"role": "assistant", "content": response.text},
                             {"role": "user", "content": "Repair the JSON only. Validation failed: " + str(exc) +
                              ". Return the complete object in the requested schema with every candidate. Do not change facts."}]
        raise RuntimeError("Unreachable")
