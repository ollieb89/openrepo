"""
Static analysis tests for L3 entrypoint SIGTERM handling and spawn stop_timeout.

These tests verify the graceful shutdown implementation (REL-04, REL-05) without
requiring a running Docker daemon or container. All checks are file-content based.
"""

import pytest
from pathlib import Path

# Navigate from packages/orchestration/tests/ up to the repo root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


@pytest.fixture
def entrypoint_content():
    return (PROJECT_ROOT / "docker" / "l3-specialist" / "entrypoint.sh").read_text()


@pytest.fixture
def dockerfile_content():
    return (PROJECT_ROOT / "docker" / "l3-specialist" / "Dockerfile").read_text()


@pytest.fixture
def spawn_content():
    return (PROJECT_ROOT / "skills" / "spawn" / "spawn.py").read_text()


def test_entrypoint_has_sigterm_trap(entrypoint_content):
    """SIGTERM trap must be registered using the _trap_sigterm handler."""
    assert "trap '_trap_sigterm' TERM" in entrypoint_content, (
        "entrypoint.sh must register a TERM trap via: trap '_trap_sigterm' TERM"
    )


def test_entrypoint_trap_is_idempotent(entrypoint_content):
    """Trap handler must be idempotent — double SIGTERM should not cause duplicate state writes."""
    assert "_shutdown_requested" in entrypoint_content, (
        "entrypoint.sh must define _shutdown_requested flag for idempotency"
    )
    assert "[[ $_shutdown_requested -eq 1 ]] && return" in entrypoint_content, (
        "entrypoint.sh trap must guard against duplicate invocations with early return"
    )


def test_entrypoint_exits_143(entrypoint_content):
    """Trap handler must exit with code 143 (128 + SIGTERM signal 15)."""
    assert "exit 143" in entrypoint_content, (
        "entrypoint.sh trap must exit with code 143 (128 + 15 for SIGTERM)"
    )


def test_entrypoint_trap_before_work(entrypoint_content):
    """Trap must be registered before any work begins (before update_state 'starting')."""
    lines = entrypoint_content.splitlines()

    trap_line = None
    starting_line = None

    for i, line in enumerate(lines, start=1):
        if "trap '_trap_sigterm' TERM" in line and trap_line is None:
            trap_line = i
        if 'update_state "starting"' in line and starting_line is None:
            starting_line = i

    assert trap_line is not None, "trap '_trap_sigterm' TERM not found in entrypoint.sh"
    assert starting_line is not None, 'update_state "starting" not found in entrypoint.sh'
    assert trap_line < starting_line, (
        f"Trap registered at line {trap_line} must be BEFORE update_state 'starting' at line {starting_line}"
    )


def test_dockerfile_exec_form(dockerfile_content):
    """Dockerfile ENTRYPOINT must use JSON array (exec) form, not shell form.

    Exec form ensures bash is PID 1 and receives SIGTERM directly from Docker.
    Shell form wraps in /bin/sh -c which intercepts signals and breaks graceful shutdown.
    """
    assert 'ENTRYPOINT ["bash", "/entrypoint.sh"]' in dockerfile_content, (
        'Dockerfile must use exec form: ENTRYPOINT ["bash", "/entrypoint.sh"]'
    )


def test_spawn_has_stop_timeout(spawn_content):
    """spawn.py must set stop_timeout=30 in container_config to grant 30s grace period."""
    assert '"stop_timeout": 30' in spawn_content, (
        'spawn.py container_config must contain "stop_timeout": 30'
    )


def test_entrypoint_child_backgrounded(entrypoint_content):
    """CLI runtime must run as a background process so PID 1 (bash) can receive SIGTERM.

    Pattern: command & followed by _child_pid=$! and wait to block until child finishes.
    """
    assert "_child_pid=$!" in entrypoint_content, (
        "entrypoint.sh must capture CLI runtime PID via _child_pid=$!"
    )
    assert "wait $_child_pid" in entrypoint_content, (
        "entrypoint.sh must use 'wait $_child_pid' to block while CLI runtime runs"
    )
