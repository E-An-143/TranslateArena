from dataclasses import dataclass, field
from typing import Callable, Protocol
from arena.notifications import notification_text


class ProviderError(Exception):
    """User-facing, credential-free error. Never include raw response bodies."""
    def __init__(self, message, *, requests=1, usage=None, latency=0.0):
        super().__init__(notification_text(message))
        self.requests = requests
        self.usage = usage or {}
        self.latency = latency


@dataclass
class Completion:
    text: str
    usage: dict = field(default_factory=dict)
    latency: float = 0.0
    requests: int = 1
    reasoning: str = ""


@dataclass(frozen=True)
class CompletionDelta:
    reasoning: str = ""
    text: str = ""


class BaseProvider(Protocol):
    async def complete(self, *, key: str, model: str, messages: list[dict],
                       json_output: bool = False) -> Completion: ...

    async def stream_complete(self, *, key: str, model: str, messages: list[dict],
                              on_delta: Callable[[CompletionDelta], None],
                              json_output: bool = False) -> Completion: ...

    async def test_connection(self, key: str) -> list[str]: ...
