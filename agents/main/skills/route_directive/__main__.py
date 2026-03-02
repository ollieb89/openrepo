"""
CLI for testing directive routing.

Usage:
    python -m agents.main.skills.route_directive "Implement a Next.js login page"
"""

import argparse
import json
import sys
from pathlib import Path

# Add paths for imports
script_dir = Path(__file__).resolve().parent
repo_root = script_dir.parent.parent.parent.parent.parent
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(repo_root / "packages" / "orchestration" / "src"))

from agents.main.skills.route_directive import DirectiveRouter, RouteType


def main():
    parser = argparse.ArgumentParser(
        description="Test directive routing logic",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "Implement a Next.js login page"
  %(prog)s "Research authentication best practices"
  %(prog)s "Create FastAPI backend for user management"
        """
    )
    parser.add_argument("directive", help="Directive to route")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).parent.parent / "agent" / "config.json",
        help="Path to main agent config"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    
    args = parser.parse_args()
    
    # Load config
    try:
        with open(args.config) as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        return 1
    
    # Create router (without swarm for CLI testing)
    router = DirectiveRouter(config, swarm_query=None)
    
    # Route directive
    try:
        decision = router.route(args.directive)
    except Exception as e:
        print(f"Routing error: {e}", file=sys.stderr)
        return 1
    
    # Output result
    if args.json:
        result = {
            "route_type": decision.route_type.name,
            "target": decision.target,
            "reasoning": decision.reasoning,
            "confidence": decision.confidence,
            "priority": decision.priority,
        }
        print(json.dumps(result, indent=2))
    else:
        route_type_colors = {
            RouteType.TO_PM: "\033[94m",      # Blue
            RouteType.SPAWN_L3: "\033[92m",   # Green
            RouteType.COORDINATE: "\033[93m", # Yellow
            RouteType.ESCALATE: "\033[91m",   # Red
            RouteType.QUEUE: "\033[95m",      # Magenta
        }
        reset = "\033[0m"
        bold = "\033[1m"
        color = route_type_colors.get(decision.route_type, "")
        
        print(f"{bold}Routing Decision:{reset}")
        print(f"  Route Type: {color}{decision.route_type.name}{reset}")
        print(f"  Target: {bold}{decision.target}{reset}")
        print(f"  Confidence: {decision.confidence:.0%}")
        print(f"  Priority: {decision.priority}")
        print(f"  Reasoning: {decision.reasoning}")
        
        if decision.alternatives:
            print(f"  Alternatives: {', '.join(decision.alternatives)}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
