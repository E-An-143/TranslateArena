"""DeepSeek adapter. UI never handles HTTP; requests remain cancellable."""
import asyncio
import json
import logging
import random
import time

import httpx

from .base_provider import Completion, CompletionDelta, ProviderError
from arena.config import DEFAULT_REASONING_EFFORT, REQUEST_TIMEOUT

BASE_URL = "https://api.deepseek.com"
CONNECT_TIMEOUT = 30
RETRY_STATUSES = (429, 500, 502, 503, 504)


class _InterruptedStream(ProviderError):
    """A stream ended before its terminal event, rather than invalid model output."""


class DeepSeekProvider:
    def __init__(self, timeout: float = REQUEST_TIMEOUT, transport=None, retries: int = 2):
        self.timeout = timeout
        self.transport = transport
        self.retries = retries
        self.on_request = None

    @staticmethod
    def _headers(key):
        if not key or not key.strip():
            raise ProviderError("尚未配置 DeepSeek API Key，请前往设置", requests=0)
        return {"Authorization": "Bearer " + key.strip(), "Content-Type": "application/json"}

    @staticmethod
    def _check_status(code):
        if code in (401, 403):
            raise ProviderError("API Key 无效或没有访问权限，请在设置中检查")
        if code == 402:
            raise ProviderError("DeepSeek 账户余额不足，请检查账户")
        if code == 429:
            raise ProviderError("请求过于频繁，稍后可重试")
        if code >= 500:
            raise ProviderError("DeepSeek 服务暂时不可用，稍后可重试")
        if code >= 400:
            raise ProviderError(f"DeepSeek 拒绝了请求（HTTP {code}），请检查模型与输入长度")

    @staticmethod
    def _retry_delay(response, attempt):
        if response is not None:
            try:
                return min(10, max(0, float(response.headers.get("Retry-After", ""))))
            except ValueError:
                pass
        return min(8, 0.8 * 2 ** attempt + random.random() * 0.3)

    @staticmethod
    def _retryable_network_error(exc):
        return isinstance(exc, (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError))

    @staticmethod
    def _network_error(exc, requests, started):
        if isinstance(exc, httpx.ConnectTimeout):
            message = "连接 DeepSeek 服务器超时，可以单独重试"
        elif isinstance(exc, httpx.TimeoutException):
            message = "等待 DeepSeek 响应超时，已保留预览内容，可以单独重试"
        elif isinstance(exc, httpx.ConnectError):
            message = "无法建立到 DeepSeek 的连接，请检查网络后单独重试"
        elif isinstance(exc, httpx.RemoteProtocolError):
            message = "服务器提前中断连接，已保留预览内容，可以单独重试"
        else:
            message = "连接中断，已保留预览内容，请检查网络后单独重试"
        # Record only the exception class, never headers, keys or raw server errors.
        logging.getLogger("arena").warning("Network request failed kind=%s attempts=%d", type(exc).__name__, requests)
        return ProviderError(message, requests=requests, latency=time.monotonic() - started)

    def _timeout(self):
        return httpx.Timeout(self.timeout, connect=min(CONNECT_TIMEOUT, self.timeout))

    @staticmethod
    def _usage(value):
        if not isinstance(value, dict):
            return {}
        return {k: v for k, v in value.items() if isinstance(v, int) and not isinstance(v, bool) and v >= 0}

    @staticmethod
    def _check_finish(reason):
        if reason == "length":
            raise ProviderError("返回内容达到模型长度上限，请分段翻译，避免使用截断译文")
        if reason not in (None, "stop"):
            raise ProviderError("模型未完整生成译文，已保留预览内容，可以单独重试")

    async def _request(self, method: str, path: str, key: str, payload=None):
        headers = self._headers(key)
        started = time.monotonic()
        # No client is shared across event loops. trust_env=False prevents unintended proxy routing.
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=self._timeout(),
                                     transport=self.transport, trust_env=False) as client:
            for attempt in range(self.retries + 1):
                try:
                    if self.on_request:
                        self.on_request()
                    response = await client.request(method, path, headers=headers, json=payload)
                    code = response.status_code
                    if code in RETRY_STATUSES and attempt < self.retries:
                        await asyncio.sleep(self._retry_delay(response, attempt))
                        continue
                    self._check_status(code)
                    try:
                        return response.json(), attempt + 1
                    except (ValueError, UnicodeError):
                        raise ProviderError("DeepSeek 返回了无法读取的数据，请重试。") from None
                except httpx.HTTPError as exc:
                    if self._retryable_network_error(exc) and attempt < self.retries:
                        logging.getLogger("arena").info("Retrying network request kind=%s attempt=%d", type(exc).__name__, attempt + 1)
                        await asyncio.sleep(self._retry_delay(None, attempt))
                        continue
                    raise self._network_error(exc, attempt + 1, started) from None
                except ProviderError as exc:
                    exc.requests = attempt + 1
                    exc.latency = time.monotonic() - started
                    raise

    @staticmethod
    def _completion_payload(model, messages, *, stream, json_output):
        payload = {"model": model, "messages": messages, "stream": stream,
                   "thinking": {"type": "enabled"}, "reasoning_effort": DEFAULT_REASONING_EFFORT}
        # Leave the output budget to the API's max-effort default; an 8K cap can exhaust on reasoning alone.
        if stream:
            payload["stream_options"] = {"include_usage": True}
        if json_output:
            payload["response_format"] = {"type": "json_object"}
        return payload

    async def complete(self, *, key, model, messages, json_output=False):
        payload = self._completion_payload(model, messages, stream=False, json_output=json_output)
        start = time.monotonic()
        data, requests = await self._request("POST", "/chat/completions", key, payload)
        try:
            choice = data["choices"][0]
            content = choice["message"]["content"]
            self._check_finish(choice.get("finish_reason"))
            if choice.get("finish_reason") != "stop":
                raise ProviderError("DeepSeek 未返回完整结束标记，请重试")
            if not isinstance(content, str) or not content.strip():
                raise ProviderError("模型返回了空内容，请重试。")
            reasoning = choice["message"].get("reasoning_content")
            reasoning = "" if reasoning is None else reasoning
            if not isinstance(reasoning, str):
                raise ProviderError("DeepSeek 返回的思考内容格式不完整，请重试")
            usage = self._usage(data.get("usage"))
        except (KeyError, IndexError, TypeError, AttributeError):
            raise ProviderError("DeepSeek 返回格式不完整，请重试。") from None
        return Completion(content.strip(), usage, time.monotonic() - start, requests, reasoning)

    async def stream_complete(self, *, key, model, messages, on_delta, json_output=False):
        """DeepSeek Chat Completions SSE; reasoning and answer stay separate.

        Official reference: https://api-docs.deepseek.com/guides/thinking_mode/
        A failed or cancelled stream retains its preview but never commits a translation.
        Transient status/network failures are retried before any model output.
        Once reasoning or text arrives, a failed stream is retained for manual retry.
        """
        headers = self._headers(key)
        headers["Accept"] = "text/event-stream"
        payload = self._completion_payload(model, messages, stream=True, json_output=json_output)
        started = time.monotonic()
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=self._timeout(),
                                     transport=self.transport, trust_env=False) as client:
            for attempt in range(self.retries + 1):
                received_content = False

                def forward(delta):
                    nonlocal received_content
                    received_content = received_content or bool(delta.reasoning or delta.text)
                    on_delta(delta)

                try:
                    if self.on_request:
                        self.on_request()
                    async with client.stream("POST", "/chat/completions", headers=headers, json=payload) as response:
                        if response.status_code in RETRY_STATUSES and attempt < self.retries:
                            delay = self._retry_delay(response, attempt)
                        else:
                            self._check_status(response.status_code)
                            return await self._read_stream(response, forward, started, attempt + 1)
                    await asyncio.sleep(delay)
                except httpx.HTTPError as exc:
                    if not received_content and self._retryable_network_error(exc) and attempt < self.retries:
                        logging.getLogger("arena").info("Retrying empty stream kind=%s attempt=%d", type(exc).__name__, attempt + 1)
                        await asyncio.sleep(self._retry_delay(None, attempt))
                        continue
                    raise self._network_error(exc, attempt + 1, started) from None
                except ProviderError as exc:
                    if isinstance(exc, _InterruptedStream) and not received_content and attempt < self.retries:
                        await asyncio.sleep(self._retry_delay(None, attempt))
                        continue
                    exc.requests = attempt + 1
                    exc.latency = time.monotonic() - started
                    raise

    async def _read_stream(self, response, on_delta, started, requests):
        reasoning, content, usage = [], [], {}
        finish_reason = None
        event = []

        def consume(data):
            nonlocal finish_reason, usage
            if data == "[DONE]":
                return True
            try:
                packet = json.loads(data)
                if not isinstance(packet, dict) or "error" in packet:
                    raise ValueError
                usage.update(self._usage(packet.get("usage")))
                choices = packet["choices"]
                if not isinstance(choices, list):
                    raise ValueError
                # Both the current terminal content chunk and legacy usage-only chunks are accepted.
                if not choices:
                    return False
                choice = choices[0]
                delta = choice.get("delta")
                if delta is None:
                    delta = {}
                if not isinstance(delta, dict):
                    raise ValueError
                thought, text = delta.get("reasoning_content"), delta.get("content")
                thought = "" if thought is None else thought
                text = "" if text is None else text
                if not isinstance(thought, str) or not isinstance(text, str):
                    raise ValueError
                if choice.get("finish_reason") is not None:
                    finish_reason = choice["finish_reason"]
                if thought:
                    reasoning.append(thought)
                if text:
                    content.append(text)
                if thought or text:
                    on_delta(CompletionDelta(thought, text))
                return False
            except (ValueError, KeyError, IndexError, TypeError, AttributeError):
                raise ProviderError("DeepSeek 流式返回格式不完整，已保留预览内容，请重试") from None

        async for line in response.aiter_lines():
            if line.startswith("data:"):
                value = line[5:]
                event.append(value[1:] if value.startswith(" ") else value)
            elif not line and event:
                done = consume("\n".join(event))
                event = []
                if done:
                    break
        else:
            # Some transports omit the trailing blank line after [DONE].
            if not event or not consume("\n".join(event)):
                raise _InterruptedStream("翻译连接在完成前中断，已保留预览内容，可以单独重试")
        self._check_finish(finish_reason)
        if finish_reason != "stop":
            raise ProviderError("DeepSeek 未返回完整结束标记，已保留预览内容，请重试")
        text = "".join(content).strip()
        if not text:
            raise ProviderError("模型返回了空译文，已保留思考内容，请重试")
        return Completion(text, usage, time.monotonic() - started, requests, "".join(reasoning))

    async def test_connection(self, key):
        data, _ = await self._request("GET", "/models", key)
        try:
            return [item["id"] for item in data["data"] if isinstance(item.get("id"), str)]
        except (KeyError, TypeError, AttributeError):
            raise ProviderError("连接成功，但模型列表格式无法识别。") from None
