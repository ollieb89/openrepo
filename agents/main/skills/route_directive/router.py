"""
Intelligent routing logic for Meta-PM Coordinator.

Determines best target for a directive based on:
1. Content analysis (project mentions, tech stack, task type)
2. Swarm state (PM availability, bottlenecks)
3. Registry configuration (domain mappings)
"""

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Dict, Any

from openclaw.logging import get_logger

logger = get_logger("route_directive")


class RouteType(Enum):
    """Types of routing decisions."""
    TO_PM = auto()           # Route to domain PM
    SPAWN_L3 = auto()        # Spawn generic L3 specialist
    COORDINATE = auto()      # Multi-PM coordination
    ESCALATE = auto()        # Escalate to L1
    QUEUE = auto()           # Queue for later (PM bottlenecked)


@dataclass
class RouteDecision:
    """A routing decision with metadata."""
    route_type: RouteType
    target: str              # PM ID, L3 skill, PM list, or escalation reason
    reasoning: str           # Human-readable rationale
    confidence: float = 1.0  # 0.0-1.0 confidence in decision
    priority: str = "normal" # normal, high, urgent
    alternatives: List[str] = field(default_factory=list)  # Alternative targets if primary fails
    swarm_state: Dict[str, Any] = field(default_factory=dict)  # Snapshot at decision time


class DirectiveRouter:
    """
    Intelligent router for L1 directives.
    
    Analyzes directive content, checks swarm state, and returns
    optimal routing decision.
    """
    
    # Keywords that indicate generic tasks (spawn L3 directly)
    GENERIC_KEYWORDS = {
        "research": "research",
        "investigate": "research",
        "explore": "research",
        "analyze": "analysis",
        "analysis": "analysis",
        "evaluate": "analysis",
        "compare": "analysis",
        "document": "documentation",
        "docs": "documentation",
        "readme": "documentation",
        "wiki": "documentation",
        "plan": "planning",
        "breakdown": "planning",
        "estimate": "planning",
    }
    
    # Keywords indicating multi-domain work
    MULTI_DOMAIN_INDICATORS = [
        "frontend and backend",
        "backend and frontend",
        "api and ui",
        "ui and api",
        "full-stack",
        "fullstack",
        "end-to-end",
        "frontend to backend",
        "backend to frontend",
    ]
    
    def __init__(self, config: Dict[str, Any], swarm_query=None):
        """
        Initialize router with configuration.
        
        Args:
            config: Main agent config (project_registry, routing_config)
            swarm_query: Optional SwarmQuery instance for state-aware routing
        """
        self.project_registry = config.get("project_registry", {})
        self.routing_config = config.get("routing_config", {})
        self.swarm = swarm_query
        
        # Build reverse index: stack hint -> project
        self.stack_index: Dict[str, str] = {}
        for project_id, project in self.project_registry.items():
            for hint in project.get("stack_hints", []):
                self.stack_index[hint.lower()] = project_id
    
    def route(self, directive: str, context: Optional[Dict] = None) -> RouteDecision:
        """
        Analyze directive and return routing decision.
        
        Args:
            directive: The L1 directive to route
            context: Optional context (urgent flag, preferred project, etc.)
            
        Returns:
            RouteDecision with routing information
            
        Raises:
            RoutingError: If no valid route can be determined
        """
        directive_lower = directive.lower()
        context = context or {}
        
        logger.info("Routing directive", extra={
            "directive_preview": directive[:100],
            "has_swarm_query": self.swarm is not None
        })
        
        # Get swarm state if available
        swarm_state = self._get_swarm_state()
        
        # Step 1: Check for explicit project mention
        if project_id := self._detect_project_mention(directive_lower):
            return self._route_to_project(project_id, directive, swarm_state)
        
        # Step 2: Check for multi-domain indicators
        if self._detect_multi_domain(directive_lower):
            return self._route_multi_domain(directive, swarm_state)
        
        # Step 3: Check for generic task keywords
        if skill := self._detect_generic_task(directive_lower):
            return self._route_to_l3(skill, directive, swarm_state)
        
        # Step 4: Tech stack detection
        if project_id := self._detect_tech_stack(directive_lower):
            return self._route_to_project(project_id, directive, swarm_state)
        
        # Step 5: Check for domain hints
        if project_id := self._detect_domain_hint(directive_lower):
            return self._route_to_project(project_id, directive, swarm_state)
        
        # Step 6: No clear match - escalate
        return self._escalate(
            directive,
            "No project, stack, or domain match detected",
            swarm_state
        )
    
    def _detect_project_mention(self, directive: str) -> Optional[str]:
        """Detect if directive explicitly mentions a project."""
        for project_id in self.project_registry.keys():
            if project_id.lower() in directive:
                logger.debug(f"Detected project mention: {project_id}")
                return project_id
        return None
    
    def _detect_multi_domain(self, directive: str) -> bool:
        """Detect if directive spans multiple domains."""
        for indicator in self.MULTI_DOMAIN_INDICATORS:
            if indicator in directive:
                logger.debug(f"Detected multi-domain indicator: {indicator}")
                return True
        return False
    
    def _detect_generic_task(self, directive: str) -> Optional[str]:
        """Detect if directive is a generic task (research, analysis, etc.)."""
        for keyword, skill in self.GENERIC_KEYWORDS.items():
            if keyword in directive:
                logger.debug(f"Detected generic task: {keyword} -> {skill}")
                return skill
        return None
    
    def _detect_tech_stack(self, directive: str) -> Optional[str]:
        """Detect tech stack mentions and map to project."""
        for hint, project_id in self.stack_index.items():
            # Use word boundary matching for tech stack names
            pattern = r'\b' + re.escape(hint) + r'\b'
            if re.search(pattern, directive):
                logger.debug(f"Detected stack hint: {hint} -> {project_id}")
                return project_id
        return None
    
    def _detect_domain_hint(self, directive: str) -> Optional[str]:
        """Detect domain keywords from project registry."""
        for project_id, project in self.project_registry.items():
            for domain in project.get("domains", []):
                if domain.lower() in directive:
                    logger.debug(f"Detected domain hint: {domain} -> {project_id}")
                    return project_id
        return None
    
    def _route_to_project(
        self,
        project_id: str,
        directive: str,
        swarm_state: Optional[Dict]
    ) -> RouteDecision:
        """Route directive to a specific project's PM."""
        project = self.project_registry.get(project_id)
        if not project:
            return self._escalate(directive, f"Unknown project: {project_id}", swarm_state)
        
        pm_agent = project.get("pm_agent")
        if not pm_agent:
            return self._escalate(
                directive,
                f"Project {project_id} has no configured PM",
                swarm_state
            )
        
        # Check PM health if swarm state available
        if swarm_state and self.routing_config.get("enable_load_balancing", True):
            pm_health = self._get_pm_health(pm_agent, swarm_state)
            
            low_threshold = self.routing_config.get("health_threshold_low", 0.3)
            
            if pm_health < low_threshold:
                # PM is bottlenecked
                logger.warning(
                    f"Target PM {pm_agent} is bottlenecked (health: {pm_health})"
                )
                
                # Try to find alternative
                alternatives = self._find_alternative_pms(project_id, swarm_state)
                
                if alternatives:
                    return RouteDecision(
                        route_type=RouteType.TO_PM,
                        target=alternatives[0],
                        reasoning=f"Primary PM {pm_agent} bottlenecked, routing to alternative {alternatives[0]}",
                        confidence=0.7,
                        alternatives=alternatives[1:],
                        swarm_state=swarm_state
                    )
                elif self.routing_config.get("fallback_to_l3", True):
                    # Queue or fallback to L3
                    return RouteDecision(
                        route_type=RouteType.QUEUE,
                        target=pm_agent,
                        reasoning=f"PM {pm_agent} bottlenecked, queuing for later",
                        confidence=0.5,
                        swarm_state=swarm_state
                    )
        
        return RouteDecision(
            route_type=RouteType.TO_PM,
            target=pm_agent,
            reasoning=f"Routed to {pm_agent} for project {project_id}",
            confidence=0.95,
            swarm_state=swarm_state
        )
    
    def _route_to_l3(
        self,
        skill: str,
        directive: str,
        swarm_state: Optional[Dict]
    ) -> RouteDecision:
        """Route directive to generic L3 execution."""
        return RouteDecision(
            route_type=RouteType.SPAWN_L3,
            target=skill,
            reasoning=f"Generic task detected, spawning L3 specialist for {skill}",
            confidence=0.9,
            swarm_state=swarm_state
        )
    
    def _route_multi_domain(
        self,
        directive: str,
        swarm_state: Optional[Dict]
    ) -> RouteDecision:
        """Route directive to multi-PM coordination."""
        # Find all relevant PMs based on stack/domain hints
        involved_pms = set()
        
        directive_lower = directive.lower()
        
        # Check for frontend/backend indicators
        if any(kw in directive_lower for kw in ["frontend", "ui", "react", "next.js"]):
            frontend_pm = self._find_pm_for_domain("frontend")
            if frontend_pm:
                involved_pms.add(frontend_pm)
        
        if any(kw in directive_lower for kw in ["backend", "api", "fastapi", "server"]):
            backend_pm = self._find_pm_for_domain("backend")
            if backend_pm:
                involved_pms.add(backend_pm)
        
        # If no specific PMs detected, include all registered PMs
        if not involved_pms:
            for project in self.project_registry.values():
                if pm := project.get("pm_agent"):
                    involved_pms.add(pm)
        
        return RouteDecision(
            route_type=RouteType.COORDINATE,
            target=list(involved_pms),
            reasoning=f"Multi-domain task, coordinating {len(involved_pms)} PMs",
            confidence=0.8,
            swarm_state=swarm_state
        )
    
    def _escalate(
        self,
        directive: str,
        reason: str,
        swarm_state: Optional[Dict]
    ) -> RouteDecision:
        """Create escalation decision."""
        logger.warning(f"Escalating directive: {reason}")
        
        return RouteDecision(
            route_type=RouteType.ESCALATE,
            target="clawdia_prime",
            reasoning=f"Escalated: {reason}",
            confidence=0.3,
            swarm_state=swarm_state
        )
    
    def _get_swarm_state(self) -> Optional[Dict]:
        """Get current swarm state if available."""
        if not self.swarm:
            return None
        
        try:
            overview = self.swarm.get_swarm_overview()
            return {
                "total_active": overview.total_active,
                "total_queued": overview.total_queued,
                "bottleneck_projects": overview.bottleneck_projects,
                "projects": [
                    {
                        "id": p.project_id,
                        "health": p.health_score,
                        "active": p.active_tasks,
                        "queued": p.queued_tasks,
                    }
                    for p in overview.projects
                ]
            }
        except Exception as e:
            logger.warning(f"Failed to get swarm state: {e}")
            return None
    
    def _get_pm_health(self, pm_agent: str, swarm_state: Dict) -> float:
        """Extract PM health from swarm state."""
        # Map pm_agent to project
        for project in self.project_registry.values():
            if project.get("pm_agent") == pm_agent:
                # Find matching project in swarm state
                for p in swarm_state.get("projects", []):
                    if p["id"] in self.project_registry:
                        return p.get("health", 1.0)
        
        return 1.0  # Default to healthy if unknown
    
    def _find_alternative_pms(
        self,
        primary_project: str,
        swarm_state: Dict
    ) -> List[str]:
        """Find alternative PMs with capacity."""
        alternatives = []
        
        primary_domains = set(
            self.project_registry
            .get(primary_project, {})
            .get("domains", [])
        )
        
        for project_id, project in self.project_registry.items():
            if project_id == primary_project:
                continue
            
            # Check if domains overlap
            project_domains = set(project.get("domains", []))
            if primary_domains & project_domains:  # Intersection
                pm_agent = project.get("pm_agent")
                
                # Check health
                pm_health = self._get_pm_health(pm_agent, swarm_state)
                if pm_health > self.routing_config.get("health_threshold_low", 0.3):
                    alternatives.append(pm_agent)
        
        return alternatives
    
    def _find_pm_for_domain(self, domain: str) -> Optional[str]:
        """Find PM responsible for a domain."""
        for project in self.project_registry.values():
            if domain in project.get("domains", []):
                return project.get("pm_agent")
        return None
