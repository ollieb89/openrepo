"""
Tests for ensure_gateway(), is_bootstrap_mode(), and bootstrap error paths.

Covers:
- is_bootstrap_mode() reading OPENCLAW_BOOTSTRAP env var
- ensure_gateway() exits with code 1 and FATAL message when gateway is unhealthy
- ensure_gateway() succeeds silently when gateway is healthy
- ensure_gateway() skips check entirely in bootstrap mode
"""

import sys
import pytest

from openclaw.config import ensure_gateway, is_bootstrap_mode


# ---------------------------------------------------------------------------
# is_bootstrap_mode() tests
# ---------------------------------------------------------------------------


def test_is_bootstrap_mode_true_when_env_is_1(monkeypatch):
    """is_bootstrap_mode() returns True when OPENCLAW_BOOTSTRAP=1."""
    monkeypatch.setenv("OPENCLAW_BOOTSTRAP", "1")
    assert is_bootstrap_mode() is True


def test_is_bootstrap_mode_false_when_env_is_0(monkeypatch):
    """is_bootstrap_mode() returns False when OPENCLAW_BOOTSTRAP=0."""
    monkeypatch.setenv("OPENCLAW_BOOTSTRAP", "0")
    assert is_bootstrap_mode() is False


def test_is_bootstrap_mode_false_when_env_is_unset(monkeypatch):
    """is_bootstrap_mode() returns False when OPENCLAW_BOOTSTRAP is not set."""
    monkeypatch.delenv("OPENCLAW_BOOTSTRAP", raising=False)
    assert is_bootstrap_mode() is False


def test_is_bootstrap_mode_false_when_env_is_empty(monkeypatch):
    """is_bootstrap_mode() returns False when OPENCLAW_BOOTSTRAP is empty string."""
    monkeypatch.setenv("OPENCLAW_BOOTSTRAP", "")
    assert is_bootstrap_mode() is False


def test_is_bootstrap_mode_false_when_env_is_true_string(monkeypatch):
    """is_bootstrap_mode() returns False for 'true' (only '1' is accepted)."""
    monkeypatch.setenv("OPENCLAW_BOOTSTRAP", "true")
    assert is_bootstrap_mode() is False


# ---------------------------------------------------------------------------
# ensure_gateway() tests
# ---------------------------------------------------------------------------


def test_ensure_gateway_exits_when_gateway_unhealthy(monkeypatch):
    """ensure_gateway() raises SystemExit(1) when gateway is unhealthy and not in bootstrap mode."""
    monkeypatch.delenv("OPENCLAW_BOOTSTRAP", raising=False)

    async def _unhealthy(base_url="http://localhost:18789"):
        return False

    monkeypatch.setattr("openclaw.config.gateway_healthy", _unhealthy)

    with pytest.raises(SystemExit) as exc_info:
        ensure_gateway()

    assert exc_info.value.code == 1


def test_ensure_gateway_prints_fatal_message_when_unhealthy(monkeypatch, capsys):
    """ensure_gateway() prints FATAL error to stderr with 'openclaw gateway start' hint."""
    monkeypatch.delenv("OPENCLAW_BOOTSTRAP", raising=False)

    async def _unhealthy(base_url="http://localhost:18789"):
        return False

    monkeypatch.setattr("openclaw.config.gateway_healthy", _unhealthy)

    with pytest.raises(SystemExit):
        ensure_gateway()

    captured = capsys.readouterr()
    assert "FATAL" in captured.err
    assert "openclaw gateway start" in captured.err


def test_ensure_gateway_succeeds_when_gateway_healthy(monkeypatch):
    """ensure_gateway() succeeds silently when gateway is healthy."""
    monkeypatch.delenv("OPENCLAW_BOOTSTRAP", raising=False)

    async def _healthy(base_url="http://localhost:18789"):
        return True

    monkeypatch.setattr("openclaw.config.gateway_healthy", _healthy)

    # Should not raise
    ensure_gateway()


def test_ensure_gateway_skips_check_in_bootstrap_mode(monkeypatch):
    """ensure_gateway() skips gateway check entirely when in bootstrap mode."""
    monkeypatch.setenv("OPENCLAW_BOOTSTRAP", "1")

    # gateway_healthy would raise if called — ensures it's NOT called in bootstrap mode
    async def _should_not_be_called(base_url="http://localhost:18789"):
        raise AssertionError("gateway_healthy should not be called in bootstrap mode")

    monkeypatch.setattr("openclaw.config.gateway_healthy", _should_not_be_called)

    # Should not raise (no SystemExit, no AssertionError)
    ensure_gateway()


def test_ensure_gateway_bootstrap_mode_does_not_exit(monkeypatch):
    """ensure_gateway() does not call sys.exit() when in bootstrap mode."""
    monkeypatch.setenv("OPENCLAW_BOOTSTRAP", "1")

    async def _healthy(base_url="http://localhost:18789"):
        return True

    monkeypatch.setattr("openclaw.config.gateway_healthy", _healthy)

    # No exception expected
    ensure_gateway()
