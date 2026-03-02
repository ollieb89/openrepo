"""
Parallel PM Coordinator implementation.

Coordinates execution across multiple domain PMs for cross-domain work.
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Any

from openclaw.logging import get_logger

logger = get_logger("coordinate_parallel")


class CoordinationStatus(Enum):
    """Status of coordination execution."""
    PENDING = auto()
    DISPATCHED = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    PARTIAL = auto()      # Some PMs succeeded, others failed
    FAILED = auto()
    TIMEOUT = auto()


@dataclass
class Subtask:
    """A subtask assigned to a specific PM."""
    pm_agent: str
    directive: str
    expected_output: str
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


@dataclass
class CoordinationResult:
    """Result of coordination execution."""
    status: CoordinationStatus
    subtasks: Dict[str, Subtask]
    aggregated_output: Optional[str] = None
    integration_valid: bool = False
    conflicts: List[str] = field(default_factory=list)
    report: str = ""


class ParallelCoordinator:
    """
    Coordinates parallel execution across multiple PMs.
    
    Handles decomposition, dispatch, monitoring, validation, and aggregation.
    """
    
    def __init__(self, config: Dict[str, Any], swarm_query=None, router=None):
        """
        Initialize coordinator.
        
        Args:
            config: Main agent configuration
            swarm_query: SwarmQuery instance for monitoring
            router: Optional router for subtask dispatch
        """
        self.config = config
        self.swarm = swarm_query
        self.router = router
        self.poll_interval = 10.0  # seconds between progress checks
        self.timeout = config.get("coordination_timeout", 3600)  # 1 hour default
    
    async def execute(
        self,
        directive: str,
        pm_list: List[str],
        integration_contract: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> CoordinationResult:
        """
        Execute coordination across multiple PMs.
        
        Args:
            directive: Original L1 directive
            pm_list: List of PM agents to coordinate
            integration_contract: Expected outputs and interfaces
            context: Additional context (deadline, priority, etc.)
            
        Returns:
            CoordinationResult with status and aggregated output
        """
        context = context or {}
        logger.info(
            "Starting parallel coordination",
            extra={"pm_count": len(pm_list), "directive_preview": directive[:100]}
        )
        
        # Step 1: Decompose directive into subtasks
        subtasks = self._decompose(directive, pm_list, integration_contract)
        
        # Step 2: Dispatch to PMs in parallel
        await self._dispatch_parallel(subtasks)
        
        # Step 3: Monitor until completion or timeout
        completed = await self._monitor(subtasks)
        
        if not completed:
            return CoordinationResult(
                status=CoordinationStatus.TIMEOUT,
                subtasks=subtasks,
                report="Coordination timed out"
            )
        
        # Step 4: Validate integration
        valid, conflicts = self._validate_integration(subtasks, integration_contract)
        
        # Step 5: Aggregate results
        if valid:
            aggregated = self._aggregate_results(subtasks)
            status = self._determine_status(subtasks)
            return CoordinationResult(
                status=status,
                subtasks=subtasks,
                aggregated_output=aggregated,
                integration_valid=True,
                report=self._generate_report(subtasks, status)
            )
        else:
            return CoordinationResult(
                status=CoordinationStatus.FAILED,
                subtasks=subtasks,
                integration_valid=False,
                conflicts=conflicts,
                report=self._generate_report(subtasks, CoordinationStatus.FAILED, conflicts)
            )
    
    def _decompose(
        self,
        directive: str,
        pm_list: List[str],
        contract: Optional[Dict[str, Any]]
    ) -> Dict[str, Subtask]:
        """
        Decompose directive into PM-specific subtasks.
        
        Args:
            directive: Original directive
            pm_list: Target PMs
            contract: Integration contract defining expected outputs
            
        Returns:
            Dict mapping pm_agent -> Subtask
        """
        subtasks = {}
        
        # Extract expected outputs from contract
        outputs = contract.get("outputs", {}) if contract else {}
        interface = contract.get("interface", "") if contract else ""
        
        for pm_agent in pm_list:
            # Create PM-specific subtask directive
            expected = outputs.get(pm_agent, "Complete assigned portion")
            
            subtask_directive = self._create_subtask_directive(
                directive, pm_agent, expected, interface
            )
            
            subtasks[pm_agent] = Subtask(
                pm_agent=pm_agent,
                directive=subtask_directive,
                expected_output=expected,
                dependencies=[]  # Could be enhanced to detect dependencies
            )
            
            logger.debug(f"Created subtask for {pm_agent}", extra={
                "directive_preview": subtask_directive[:100]
            })
        
        return subtasks
    
    def _create_subtask_directive(
        self,
        original: str,
        pm_agent: str,
        expected: str,
        interface: str
    ) -> str:
        """Create a focused subtask directive for a specific PM."""
        parts = [
            f"[Meta-PM Coordination Task]",
            f"",
            f"Context: This is part of a multi-domain directive coordinated by the Meta-PM.",
            f"Your role: {pm_agent}",
            f"",
            f"Original directive: {original}",
            f"",
            f"Your specific deliverable: {expected}",
        ]
        
        if interface:
            parts.extend([
                f"",
                f"Integration requirements: {interface}",
            ])
        
        parts.extend([
            f"",
            f"IMPORTANT: Coordinate with other PMs via the Meta-PM. Do not assume completion of other parts.",
            f"Report progress regularly. Signal blockers immediately.",
        ])
        
        return "\n".join(parts)
    
    async def _dispatch_parallel(self, subtasks: Dict[str, Subtask]) -> None:
        """
        Dispatch all subtasks to their PMs in parallel.
        
        In production, this would use the router or openclaw CLI to dispatch.
        For now, we simulate the dispatch by updating subtask state.
        """
        logger.info(f"Dispatching {len(subtasks)} subtasks in parallel")
        
        # In real implementation, this would:
        # 1. Call router to dispatch to each PM
        # 2. Use asyncio.gather for parallel dispatch
        # 3. Handle dispatch errors
        
        for subtask in subtasks.values():
            subtask.status = "dispatched"
            subtask.started_at = time.time()
            
            # TODO: Actual dispatch via router.spawn or CLI
            logger.debug(f"Dispatched to {subtask.pm_agent}")
    
    async def _monitor(self, subtasks: Dict[str, Subtask]) -> bool:
        """
        Monitor subtask progress until completion or timeout.
        
        Args:
            subtasks: Dict of subtasks to monitor
            
        Returns:
            True if all completed (success or failure), False if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < self.timeout:
            # Check completion status
            all_done = True
            any_active = False
            
            for pm_agent, subtask in subtasks.items():
                # In production, query swarm state for actual status
                # For now, simulate status check
                current_status = self._query_pm_status(pm_agent)
                
                if current_status == "completed":
                    subtask.status = "completed"
                    subtask.completed_at = time.time()
                elif current_status == "failed":
                    subtask.status = "failed"
                    subtask.completed_at = time.time()
                elif current_status in ("in_progress", "starting"):
                    subtask.status = "in_progress"
                    all_done = False
                    any_active = True
                else:
                    all_done = False
            
            if all_done:
                logger.info("All subtasks completed")
                return True
            
            if any_active:
                logger.debug(f"Monitoring: {len([s for s in subtasks.values() if s.status == 'in_progress'])} active")
            
            # Wait before next poll
            await asyncio.sleep(self.poll_interval)
        
        logger.warning("Coordination timed out")
        return False
    
    def _query_pm_status(self, pm_agent: str) -> str:
        """
        Query PM status via swarm state.
        
        In production, this would check the PM's project state via swarm_query.
        """
        if not self.swarm:
            return "unknown"
        
        try:
            # Find project for this PM
            project_id = self._find_project_for_pm(pm_agent)
            if not project_id:
                return "unknown"
            
            snapshot = self.swarm.get_project_status(project_id)
            if not snapshot:
                return "unknown"
            
            # Determine status from active/queued/completed tasks
            if snapshot.active_tasks > 0:
                return "in_progress"
            elif snapshot.queued_tasks > 0:
                return "pending"
            else:
                return "completed"  # Or could be idle
                
        except Exception as e:
            logger.warning(f"Failed to query PM status: {e}")
            return "unknown"
    
    def _find_project_for_pm(self, pm_agent: str) -> Optional[str]:
        """Find project ID managed by a PM."""
        registry = self.config.get("project_registry", {})
        for project_id, project in registry.items():
            if project.get("pm_agent") == pm_agent:
                return project_id
        return None
    
    def _validate_integration(
        self,
        subtasks: Dict[str, Subtask],
        contract: Optional[Dict[str, Any]]
    ) -> tuple[bool, List[str]]:
        """
        Validate that subtask outputs meet integration contract.
        
        Args:
            subtasks: Completed subtasks
            contract: Integration contract
            
        Returns:
            (is_valid, list_of_conflicts)
        """
        if not contract:
            # No contract to validate against
            return True, []
        
        conflicts = []
        
        # Check each PM produced expected output
        expected_outputs = contract.get("outputs", {})
        for pm_agent, expected in expected_outputs.items():
            if pm_agent not in subtasks:
                conflicts.append(f"Missing PM: {pm_agent}")
                continue
            
            subtask = subtasks[pm_agent]
            if subtask.status != "completed":
                conflicts.append(f"PM {pm_agent} did not complete: {subtask.status}")
            elif not subtask.result:
                conflicts.append(f"PM {pm_agent} completed but produced no output")
        
        # TODO: More sophisticated validation (interface compatibility, etc.)
        
        return len(conflicts) == 0, conflicts
    
    def _aggregate_results(self, subtasks: Dict[str, Subtask]) -> str:
        """
        Aggregate subtask results into unified output.
        
        Args:
            subtasks: Completed subtasks
            
        Returns:
            Aggregated output string
        """
        parts = [
            "# Multi-Domain Coordination Results",
            "",
            f"Coordinated {len(subtasks)} PMs:",
            "",
        ]
        
        for pm_agent, subtask in subtasks.items():
            status_icon = "✅" if subtask.status == "completed" else "❌"
            parts.append(f"## {status_icon} {pm_agent}")
            parts.append(f"")
            parts.append(f"**Expected:** {subtask.expected_output}")
            parts.append(f"**Status:** {subtask.status}")
            
            if subtask.result:
                parts.append(f"**Result:**")
                parts.append(subtask.result)
            elif subtask.error:
                parts.append(f"**Error:** {subtask.error}")
            
            if subtask.completed_at and subtask.started_at:
                duration = subtask.completed_at - subtask.started_at
                parts.append(f"**Duration:** {duration:.1f}s")
            
            parts.append("")
        
        return "\n".join(parts)
    
    def _determine_status(self, subtasks: Dict[str, Subtask]) -> CoordinationStatus:
        """Determine overall coordination status from subtasks."""
        statuses = [s.status for s in subtasks.values()]
        
        if all(s == "completed" for s in statuses):
            return CoordinationStatus.COMPLETED
        elif all(s == "failed" for s in statuses):
            return CoordinationStatus.FAILED
        elif any(s == "completed" for s in statuses):
            return CoordinationStatus.PARTIAL
        else:
            return CoordinationStatus.FAILED
    
    def _generate_report(
        self,
        subtasks: Dict[str, Subtask],
        status: CoordinationStatus,
        conflicts: Optional[List[str]] = None
    ) -> str:
        """Generate human-readable coordination report."""
        lines = [
            f"Coordination Status: {status.name}",
            f"PMs Involved: {len(subtasks)}",
            f"Completed: {sum(1 for s in subtasks.values() if s.status == 'completed')}",
            f"Failed: {sum(1 for s in subtasks.values() if s.status == 'failed')}",
        ]
        
        if conflicts:
            lines.append("")
            lines.append("Integration Conflicts:")
            for conflict in conflicts:
                lines.append(f"  - {conflict}")
        
        return "\n".join(lines)
