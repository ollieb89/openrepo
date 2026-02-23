"""
Orchestration Startup Initialization Module

Provides idempotent workspace initialization and verification functions.
Ensures all required directories exist at startup.

Usage:
    python3 orchestration/init.py
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def find_project_root(start_path: Optional[Path] = None) -> Path:
    """
    Find project root by walking up to find openclaw.json.
    
    Args:
        start_path: Starting directory (default: current file location)
        
    Returns:
        Path to project root
        
    Raises:
        FileNotFoundError: If openclaw.json not found
    """
    if start_path is None:
        start_path = Path(__file__).resolve().parent
    
    current = start_path
    for _ in range(10):
        if (current / 'openclaw.json').exists():
            return current
        if current.parent == current:
            break
        current = current.parent
    
    raise FileNotFoundError(
        "Could not find openclaw.json in parent directories. "
        "Are you running from within the OpenClaw project?"
    )


def initialize_workspace(project_root: Optional[Path] = None) -> Dict[str, Any]:
    """
    Initialize workspace by creating required directories idempotently.
    
    Args:
        project_root: Path to project root (default: auto-detect)
        
    Returns:
        Dictionary with initialization results:
        - snapshots_dir: str - Path to snapshots directory
        - created: bool - Whether directory was created
        - already_existed: bool - Whether directory already existed
    """
    if project_root is None:
        project_root = find_project_root()
    
    snapshots_dir = project_root / 'workspace' / '.openclaw' / 'snapshots'
    
    already_existed = snapshots_dir.exists()
    
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    
    created = not already_existed
    
    if created:
        print(f"{Colors.GREEN}✓{Colors.RESET} Created snapshots directory: {snapshots_dir}")
    else:
        print(f"{Colors.BLUE}ℹ{Colors.RESET} Snapshots directory already exists: {snapshots_dir}")
    
    return {
        'snapshots_dir': str(snapshots_dir),
        'created': created,
        'already_existed': already_existed
    }


def verify_workspace(project_root: Optional[Path] = None) -> Dict[str, bool]:
    """
    Verify workspace directories and orchestration modules.
    
    Args:
        project_root: Path to project root (default: auto-detect)
        
    Returns:
        Dictionary of verification checks:
        - snapshots_dir: bool - Snapshots directory exists
        - state_file_dir: bool - State file directory exists
        - orchestration_importable: bool - Orchestration modules importable
    """
    if project_root is None:
        project_root = find_project_root()
    
    results = {}
    
    snapshots_dir = project_root / 'workspace' / '.openclaw' / 'snapshots'
    results['snapshots_dir'] = snapshots_dir.exists() and snapshots_dir.is_dir()
    
    state_file_dir = project_root / 'workspace' / '.openclaw'
    results['state_file_dir'] = state_file_dir.exists() and state_file_dir.is_dir()
    
    try:
        import sys
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        import orchestration.config
        import orchestration.snapshot
        import orchestration.state_engine
        results['orchestration_importable'] = True
    except ImportError:
        results['orchestration_importable'] = False
    
    return results


def main():
    """
    CLI entrypoint for workspace initialization and verification.
    
    Exit codes:
        0 - All checks passed
        1 - One or more checks failed
    """
    print(f"\n{Colors.BOLD}Workspace Initialization{Colors.RESET}\n")
    
    try:
        project_root = find_project_root()
        print(f"{Colors.BLUE}ℹ{Colors.RESET} Project root: {project_root}\n")
    except FileNotFoundError as e:
        print(f"{Colors.RED}✗{Colors.RESET} {e}")
        return 1
    
    try:
        init_result = initialize_workspace(project_root)
    except Exception as e:
        print(f"{Colors.RED}✗{Colors.RESET} Initialization failed: {e}")
        return 1
    
    print(f"\n{Colors.BOLD}Verification{Colors.RESET}\n")
    
    try:
        verify_result = verify_workspace(project_root)
    except Exception as e:
        print(f"{Colors.RED}✗{Colors.RESET} Verification failed: {e}")
        return 1
    
    all_passed = True
    
    if verify_result['snapshots_dir']:
        print(f"{Colors.GREEN}✓{Colors.RESET} Snapshots directory exists")
    else:
        print(f"{Colors.RED}✗{Colors.RESET} Snapshots directory missing")
        all_passed = False
    
    if verify_result['state_file_dir']:
        print(f"{Colors.GREEN}✓{Colors.RESET} State file directory exists")
    else:
        print(f"{Colors.RED}✗{Colors.RESET} State file directory missing")
        all_passed = False
    
    if verify_result['orchestration_importable']:
        print(f"{Colors.GREEN}✓{Colors.RESET} Orchestration modules importable")
    else:
        print(f"{Colors.RED}✗{Colors.RESET} Orchestration modules not importable")
        all_passed = False
    
    print()
    if all_passed:
        print(f"{Colors.GREEN}{Colors.BOLD}RESULT: All checks PASSED{Colors.RESET}\n")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}RESULT: One or more checks FAILED{Colors.RESET}\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
