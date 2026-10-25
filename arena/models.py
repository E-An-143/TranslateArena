"""Serializable product models. Credentials are intentionally absent."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from uuid import uuid4
from arena.translation_styles import TRANSLATION_STYLES

AGENT_IDS = ("A", "B", "C")
ROUTES = ("literal", "free")
CULTURAL_DIRECTIONS = ("foreignizing", "domesticating")


@dataclass
class AgentConfig:
    id: str = "A"
    route: str = "literal"
    cultural_direction: str = "foreignizing"
    style: str = "general"

    @classmethod
    def from_dict(cls, value: dict) -> AgentConfig:
        allowed = {f.name for f in fields(cls)}
        data = {k: v for k, v in value.items() if k in allowed}
        # Legacy positions are read only for migration; current data stores a direction.
        if "cultural_direction" not in data:
            legacy_position = value.get("domestication", value.get("freedom"))
            if legacy_position is not None:
                data["cultural_direction"] = "domesticating" if int(legacy_position) >= 50 else "foreignizing"
        result = cls(**data)
        if result.id not in AGENT_IDS:
            raise ValueError("无效的 Agent 标识")
        if result.route not in ROUTES:
            result.route = "literal"
        if result.cultural_direction not in CULTURAL_DIRECTIONS:
            result.cultural_direction = "foreignizing"
        if result.style not in TRANSLATION_STYLES:
            result.style = "general"
        return result


@dataclass
class Settings:
    appearance: str = "light"
    agents: list[AgentConfig] = field(default_factory=lambda: [AgentConfig(id=i) for i in AGENT_IDS])

    @classmethod
    def from_dict(cls, value: dict) -> Settings:
        data = {k: v for k, v in value.items() if k in {f.name for f in fields(cls)} and k != "agents"}
        result = cls(**data)
        agents = {a.get("id"): a for a in value.get("agents", []) if isinstance(a, dict)}
        result.agents = [AgentConfig.from_dict(agents.get(i, {"id": i})) for i in AGENT_IDS]
        if result.appearance not in ("light", "dark"):
            result.appearance = "light"
        return result

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Candidate:
    id: str
    status: str = "queued"
    text: str = ""
    reasoning: str = ""
    preview: str = ""
    error: str = ""
    usage: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict) -> Candidate:
        return cls(**{k: v for k, v in value.items() if k in {f.name for f in fields(cls)}})


@dataclass
class TranslationRecord:
    source: str
    target_language: str
    agents: list[AgentConfig]
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    candidates: dict[str, Candidate] = field(default_factory=lambda: {i: Candidate(i) for i in AGENT_IDS})
    stage: str = "ready"
    judge: dict = field(default_factory=dict)
    judge_reasoning: str = ""
    judge_preview: str = ""
    judge_attempt: int = 0
    final: str = ""
    error: str = ""
    elapsed: float = 0.0
    judge_latency: float = 0.0
    judge_usage: dict = field(default_factory=dict)
    call_count: int = 0
    demo: bool = False

    def to_dict(self) -> dict:
        data = asdict(self)
        data["candidates"] = {k: v.to_dict() for k, v in self.candidates.items()}
        return data

    @classmethod
    def from_dict(cls, value: dict) -> TranslationRecord:
        data = {k: v for k, v in value.items() if k in {f.name for f in fields(cls)}}
        data["agents"] = [AgentConfig.from_dict(a) for a in data["agents"]]
        data["candidates"] = {i: Candidate.from_dict(data.get("candidates", {}).get(i, {"id": i})) for i in AGENT_IDS}
        return cls(**data)
