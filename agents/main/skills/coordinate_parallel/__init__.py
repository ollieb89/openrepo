"""
Parallel PM Coordinator for Meta-PM.

Manages multi-domain task execution across multiple PMs.
"""

from .coordinator import (
    ParallelCoordinator,
    CoordinationResult,
    CoordinationStatus,
    Subtask,
)

__all__ = [
    "ParallelCoordinator",
    "CoordinationResult",
    "CoordinationStatus",
    "Subtask",
]
