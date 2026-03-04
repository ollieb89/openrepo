"""
Tests that agents.main.skills.route_directive is importable and exposes
the documented public API: DirectiveRouter, RouteDecision, RouteType.

INT-02: RouteType enum and RouteDecision dataclass must exist in router.py
        so that the package __init__.py can re-export them without ImportError.
"""
import sys
import dataclasses
from pathlib import Path

# Make the repo root importable so `agents.*` can be imported as packages
REPO_ROOT = str(Path(__file__).resolve().parents[3])
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Make openclaw importable within route_directive's own imports
OPENCLAW_SRC = str(Path(__file__).resolve().parents[3] / "packages" / "orchestration" / "src")
if OPENCLAW_SRC not in sys.path:
    sys.path.insert(0, OPENCLAW_SRC)

import pytest


def test_import_route_directive():
    """import agents.main.skills.route_directive must succeed without ImportError."""
    import agents.main.skills.route_directive  # noqa: F401


def test_import_route_decision():
    """RouteDecision must be importable from agents.main.skills.route_directive."""
    from agents.main.skills.route_directive import RouteDecision  # noqa: F401


def test_import_route_type():
    """RouteType must be importable from agents.main.skills.route_directive."""
    from agents.main.skills.route_directive import RouteType  # noqa: F401


def test_route_type_values():
    """RouteType must have exactly the 5 documented members."""
    from agents.main.skills.route_directive import RouteType

    expected = {"TO_PM", "SPAWN_L3", "COORDINATE", "ESCALATE", "QUEUE"}
    actual = {m.name for m in RouteType}
    assert actual == expected, f"RouteType members mismatch: {actual}"


def test_route_decision_fields():
    """RouteDecision must be a dataclass with the 6 required fields."""
    from agents.main.skills.route_directive import RouteDecision

    assert dataclasses.is_dataclass(RouteDecision)
    field_names = {f.name for f in dataclasses.fields(RouteDecision)}
    required = {"route_type", "target", "reasoning", "confidence", "priority", "alternatives"}
    assert required.issubset(field_names), f"Missing fields: {required - field_names}"


def test_directive_router_instantiation():
    """DirectiveRouter(config, swarm_query=None) must succeed with a minimal dict config."""
    from agents.main.skills.route_directive import DirectiveRouter

    router = DirectiveRouter({}, swarm_query=None)
    assert router is not None


def test_route_returns_route_decision():
    """router.route(directive) must return a RouteDecision (sync, not coroutine)."""
    from agents.main.skills.route_directive import DirectiveRouter, RouteDecision, RouteType
    import inspect

    router = DirectiveRouter({}, swarm_query=None)
    result = router.route("test directive")

    # Must NOT be a coroutine — route() must be sync
    assert not inspect.iscoroutine(result), "route() must be synchronous, not async"
    assert isinstance(result, RouteDecision)
    assert isinstance(result.route_type, RouteType)
    assert 0.0 <= result.confidence <= 1.0, f"confidence out of range: {result.confidence}"
