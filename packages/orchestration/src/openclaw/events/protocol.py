"""Cross-runtime event protocol — shared between Python and TypeScript."""

from enum import Enum
from dataclasses import dataclass, asdict
from typing import Optional
import json
import time

class EventDomain(str, Enum):
    TASK = "openclaw.task"
    AGENT = "openclaw.agent"
    AUTONOMY = "openclaw.autonomy"
    MEMORY = "openclaw.memory"
    POOL = "openclaw.pool"

class EventType(str, Enum):
    # Task lifecycle
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_ESCALATED = "task.escalated"
    TASK_OUTPUT = "task.output"

    # Agent lifecycle
    AGENT_DISPATCHED = "agent.dispatched"
    AGENT_RESPONSE = "agent.response"
    AGENT_ERROR = "agent.error"

    # Autonomy
    AUTONOMY_STATE_CHANGED = "autonomy.state_changed"
    AUTONOMY_CONFIDENCE_UPDATED = "autonomy.confidence_updated"
    AUTONOMY_ESCALATION = "autonomy.escalation"

    # Memory
    MEMORY_STORED = "memory.stored"
    MEMORY_RECALLED = "memory.recalled"

    # Pool
    POOL_SLOT_ACQUIRED = "pool.slot_acquired"
    POOL_SLOT_RELEASED = "pool.slot_released"
    POOL_OVERFLOW = "pool.overflow"

@dataclass
class OrchestratorEvent:
    type: EventType
    domain: EventDomain
    project_id: str
    agent_id: Optional[str] = None
    task_id: Optional[str] = None
    payload: Optional[dict] = None
    timestamp: float = None
    correlation_id: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, data: str) -> "OrchestratorEvent":
        d = json.loads(data)
        d["type"] = EventType(d["type"])
        d["domain"] = EventDomain(d["domain"])
        return cls(**d)
