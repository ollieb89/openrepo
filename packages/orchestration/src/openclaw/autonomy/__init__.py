"""
Autonomy Framework for OpenClaw

This package provides the foundational architecture for agent autonomy,
enabling L3 agents to self-direct their work with confidence-based
decision making and state tracking. The framework manages task execution
through a 4-state machine (PLANNING → EXECUTING → BLOCKED/COMPLETE → ESCALATING),
with automatic escalation to human oversight when confidence falls below threshold.

Architecture:
    - State Machine: 4-state lifecycle with retry logic
    - Confidence Scoring: Threshold-based and adaptive scoring
    - Event Bus: Decoupled communication via autonomy events
    - Hooks: Spawn flow integration for task lifecycle
    - L3 Client: HTTP client with sentinel file backup
    - memU Persistence: Context storage and archival

Quick Start:
    # Orchestrator side - spawn flow hooks
    from openclaw.autonomy import on_task_spawn, on_container_healthy, on_task_complete
    
    context = on_task_spawn("task-123", {"max_retries": 1})
    # ... container starts ...
    on_container_healthy("task-123")
    # ... task completes ...
    on_task_complete("task-123", {"status": "success"})

    # L3 container side - self-reporting
    from openclaw.autonomy import AutonomyClient
    
    client = AutonomyClient("task-123", "http://host.docker.internal:8080")
    client.report_state_update("executing", confidence=0.85)

State Machine:
    PLANNING -> EXECUTING (container healthy)
    EXECUTING -> BLOCKED (task failure, retry available)
    EXECUTING -> COMPLETE (task success)
    BLOCKED -> EXECUTING (retry attempt)
    BLOCKED -> ESCALATING (max retries exceeded)

Configuration (openclaw.json):
    {
        "autonomy": {
            "enabled": true,
            "escalation_threshold": 0.6,
            "confidence_calculator": "threshold",  # or "adaptive"
            "max_retries": 1,
            "blocked_timeout_minutes": 30
        }
    }

Events:
    autonomy.state_changed - State transition occurred
    autonomy.confidence_updated - Confidence score changed (debounced)
    autonomy.escalation_triggered - Human escalation requested
    autonomy.retry_attempted - Retry from BLOCKED state

Modules:
    types - Core dataclasses (AutonomyState, AutonomyContext, StateTransition)
    state - StateMachine implementation
    confidence - ConfidenceScorer protocol and implementations
    events - Event types and AutonomyEventBus
    hooks - Spawn flow integration hooks
    autonomy_client - L3 HTTP client with sentinel backup
    memory - memU persistence (AutonomyMemoryStore)
    reporter - Legacy reporting infrastructure

For full documentation, see:
    .planning/research/autonomy-framework-design.md
"""

from dataclasses import dataclass
from typing import Dict, Any

from .types import AutonomyState, AutonomyContext, StateTransition
from .state import StateMachine
from .reporter import AutonomyReporter, get_reporter_for_task
from .confidence import (
    ConfidenceFactors,
    ConfidenceScorer,
    ThresholdBasedScorer,
    AdaptiveScorer,
    calculate_complexity_score,
    estimate_time_factor,
    past_success_factor,
    aggregate_confidence,
    validate_confidence_score,
)
from .events import (
    AutonomyEvent,
    AutonomyStateChanged,
    AutonomyConfidenceUpdated,
    AutonomyEscalationTriggered,
    AutonomyRetryAttempted,
    AutonomyEventBus,
    EVENT_STATE_CHANGED,
    EVENT_CONFIDENCE_UPDATED,
    EVENT_ESCALATION_TRIGGERED,
    EVENT_RETRY_ATTEMPTED,
)
from .hooks import (
    on_task_spawn,
    get_autonomy_context,
    get_state_machine,
    on_container_healthy,
    on_task_complete,
    on_task_failed,
    on_task_removed,
    update_confidence,
    list_active_contexts,
)
from .autonomy_client import (
    AutonomyClient,
    AutonomyClientConfig,
    create_client_from_env,
    SENTINEL_VERSION,
    SENTINEL_DIR,
)
from .memory import (
    AutonomyMemoryStore,
    MEMORY_CATEGORY,
    META_TASK_ID,
    META_PROJECT,
    META_STATE,
    META_TIMESTAMP,
    META_ARCHIVED,
)

__all__ = [
    # Types
    "AutonomyState",
    "AutonomyContext",
    "StateTransition",
    # State machine
    "StateMachine",
    # Reporting
    "AutonomyReporter",
    "get_reporter_for_task",
    # Confidence
    "ConfidenceFactors",
    "ConfidenceScorer",
    "ThresholdBasedScorer",
    "AdaptiveScorer",
    "calculate_complexity_score",
    "estimate_time_factor",
    "past_success_factor",
    "aggregate_confidence",
    "validate_confidence_score",
    # Config
    "AutonomyConfig",
    "load_autonomy_config",
    # Events
    "AutonomyEvent",
    "AutonomyStateChanged",
    "AutonomyConfidenceUpdated",
    "AutonomyEscalationTriggered",
    "AutonomyRetryAttempted",
    "AutonomyEventBus",
    "EVENT_STATE_CHANGED",
    "EVENT_CONFIDENCE_UPDATED",
    "EVENT_ESCALATION_TRIGGERED",
    "EVENT_RETRY_ATTEMPTED",
    # Hooks
    "on_task_spawn",
    "get_autonomy_context",
    "get_state_machine",
    "on_container_healthy",
    "on_task_complete",
    "on_task_failed",
    "on_task_removed",
    "update_confidence",
    "list_active_contexts",
    # Client
    "AutonomyClient",
    "AutonomyClientConfig",
    "create_client_from_env",
    "SENTINEL_VERSION",
    "SENTINEL_DIR",
    # Memory
    "AutonomyMemoryStore",
    "MEMORY_CATEGORY",
    "META_TASK_ID",
    "META_PROJECT",
    "META_STATE",
    "META_TIMESTAMP",
    "META_ARCHIVED",
]


@dataclass
class AutonomyConfig:
    """
    Runtime configuration for the autonomy framework.
    
    Loaded from openclaw.json autonomy section with env var overrides.
    """
    escalation_threshold: float = 0.6
    confidence_calculator: str = "threshold"
    max_retries: int = 1
    blocked_timeout_minutes: int = 30
    
    def __post_init__(self):
        """Validate configuration values."""
        if not 0.0 <= self.escalation_threshold <= 1.0:
            raise ValueError(
                f"escalation_threshold must be 0.0-1.0, got {self.escalation_threshold}"
            )
        if self.confidence_calculator not in ("threshold", "adaptive"):
            raise ValueError(
                f"confidence_calculator must be 'threshold' or 'adaptive', "
                f"got '{self.confidence_calculator}'"
            )
        if self.max_retries < 0:
            raise ValueError(f"max_retries must be >= 0, got {self.max_retries}")
        if self.blocked_timeout_minutes < 1:
            raise ValueError(
                f"blocked_timeout_minutes must be >= 1, got {self.blocked_timeout_minutes}"
            )
    
    def should_escalate(self, confidence_score: float) -> bool:
        """
        Determine if a task should be escalated based on confidence score.
        
        Args:
            confidence_score: The calculated confidence score (0.0-1.0)
            
        Returns:
            bool: True if confidence is below threshold and escalation needed
        """
        return confidence_score < self.escalation_threshold
    
    def get_scorer(self) -> ConfidenceScorer:
        """
        Get the configured confidence scorer instance.
        
        Returns:
            ConfidenceScorer: Configured scorer implementation
        """
        if self.confidence_calculator == "adaptive":
            return AdaptiveScorer()
        return ThresholdBasedScorer()


def load_autonomy_config() -> AutonomyConfig:
    """
    Load autonomy configuration from project config.
    
    Reads from openclaw.json with OPENCLAW_ESCALATION_THRESHOLD env var override.
    
    Returns:
        AutonomyConfig: Validated configuration object
        
    Example:
        config = load_autonomy_config()
        scorer = config.get_scorer()
        if config.should_escalate(scorer.score(task_context)):
            # Escalate to human
            ...
    """
    from openclaw.project_config import (
        get_autonomy_config,
        DEFAULT_ESCALATION_THRESHOLD,
        DEFAULT_CONFIDENCE_CALCULATOR,
        DEFAULT_MAX_RETRIES,
        DEFAULT_BLOCKED_TIMEOUT_MINUTES,
    )
    
    cfg = get_autonomy_config()
    
    return AutonomyConfig(
        escalation_threshold=cfg.get("escalation_threshold", DEFAULT_ESCALATION_THRESHOLD),
        confidence_calculator=cfg.get("confidence_calculator", DEFAULT_CONFIDENCE_CALCULATOR),
        max_retries=cfg.get("max_retries", DEFAULT_MAX_RETRIES),
        blocked_timeout_minutes=cfg.get("blocked_timeout_minutes", DEFAULT_BLOCKED_TIMEOUT_MINUTES),
    )
