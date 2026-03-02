"""
Swarm-Aware Router Integration

Convenience module that properly initializes DirectiveRouter with SwarmQuery.
Handles import path setup and configuration loading.
"""

import json
import sys
from pathlib import Path
from typing import Optional

# Setup paths relative to this file
_REPO_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "packages" / "orchestration" / "src"))

_SKILL_DIR = Path(__file__).parent
_AGENT_DIR = _SKILL_DIR.parent
_CONFIG_PATH = _AGENT_DIR / "agent" / "config.json"

# Now we can import
from agents.clawdia_prime.skills.swarm_query import SwarmQuery
from agents.main.skills.route_directive import DirectiveRouter, RouteDecision, RouteType


class SwarmAwareRouter:
    """
    Ready-to-use router with SwarmQuery integration.
    
    Usage:
        from agents.main.skills.swarm_router import SwarmAwareRouter
        
        router = SwarmAwareRouter()
        decision = router.route("Implement a Next.js feature")
        
        if decision.route_type == RouteType.TO_PM:
            print(f"Route to {decision.target} (health: {decision.swarm_state})")
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize swarm-aware router.
        
        Args:
            config_path: Path to main agent config. Auto-detected if not provided.
        """
        self.config_path = config_path or _CONFIG_PATH
        self.config = self._load_config()
        self.swarm = SwarmQuery(project_ids=self._get_project_ids())
        self.router = DirectiveRouter(self.config, swarm_query=self.swarm)
        
    def _load_config(self) -> dict:
        """Load main agent configuration."""
        with open(self.config_path) as f:
            return json.load(f)
    
    def _get_project_ids(self) -> list:
        """Extract project IDs from config."""
        registry = self.config.get("project_registry", {})
        return list(registry.keys())
    
    def route(self, directive: str, context: Optional[dict] = None) -> RouteDecision:
        """
        Route a directive with full swarm awareness.
        
        Args:
            directive: The L1 directive to route
            context: Optional routing context
            
        Returns:
            RouteDecision with swarm state included
        """
        return self.router.route(directive, context)
    
    def get_swarm_overview(self):
        """Get current swarm overview."""
        return self.swarm.get_swarm_overview()
    
    def get_project_status(self, project_id: str):
        """Get status for a specific project."""
        return self.swarm.get_project_status(project_id)


def quick_route(directive: str) -> RouteDecision:
    """
    Quick routing without explicit router setup.
    
    Args:
        directive: Directive to route
        
    Returns:
        RouteDecision
    """
    router = SwarmAwareRouter()
    return router.route(directive)


if __name__ == "__main__":
    """CLI for testing swarm-aware routing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Swarm-aware directive router")
    parser.add_argument("directive", help="Directive to route")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    router = SwarmAwareRouter()
    decision = router.route(args.directive)
    
    if args.json:
        import json
        result = {
            "route_type": decision.route_type.name,
            "target": decision.target,
            "reasoning": decision.reasoning,
            "confidence": decision.confidence,
            "swarm_state": decision.swarm_state,
        }
        print(json.dumps(result, indent=2, default=str))
    else:
        route_colors = {
            RouteType.TO_PM: "\033[94m",
            RouteType.SPAWN_L3: "\033[92m",
            RouteType.COORDINATE: "\033[93m",
            RouteType.ESCALATE: "\033[91m",
            RouteType.QUEUE: "\033[95m",
        }
        reset = "\033[0m"
        bold = "\033[1m"
        color = route_colors.get(decision.route_type, "")
        
        print(f"{bold}Swarm-Aware Routing Decision:{reset}")
        print(f"  Directive: {args.directive[:60]}...")
        print(f"  Route Type: {color}{decision.route_type.name}{reset}")
        print(f"  Target: {bold}{decision.target}{reset}")
        print(f"  Confidence: {decision.confidence:.0%}")
        print(f"  Reasoning: {decision.reasoning}")
        
        if decision.swarm_state:
            print(f"\n{bold}Swarm State:{reset}")
            print(f"  Total Active: {decision.swarm_state.get('total_active', 'N/A')}")
            print(f"  Bottlenecks: {decision.swarm_state.get('bottleneck_projects', [])}")
