"""
Semantic Snapshot System - Git staging branch workflow for L3 work isolation.

This module provides L2-side operations for managing L3 staging branches:
- Review git diffs before merging
- Merge staging branches into main with --no-ff
- Reject and cleanup staging branches
- Capture semantic snapshots as git diffs
"""

import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from .state_engine import JarvisState
from .project_config import load_project_config, get_snapshot_dir
from .logging import get_logger

logger = get_logger("snapshot")


def _memorize_review_decision(
    project_id: str,
    task_id: str,
    verdict: str,
    reasoning: str,
    diff_summary: str = "",
    skill_type: str = "",
) -> None:
    """
    Fire-and-forget helper that persists an L2 review decision to memU.

    Launches a daemon thread to POST the decision payload to /memorize so
    the call site is never blocked.  All exceptions are swallowed — memU
    unavailability must never prevent a merge or rejection from completing.

    Args:
        project_id:   OpenClaw project identifier (used as memU user_id scope).
        task_id:      L3 task identifier, e.g. "T-001".
        verdict:      "merge", "reject", or "conflict".
        reasoning:    Human-readable explanation of the decision.
        diff_summary: Optional short snippet from the git diff (truncated to 500 chars).
        skill_type:   L3 skill type, e.g. "code" or "test".
    """
    try:
        # Lazy imports — consistent with pool.py pattern
        from .project_config import get_memu_config
        from .memory_client import AgentType

        memu_cfg = get_memu_config()
        memu_api_url = memu_cfg.get("memu_api_url", "")

        if not memu_api_url or not project_id:
            logger.debug(
                "Skipping review memorization — memU URL or project_id not set",
                extra={"task_id": task_id, "verdict": verdict},
            )
            return

        # Build human-readable content string
        lines = [
            f"# L2 Review Decision: task {task_id}",
            f"Verdict: {verdict}",
            f"Task type: {skill_type}",
            f"Reasoning: {reasoning}",
        ]
        if diff_summary:
            lines.append(f"Diff summary:\n{diff_summary[:500]}")
        content = "\n".join(lines)

        base_url = memu_api_url.rstrip("/")
        payload = {
            "resource_url": content,
            "modality": "conversation",
            "user": {
                "user_id": project_id,
                "agent_type": AgentType.L2_PM.value,
            },
        }

        def _post() -> None:
            try:
                import httpx
                with httpx.Client(timeout=httpx.Timeout(10.0, connect=2.0)) as client:
                    client.post(f"{base_url}/memorize", json=payload)
            except Exception as exc:
                logger.warning(
                    "memU review memorization failed",
                    extra={"task_id": task_id, "verdict": verdict, "error": str(exc)},
                )

        t = threading.Thread(target=_post, daemon=True, name=f"memu-review-{task_id}")
        t.start()

    except Exception as exc:
        logger.warning(
            "Failed to launch review memorization thread",
            extra={"task_id": task_id, "verdict": verdict, "error": str(exc)},
        )


def _detect_default_branch(workspace: Path, project_id: Optional[str] = None) -> str:
    """
    Detect the default branch for a workspace.

    Resolution order:
    1. default_branch field in project.json (if project_id given)
    2. git symbolic-ref refs/remotes/origin/HEAD
    3. Check if 'main' exists locally
    4. Check if 'master' exists locally
    5. Fallback: return "main" with a warning

    Fresh detection on every call — no caching.
    """
    # 1. Project config
    if project_id is not None:
        try:
            config = load_project_config(project_id)
            branch = config.get("default_branch", "")
            if branch:
                return branch
        except (FileNotFoundError, ValueError):
            pass

    # 2. Git symbolic-ref
    try:
        result = subprocess.run(
            ['git', '-C', str(workspace), 'symbolic-ref', 'refs/remotes/origin/HEAD'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split('/')[-1]
    except Exception:
        pass

    # 3 & 4. Local branch existence
    for candidate in ('main', 'master'):
        result = subprocess.run(
            ['git', '-C', str(workspace), 'rev-parse', '--verify', candidate],
            capture_output=True
        )
        if result.returncode == 0:
            return candidate

    # 5. Last-resort fallback
    logger.warning("Could not detect default branch, falling back to main", extra={"workspace": str(workspace)})
    return "main"


class GitOperationError(Exception):
    """Raised when a git operation fails."""
    pass


def create_staging_branch(task_id: str, workspace_path: str, stash_if_needed: bool = True) -> str:
    """
    Create isolated staging branch for L3 work.
    
    Args:
        task_id: The task identifier
        workspace_path: Path to the workspace git repository
        stash_if_needed: If True, automatically stash uncommitted changes
        
    Returns:
        Branch name (l3/task-{task_id})
        
    Raises:
        GitOperationError: If workspace is not a git repo or branch creation fails
    """
    workspace = Path(workspace_path)
    branch_name = f"l3/task-{task_id}"
    
    # Check if workspace is a git repo
    try:
        subprocess.run(
            ['git', '-C', str(workspace), 'rev-parse', '--git-dir'],
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError:
        raise GitOperationError(f"Workspace {workspace_path} is not a git repository")
    
    # Check for uncommitted changes
    status_result = subprocess.run(
        ['git', '-C', str(workspace), 'status', '--porcelain'],
        capture_output=True,
        text=True
    )
    has_changes = bool(status_result.stdout.strip())
    
    if has_changes and stash_if_needed:
        # Stash changes before creating branch
        try:
            subprocess.run(
                ['git', '-C', str(workspace), 'stash', 'push', '-m', f'Auto-stash for {branch_name}'],
                check=True,
                capture_output=True,
                text=True
            )
            logger.info("Stashed uncommitted changes", extra={"task_id": task_id, "branch": branch_name})
        except subprocess.CalledProcessError as e:
            raise GitOperationError(f"Failed to stash uncommitted changes: {e.stderr}")
    elif has_changes:
        raise GitOperationError(
            f"Workspace has uncommitted changes. "
            f"Stash them first or use stash_if_needed=True"
        )
    
    default_branch = _detect_default_branch(workspace)
    
    # Check if branch already exists
    result = subprocess.run(
        ['git', '-C', str(workspace), 'branch', '--list', branch_name],
        capture_output=True,
        text=True
    )
    
    if result.stdout.strip():
        # Branch exists, checkout existing
        try:
            subprocess.run(
                ['git', '-C', str(workspace), 'checkout', branch_name],
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            raise GitOperationError(f"Failed to checkout existing branch {branch_name}: {e.stderr}")
    else:
        # Create new branch from default branch
        try:
            subprocess.run(
                ['git', '-C', str(workspace), 'checkout', '-b', branch_name, default_branch],
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr or "Unknown error"
            # Check for uncommitted changes error
            if "local changes" in error_msg.lower() or "overwritten by checkout" in error_msg.lower():
                raise GitOperationError(
                    f"Cannot create branch {branch_name}: uncommitted changes. "
                    f"Use stash_if_needed=True to auto-stash. Error: {error_msg}"
                )
            raise GitOperationError(f"Failed to create branch {branch_name}: {error_msg}")
    
    return branch_name


def capture_semantic_snapshot(task_id: str, workspace_path: str, project_id: str) -> Tuple[Path, Dict[str, Any]]:
    """
    Generate git diff as semantic snapshot.

    Captures diff against default branch and saves to .openclaw/snapshots/{task_id}.diff
    with metadata header.

    Args:
        task_id: The task identifier
        workspace_path: Path to the workspace git repository
        project_id: The project identifier (required — determines snapshot directory via get_snapshot_dir)

    Returns:
        Tuple of (snapshot_path, summary_dict)
        summary_dict contains: files_changed, insertions, deletions
        
    Raises:
        GitOperationError: If diff generation fails
    """
    workspace = Path(workspace_path)
    branch_name = f"l3/task-{task_id}"
    default_branch = _detect_default_branch(workspace)

    # Create snapshots directory
    snapshots_dir = get_snapshot_dir(project_id)
    snapshots_dir.mkdir(parents=True, exist_ok=True)

    # Generate diff against default branch
    try:
        diff_result = subprocess.run(
            ['git', '-C', str(workspace), 'diff', f'{default_branch}...HEAD'],
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        raise GitOperationError(f"Failed to generate diff for {branch_name}: {e.stderr}")
    
    # Get diff stats
    try:
        stat_result = subprocess.run(
            ['git', '-C', str(workspace), 'diff', '--stat', f'{default_branch}...HEAD'],
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        raise GitOperationError(f"Failed to generate diff stats: {e.stderr}")
    
    # Parse stats (last line typically has format: "X files changed, Y insertions(+), Z deletions(-)")
    stat_lines = stat_result.stdout.strip().split('\n')
    files_changed = 0
    insertions = 0
    deletions = 0
    
    if stat_lines:
        last_line = stat_lines[-1]
        if 'file' in last_line:
            parts = last_line.split(',')
            for part in parts:
                part = part.strip()
                if 'file' in part:
                    files_changed = int(part.split()[0])
                elif 'insertion' in part:
                    insertions = int(part.split()[0])
                elif 'deletion' in part:
                    deletions = int(part.split()[0])
    
    # Create metadata header
    timestamp = time.time()
    metadata_header = f"""# Semantic Snapshot: {task_id}
# Branch: {branch_name}
# Timestamp: {timestamp}
# Files Changed: {files_changed}
# Insertions: {insertions}
# Deletions: {deletions}
# Generated: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))}

"""
    
    # Save snapshot with metadata
    snapshot_path = snapshots_dir / f'{task_id}.diff'
    snapshot_content = metadata_header + diff_result.stdout
    snapshot_path.write_text(snapshot_content)
    
    summary = {
        'files_changed': files_changed,
        'insertions': insertions,
        'deletions': deletions,
        'snapshot_path': str(snapshot_path)
    }
    
    return snapshot_path, summary


def l2_review_diff(task_id: str, workspace_path: str) -> Dict[str, str]:
    """
    Generate human-readable diff summary for L2 review.
    
    Does NOT auto-merge - L2 makes the decision.
    
    Args:
        task_id: The task identifier
        workspace_path: Path to the workspace git repository
        
    Returns:
        Dictionary with 'stat' and 'diff' keys
        
    Raises:
        GitOperationError: If diff generation fails
    """
    workspace = Path(workspace_path)
    branch_name = f"l3/task-{task_id}"
    default_branch = _detect_default_branch(workspace)
    
    # Generate stat summary
    try:
        stat_result = subprocess.run(
            ['git', '-C', str(workspace), 'diff', '--stat', f'{default_branch}...{branch_name}'],
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        raise GitOperationError(f"Failed to generate diff stat: {e.stderr}")
    
    # Generate full diff
    try:
        diff_result = subprocess.run(
            ['git', '-C', str(workspace), 'diff', f'{default_branch}...{branch_name}'],
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        raise GitOperationError(f"Failed to generate diff: {e.stderr}")
    
    return {
        'stat': stat_result.stdout,
        'diff': diff_result.stdout
    }


def l2_merge_staging(
    task_id: str,
    workspace_path: str,
    state_file: Optional[Path] = None,
    reasoning: str = "",
    skill_type: str = "",
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Merge L3 staging branch into default branch with --no-ff.

    On conflict: aborts merge, returns conflict details, leaves branch intact.

    After a successful merge or conflict-abort, fires a non-blocking daemon
    thread to persist the decision (verdict="merge" or "conflict") to memU via
    `_memorize_review_decision`.  memU unavailability never blocks this function.

    Args:
        task_id:        The task identifier.
        workspace_path: Path to the workspace git repository.
        state_file:     Optional path to state file for status updates.
        reasoning:      Human-readable explanation of the merge decision.
        skill_type:     L3 skill type ("code" or "test") — stored in memU entry.
        project_id:     OpenClaw project identifier for memU scoping.  Safe to
                        omit — memorization is silently skipped when absent.

    Returns:
        Dictionary with 'success' (bool), 'message' (str), and optional 'conflicts' (list)

    Raises:
        GitOperationError: If checkout or branch deletion fails
    """
    workspace = Path(workspace_path)
    branch_name = f"l3/task-{task_id}"
    default_branch = _detect_default_branch(workspace)
    
    # Checkout default branch
    try:
        subprocess.run(
            ['git', '-C', str(workspace), 'checkout', default_branch],
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        raise GitOperationError(f"Failed to checkout {default_branch}: {e.stderr}")
    
    # Attempt merge with --no-ff
    merge_result = subprocess.run(
        ['git', '-C', str(workspace), 'merge', '--no-ff', branch_name, 
         '-m', f'Merge L3 task {task_id} into {default_branch}'],
        capture_output=True,
        text=True
    )
    
    if merge_result.returncode != 0:
        # Merge failed - likely conflicts
        # Abort the merge
        subprocess.run(
            ['git', '-C', str(workspace), 'merge', '--abort'],
            capture_output=True
        )

        # Get conflict details
        conflicts = []
        if 'CONFLICT' in merge_result.stdout or 'CONFLICT' in merge_result.stderr:
            conflict_text = merge_result.stdout + merge_result.stderr
            conflicts = [line for line in conflict_text.split('\n') if 'CONFLICT' in line]

        # Fire-and-forget: persist conflict decision to memU
        _memorize_review_decision(
            project_id=project_id or "",
            task_id=task_id,
            verdict="conflict",
            reasoning=reasoning or f"Merge conflict in task {task_id}",
            diff_summary=merge_result.stderr[:500],
            skill_type=skill_type,
        )

        return {
            'success': False,
            'message': f'Merge conflict detected for task {task_id}',
            'conflicts': conflicts,
            'stderr': merge_result.stderr
        }
    
    # Merge succeeded - delete staging branch
    try:
        subprocess.run(
            ['git', '-C', str(workspace), 'branch', '-d', branch_name],
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        # Branch deletion failed, but merge succeeded
        return {
            'success': True,
            'message': f'Merged task {task_id} successfully, but failed to delete branch: {e.stderr}',
            'branch_deleted': False
        }

    # Fire-and-forget: persist successful merge decision to memU
    _memorize_review_decision(
        project_id=project_id or "",
        task_id=task_id,
        verdict="merge",
        reasoning=reasoning,
        diff_summary="",
        skill_type=skill_type,
    )

    return {
        'success': True,
        'message': f'Successfully merged and deleted branch for task {task_id}',
        'branch_deleted': True
    }


def l2_reject_staging(
    task_id: str,
    workspace_path: str,
    state_file: Optional[Path] = None,
    reasoning: str = "",
    skill_type: str = "",
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Reject L3 staging branch without merging.

    Deletes the staging branch and updates task status to "rejected".

    After the branch is deleted, fires a non-blocking daemon thread to persist
    the rejection decision (verdict="reject") to memU via
    `_memorize_review_decision`.  memU unavailability never blocks this function.

    Args:
        task_id:        The task identifier.
        workspace_path: Path to the workspace git repository.
        state_file:     Optional path to state file for status updates.
        reasoning:      Human-readable explanation of the rejection decision.
        skill_type:     L3 skill type ("code" or "test") — stored in memU entry.
        project_id:     OpenClaw project identifier for memU scoping.  Safe to
                        omit — memorization is silently skipped when absent.

    Returns:
        Dictionary with 'success' (bool) and 'message' (str)

    Raises:
        GitOperationError: If branch deletion fails
    """
    workspace = Path(workspace_path)
    branch_name = f"l3/task-{task_id}"
    default_branch = _detect_default_branch(workspace)
    
    # Ensure we're not on the branch we're trying to delete
    try:
        subprocess.run(
            ['git', '-C', str(workspace), 'checkout', default_branch],
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        raise GitOperationError(f"Failed to checkout {default_branch}: {e.stderr}")
    
    # Force delete the staging branch
    try:
        subprocess.run(
            ['git', '-C', str(workspace), 'branch', '-D', branch_name],
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        raise GitOperationError(f"Failed to delete branch {branch_name}: {e.stderr}")

    # Fire-and-forget: persist rejection decision to memU
    _memorize_review_decision(
        project_id=project_id or "",
        task_id=task_id,
        verdict="reject",
        reasoning=reasoning,
        diff_summary="",
        skill_type=skill_type,
    )

    # Update state if state_file provided
    if state_file:
        try:
            js = JarvisState(state_file)
            js.update_task(task_id, 'rejected', f'L2 rejected staging branch {branch_name}')
        except Exception as e:
            # Don't fail the rejection if state update fails
            return {
                'success': True,
                'message': f'Rejected and deleted branch {branch_name}, but state update failed: {e}',
                'state_updated': False
            }
    
    return {
        'success': True,
        'message': f'Rejected and deleted branch {branch_name}',
        'state_updated': state_file is not None
    }


def cleanup_old_snapshots(workspace_path: str, project_id: str, max_snapshots: int = 100) -> Dict[str, Any]:
    """
    Keep last N snapshots, delete oldest when exceeded.

    Args:
        workspace_path: Path to the workspace (retained for API compatibility)
        project_id: The project identifier (required — determines snapshot directory via get_snapshot_dir)
        max_snapshots: Maximum number of snapshots to retain (default: 100)

    Returns:
        Dictionary with 'deleted_count' and 'remaining_count'
    """
    snapshots_dir = get_snapshot_dir(project_id)
    
    if not snapshots_dir.exists():
        return {'deleted_count': 0, 'remaining_count': 0}
    
    # Get all .diff files sorted by modification time (oldest first)
    snapshots = sorted(
        snapshots_dir.glob('*.diff'),
        key=lambda p: p.stat().st_mtime
    )
    
    total_snapshots = len(snapshots)
    deleted_count = 0
    
    # Delete oldest snapshots if we exceed max_snapshots
    if total_snapshots > max_snapshots:
        snapshots_to_delete = snapshots[:total_snapshots - max_snapshots]
        for snapshot in snapshots_to_delete:
            snapshot.unlink()
            deleted_count += 1
    
    remaining_count = total_snapshots - deleted_count
    
    return {
        'deleted_count': deleted_count,
        'remaining_count': remaining_count
    }
