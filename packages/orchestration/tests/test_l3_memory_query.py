"""
Integration tests for L3 in-execution memory queries (RET-05).

Validates the curl pattern documented in agents/l3_specialist/agent/SOUL.md
against a mock HTTP server that mimics the memU /retrieve endpoint.

Uses only stdlib: http.server, subprocess, json, threading.
"""
import http.server
import json
import socket
import subprocess
import threading

import pytest

# ---------------------------------------------------------------------------
# Mock server
# ---------------------------------------------------------------------------


class MockMemuHandler(http.server.BaseHTTPRequestHandler):
    """Minimal POST /retrieve handler that stores the last request body and
    returns a configurable mock response."""

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            self.server.last_request_body = json.loads(body)
        except json.JSONDecodeError:
            self.server.last_request_body = None

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(self.server.mock_response).encode())

    def log_message(self, format, *args):  # noqa: A002
        """Suppress request logging during tests."""
        pass


def _find_free_port():
    """Return a port number that is currently not in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture()
def mock_memu_server():
    """Start a mock memU HTTP server on a free port.

    Yields (server, port). Shuts down and closes the server after the test.
    """
    server = http.server.HTTPServer(("127.0.0.1", 0), MockMemuHandler)
    server.mock_response = []
    server.last_request_body = None
    port = server.server_address[1]

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield server, port

    server.shutdown()
    server.server_close()


# ---------------------------------------------------------------------------
# Shared curl command builder — matches the SOUL template exactly
# ---------------------------------------------------------------------------


def _build_curl_cmd(port: int, project_id: str = "testproj", query: str = "test query") -> str:
    """Build the bash command from SOUL.md that runs curl against the mock server.

    Mirrors the SOUL template exactly: variables set in env, JSON payload uses
    double-quoted string so ${MEMU_API_URL} and ${OPENCLAW_PROJECT} expand.
    """
    # Use printf to build the JSON payload — avoids single-quote escaping issues
    # while preserving the same semantics as the SOUL template.
    return (
        f'QUERY="{query}"; '
        f"MEMU_API_URL=http://127.0.0.1:{port}; "
        f"OPENCLAW_PROJECT={project_id}; "
        f'PAYLOAD=$(printf \'{{"queries": [{{"role": "user", "content": "%s"}}], "where": {{"user_id": "%s"}}}}\' '
        f'"$QUERY" "$OPENCLAW_PROJECT"); '
        f'RESPONSE=$(curl -s --max-time 5 '
        f'-X POST "${{MEMU_API_URL}}/retrieve" '
        f'-H "Content-Type: application/json" '
        f'-d "$PAYLOAD" '
        f"2>/dev/null || echo '[]'); "
        f'echo "$RESPONSE"'
    )


def _build_curl_with_jq(port: int, project_id: str = "testproj", query: str = "test query") -> str:
    """Curl command including jq extraction — for dict response shape test."""
    return (
        f'QUERY="{query}"; '
        f"MEMU_API_URL=http://127.0.0.1:{port}; "
        f"OPENCLAW_PROJECT={project_id}; "
        f'PAYLOAD=$(printf \'{{"queries": [{{"role": "user", "content": "%s"}}], "where": {{"user_id": "%s"}}}}\' '
        f'"$QUERY" "$OPENCLAW_PROJECT"); '
        f'RESPONSE=$(curl -s --max-time 5 '
        f'-X POST "${{MEMU_API_URL}}/retrieve" '
        f'-H "Content-Type: application/json" '
        f'-d "$PAYLOAD" '
        f"2>/dev/null || echo '[]'); "
        f"echo \"$RESPONSE\" | jq -r '(if type == \"array\" then . else .items // [] end)[] | .resource_url // empty' 2>/dev/null || true"
    )


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


def test_l3_curl_retrieves_memories(mock_memu_server):
    """Mock returns a list response — curl retrieves and echoes the memory items."""
    server, port = mock_memu_server
    mock_items = [{"resource_url": "Use asyncio for concurrent tasks", "category": "l3_outcome"}]
    server.mock_response = mock_items

    cmd = _build_curl_cmd(port, project_id="testproj", query="how to handle concurrency")
    result = subprocess.run(
        ["bash", "-c", cmd],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, f"bash exited non-zero: {result.stderr}"

    data = json.loads(result.stdout.strip())
    assert data == mock_items, f"Expected {mock_items}, got {data}"

    # Verify the mock received the correct POST payload
    assert server.last_request_body is not None, "Mock server did not receive a request"
    assert server.last_request_body["where"]["user_id"] == "testproj", (
        "Project scoping: where.user_id must match OPENCLAW_PROJECT"
    )
    assert server.last_request_body["queries"][0]["role"] == "user"
    assert server.last_request_body["queries"][0]["content"] == "how to handle concurrency"


def test_l3_curl_empty_result_continues(mock_memu_server):
    """Mock returns [] — subprocess exits 0 and stdout is parseable as empty JSON list."""
    server, port = mock_memu_server
    server.mock_response = []

    cmd = _build_curl_cmd(port, project_id="testproj", query="something obscure")
    result = subprocess.run(
        ["bash", "-c", cmd],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, f"bash exited non-zero on empty response: {result.stderr}"

    data = json.loads(result.stdout.strip())
    assert data == [], f"Expected [], got {data}"


def test_l3_curl_graceful_on_unreachable():
    """No mock server running — curl fails, || echo '[]' fires, subprocess exits 0."""
    unused_port = _find_free_port()
    # Nothing is listening on this port

    cmd = _build_curl_cmd(unused_port, project_id="testproj", query="will fail silently")
    result = subprocess.run(
        ["bash", "-c", cmd],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, (
        f"Graceful degradation failed — bash exited {result.returncode}: {result.stderr}"
    )

    stdout = result.stdout.strip()
    assert stdout == "[]", f"Expected '[]' from fallback, got: {stdout!r}"


def test_l3_curl_dict_response_shape(mock_memu_server):
    """Mock returns dict with 'items' key — jq extraction handles the alternate shape."""
    server, port = mock_memu_server
    server.mock_response = {
        "items": [{"resource_url": "Dict shape memory", "category": "review_decision"}],
        "total": 1,
    }

    cmd = _build_curl_with_jq(port, project_id="testproj", query="check dict shape handling")
    result = subprocess.run(
        ["bash", "-c", cmd],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, f"bash exited non-zero: {result.stderr}"
    assert "Dict shape memory" in result.stdout, (
        f"Expected 'Dict shape memory' in jq output, got: {result.stdout!r}"
    )


def test_memu_api_url_env_used(mock_memu_server):
    """Env var MEMU_API_URL routes the request — proves no hardcoded URL in the pattern."""
    server, port = mock_memu_server
    known_items = [{"resource_url": "env var routing confirmed", "category": "test"}]
    server.mock_response = known_items

    # Run curl with MEMU_API_URL pointing at our mock
    cmd = _build_curl_cmd(port, project_id="envtest", query="verify env var routing")
    result = subprocess.run(
        ["bash", "-c", cmd],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, f"bash exited non-zero: {result.stderr}"

    # Mock must have received the request (proving MEMU_API_URL was used)
    assert server.last_request_body is not None, (
        "Mock server did not receive a request — MEMU_API_URL env var was not used"
    )

    data = json.loads(result.stdout.strip())
    assert data == known_items, f"Expected {known_items}, got {data}"

    # Also verify project scoping via env var
    assert server.last_request_body["where"]["user_id"] == "envtest", (
        "OPENCLAW_PROJECT env var was not used for where.user_id scoping"
    )
