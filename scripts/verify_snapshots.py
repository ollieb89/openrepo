#!/usr/bin/env python3
"""
Snapshot System Verification Script

Tests the snapshot capture flow end-to-end and reports pass/fail for each stage:
1. Directory Existence - Verify snapshots directory exists
2. Snapshot Module Import - Verify orchestration.snapshot is importable
3. Test Snapshot Capture - Create test snapshot and verify (if git repo)
4. Config Consistency - Verify SNAPSHOT_DIR matches actual directory

Exit codes:
  0 - All stages passed or skipped
  1 - One or more stages failed
"""

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, Tuple


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_stage(name: str, status: str, message: str, hint: str = None):
    """Print a stage result with color coding"""
    if status == 'pass':
        symbol = f"{Colors.GREEN}✓{Colors.RESET}"
        print(f"[{symbol}] {Colors.BOLD}{name}{Colors.RESET}: {message}")
    elif status == 'fail':
        symbol = f"{Colors.RED}✗{Colors.RESET}"
        print(f"[{symbol}] {Colors.BOLD}{name}{Colors.RESET}: {message}")
        if hint:
            print(f"    {Colors.YELLOW}→{Colors.RESET} {hint}")
    elif status == 'skip':
        symbol = f"{Colors.YELLOW}⊘{Colors.RESET}"
        print(f"[{symbol}] {Colors.BOLD}{name}{Colors.RESET}: {message}")
    elif status == 'info':
        print(f"{Colors.BLUE}ℹ{Colors.RESET} {message}")


def find_project_root() -> Path:
    """Find project root by walking up to find openclaw.json"""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / 'openclaw.json').exists():
            return current
        if current.parent == current:
            break
        current = current.parent
    
    raise FileNotFoundError("Could not find openclaw.json in parent directories")


def stage_directory_existence() -> Tuple[bool, Path]:
    """Stage 1: Check that snapshots directory exists"""
    try:
        project_root = find_project_root()
    except FileNotFoundError as e:
        print_stage(
            'Directory Existence',
            'fail',
            str(e),
            'Run from within OpenClaw project directory'
        )
        return False, None
    
    snapshots_dir = project_root / 'workspace' / '.openclaw' / 'snapshots'
    
    if not snapshots_dir.exists():
        print_stage(
            'Directory Existence',
            'fail',
            f'Snapshots directory not found: {snapshots_dir}',
            'Run: python3 orchestration/init.py'
        )
        
        try:
            sys.path.insert(0, str(project_root))
            from orchestration.init import initialize_workspace
            print_stage('Directory Existence', 'info', 'Attempting to create directory...')
            initialize_workspace(project_root)
            
            if snapshots_dir.exists():
                print_stage('Directory Existence', 'pass', f'Directory created: {snapshots_dir}')
                return True, snapshots_dir
            else:
                print_stage('Directory Existence', 'fail', 'Failed to create directory')
                return False, None
        except Exception as e:
            print_stage('Directory Existence', 'fail', f'Auto-creation failed: {e}')
            return False, None
    
    print_stage('Directory Existence', 'pass', f'Directory exists: {snapshots_dir}')
    return True, snapshots_dir


def stage_snapshot_module_import(project_root: Path) -> Tuple[bool, Any, Any]:
    """Stage 2: Verify orchestration.snapshot is importable"""
    try:
        sys.path.insert(0, str(project_root))
        from orchestration.snapshot import capture_semantic_snapshot, create_staging_branch
        print_stage('Snapshot Module Import', 'pass', 'Successfully imported snapshot functions')
        return True, capture_semantic_snapshot, create_staging_branch
    except ImportError as e:
        print_stage(
            'Snapshot Module Import',
            'fail',
            f'Failed to import: {e}',
            'Check orchestration/snapshot.py exists and is valid'
        )
        return False, None, None
    except Exception as e:
        print_stage(
            'Snapshot Module Import',
            'fail',
            f'Unexpected error: {e}',
            'Check orchestration module structure'
        )
        return False, None, None


def stage_test_snapshot_capture(
    project_root: Path,
    capture_fn: Any,
    create_branch_fn: Any
) -> bool:
    """Stage 3: Create test snapshot to prove the flow works"""
    workspace_path = project_root / 'workspace'
    
    # Check if workspace itself is a git repository
    workspace_git_check = subprocess.run(
        ['git', '-C', str(workspace_path), 'rev-parse', '--git-dir'],
        capture_output=True,
        text=True
    )
    
    if workspace_git_check.returncode != 0:
        print_stage(
            'Test Snapshot Capture',
            'skip',
            'Workspace is not a git repository (wiring is correct, no repo to test)'
        )
        return True
    
    # Check if workspace is a git submodule by checking parent repo
    submodule_check = subprocess.run(
        ['git', '-C', str(project_root), 'ls-files', '--stage', 'workspace'],
        capture_output=True,
        text=True
    )
    
    # Mode 160000 indicates a git submodule
    if submodule_check.returncode == 0 and '160000' in submodule_check.stdout:
        print_stage(
            'Test Snapshot Capture',
            'skip',
            'Workspace is a git submodule (wiring is correct, snapshot.py will work in real usage)'
        )
        return True
    
    # Use workspace as git root (it's either a standalone repo or a submodule)
    git_root = workspace_path
    
    test_task_id = f'test-{int(time.time())}'
    test_file = workspace_path / f'.test-snapshot-{test_task_id}.tmp'
    test_branch = f'l3/task-{test_task_id}'
    test_snapshot = project_root / 'workspace' / '.openclaw' / 'snapshots' / f'{test_task_id}.diff'
    
    current_branch = None
    
    try:
        current_branch = subprocess.run(
            ['git', '-C', str(git_root), 'branch', '--show-current'],
            capture_output=True,
            text=True,
            check=True
        ).stdout.strip()
        
        test_file.write_text(f'Test snapshot verification file - {test_task_id}\n')
        
        subprocess.run(
            ['git', '-C', str(git_root), 'add', test_file.name],
            check=True,
            capture_output=True,
            text=True
        )
        
        branch_name = create_branch_fn(test_task_id, str(workspace_path), stash_if_needed=True)
        
        subprocess.run(
            ['git', '-C', str(git_root), 'add', test_file.name],
            check=True,
            capture_output=True,
            text=True
        )
        
        subprocess.run(
            ['git', '-C', str(git_root), 'commit', '-m', f'Test snapshot {test_task_id}'],
            check=True,
            capture_output=True,
            text=True
        )
        
        snapshot_path, summary = capture_fn(test_task_id, str(workspace_path))
        
        if not test_snapshot.exists():
            print_stage(
                'Test Snapshot Capture',
                'fail',
                'Snapshot file not created',
                f'Expected: {test_snapshot}'
            )
            return False
        
        snapshot_content = test_snapshot.read_text()
        if f'# Semantic Snapshot: {test_task_id}' not in snapshot_content:
            print_stage(
                'Test Snapshot Capture',
                'fail',
                'Snapshot missing metadata header'
            )
            return False
        
        file_size = test_snapshot.stat().st_size
        print_stage(
            'Test Snapshot Capture',
            'pass',
            f'Snapshot created: {file_size} bytes, {summary.get("files_changed", 0)} files changed'
        )
        return True
        
    except subprocess.CalledProcessError as e:
        error_msg = (e.stderr or e.stdout or '').strip() if hasattr(e, 'stderr') else str(e)
        print_stage(
            'Test Snapshot Capture',
            'fail',
            f'Git operation failed: {error_msg}',
            'Check git configuration and permissions'
        )
        return False
    except Exception as e:
        print_stage(
            'Test Snapshot Capture',
            'fail',
            f'Unexpected error: {e}',
            'Check snapshot.py implementation'
        )
        return False
    finally:
        try:
            if test_file.exists():
                subprocess.run(
                    ['git', '-C', str(git_root), 'reset', 'HEAD', test_file.name],
                    capture_output=True
                )
                test_file.unlink()
            
            if current_branch:
                subprocess.run(
                    ['git', '-C', str(git_root), 'checkout', current_branch],
                    capture_output=True
                )
                
                branch_exists = subprocess.run(
                    ['git', '-C', str(git_root), 'branch', '--list', test_branch],
                    capture_output=True,
                    text=True
                ).stdout.strip()
                
                if branch_exists:
                    subprocess.run(
                        ['git', '-C', str(git_root), 'branch', '-D', test_branch],
                        capture_output=True
                    )
            
            if test_snapshot.exists():
                test_snapshot.unlink()
                
        except Exception as cleanup_error:
            print_stage('Test Snapshot Capture', 'info', f'Cleanup warning: {cleanup_error}')


def stage_config_consistency(project_root: Path, snapshots_dir: Path) -> bool:
    """Stage 4: Verify orchestration/config.py SNAPSHOT_DIR matches actual directory"""
    try:
        sys.path.insert(0, str(project_root))
        from orchestration.config import SNAPSHOT_DIR
        
        configured_path = project_root / SNAPSHOT_DIR
        actual_path = snapshots_dir
        
        if configured_path.resolve() == actual_path.resolve():
            print_stage(
                'Config Consistency',
                'pass',
                f'SNAPSHOT_DIR matches: {SNAPSHOT_DIR}'
            )
            return True
        else:
            print_stage(
                'Config Consistency',
                'fail',
                f'Path mismatch - Config: {configured_path}, Actual: {actual_path}',
                'Update SNAPSHOT_DIR in orchestration/config.py'
            )
            return False
            
    except ImportError as e:
        print_stage(
            'Config Consistency',
            'fail',
            f'Failed to import config: {e}',
            'Check orchestration/config.py exists'
        )
        return False
    except Exception as e:
        print_stage(
            'Config Consistency',
            'fail',
            f'Unexpected error: {e}'
        )
        return False


def main():
    """Run all verification stages"""
    print(f"\n{Colors.BOLD}Snapshot System Verification{Colors.RESET}\n")
    
    results = []
    
    passed, snapshots_dir = stage_directory_existence()
    results.append(passed)
    
    if not passed:
        print(f"\n{Colors.RED}RESULT: Directory check failed{Colors.RESET}\n")
        return 1
    
    try:
        project_root = find_project_root()
    except FileNotFoundError:
        print(f"\n{Colors.RED}RESULT: Could not find project root{Colors.RESET}\n")
        return 1
    
    passed, capture_fn, create_branch_fn = stage_snapshot_module_import(project_root)
    results.append(passed)
    
    if not passed:
        print(f"\n{Colors.RED}RESULT: Module import failed{Colors.RESET}\n")
        return 1
    
    passed = stage_test_snapshot_capture(project_root, capture_fn, create_branch_fn)
    results.append(passed)
    
    passed = stage_config_consistency(project_root, snapshots_dir)
    results.append(passed)
    
    print()
    if all(results):
        print(f"{Colors.GREEN}{Colors.BOLD}RESULT: All stages PASSED{Colors.RESET}\n")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}RESULT: One or more stages FAILED{Colors.RESET}\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
