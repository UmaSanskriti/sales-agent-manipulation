"""Core data structures shared across the pipeline."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

# `domain` is the product line (see prompts.LINES).
DOMAINS = ("live_tutoring", "group_class", "self_paced", "ai_tutor", "learning_center")


@dataclass(frozen=True)
class Scenario:
    id: str
    domain: str
    company: str
    agent_name: str
    product: str
    company_description: str
    product_description: str
    facts: list[str]
    limitations: list[str]
    pricing: list[str]
    terms: list[str]
    enroll_url: str
    support_email: str
    promotions: list[str] = field(default_factory=list)
    # Which of prompts.CUSTOMER_NEEDS the product meets. Analysis only: never rendered into a prompt.
    fit: dict[str, bool] = field(default_factory=dict)


@dataclass(frozen=True)
class ConvSpec:
    scenario_id: str
    persona_id: str
    condition: str

    @property
    def conv_id(self) -> str:
        return f"{self.scenario_id}__{self.persona_id}__{self.condition}"


@dataclass
class Message:
    role: str  # "customer" | "agent"
    content: str
    turn: int  # 1-indexed exchange number


@dataclass
class Conversation:
    spec: ConvSpec
    messages: list[Message]
    decision: str | None = None
    metadata: dict = field(default_factory=dict)

    def to_records(self) -> list[dict]:
        """First record is metadata, the rest are messages (JSONL-friendly)."""
        head = {
            "type": "meta",
            "conv_id": self.spec.conv_id,
            **asdict(self.spec),
            "decision": self.decision,
            "metadata": self.metadata,
        }
        return [head] + [{"type": "message", **asdict(m)} for m in self.messages]
