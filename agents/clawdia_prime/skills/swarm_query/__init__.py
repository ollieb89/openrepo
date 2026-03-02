"""
Swarm Query - Read-only cross-project state aggregation for L1 visibility.

Provides ClawdiaPrime with visibility into the entire swarm without
modifying any state. Uses shared locks (LOCK_SH) for safe concurrent access.
"""

from .query import SwarmQuery, ProjectSnapshot, SwarmOverview, TaskInfo

__all__ = ["SwarmQuery", "ProjectSnapshot", "SwarmOverview", "TaskInfo"]
