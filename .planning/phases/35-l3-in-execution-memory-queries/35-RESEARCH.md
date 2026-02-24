# Phase 35: L3 In-Execution Memory Queries - Research

**Researched:** 2026-02-24
**Domain:** HTTP client patterns inside Docker containers, SOUL template documentation, integration test design with mock HTTP endpoints
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Query interface design**
- Raw HTTP calls directly against MEMU_API_URL — no wrapper scripts, no helper libraries
- Query payload is text-only — L3 sends a natural language query string
- SOUL template gets a new section with a concrete example: endpoint URL, HTTP method, payload format, and expected response shape
- Runtime-agnostic: works with claude-code, codex, gemini-cli (all support HTTP)

**Failure & fallback behavior**
- If memU is unreachable: fail silently, continue task execution — consistent with existing spawn.py graceful degradation pattern
- If memU returns empty results: log a debug-level note that no memories matched (for observability / future tuning)
- 5-second timeout on all memory queries — prevents slow memU from eating into task skill timeouts (code: 600s, test: 300s)
- Timeout guidance included explicitly in SOUL example

**Query scoping & filtering**
- Agent context (project_id, task_type from container env vars) included in query payload automatically — helps memU rank relevance
- Result count uses server-side default — L3 doesn't specify limits
- Free-text semantic search only — no category filters, no structured query params
- Project scoping strategy: Claude's discretion

**Usage patterns & triggers**
- SOUL includes suggested triggers: "Consider querying memU when you encounter an unfamiliar pattern, hit an error, or need project conventions"
- No hard limit on number of queries per task execution — let agents use it freely
- On-demand usage — agents decide when extra context would help

**Testing approach**
- Integration test that proves L3 can query memU from inside a container
- Uses a mock HTTP endpoint (no live memU dependency) that mimics the retrieve response
- Validates success criteria #1: POST to retrieve endpoint returns relevant memory items

### Claude's Discretion
- Project scoping strategy (project-only vs global fallback)
- Exact SOUL template wording and placement
- Mock endpoint implementation details
- How agent context fields map to memU API parameters

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| RET-05 | L3 containers can query memU service during execution via HTTP for task-specific lookups | Covered by: SOUL template documentation of the retrieve API, curl invocation pattern, 5s timeout flag, graceful degradation approach, and integration test design with mock HTTP server |
</phase_requirements>

---

## Summary

Phase 35 adds mid-execution memory query capability to L3 containers. The work has two surfaces: (1) documenting the capability in the L3 SOUL template so agents know how and when to call it, and (2) writing an integration test that proves a container can reach a mock memU endpoint and handle both success and empty-result cases correctly.

The retrieve API shape is already fully defined in `docker/memory/memory_service/routers/retrieve.py` and `models.py`. The endpoint is `POST /retrieve` with `{"queries": [{"role": "user", "content": "..."}], "where": {"user_id": "<project_id>"}}`. This is identical to the shape used in `memory_client.py` and `spawn.py:_retrieve_memories_sync`. No new API work is needed — L3 just calls the same endpoint that already exists.

The container environment is already fully wired: `MEMU_API_URL` is set at spawn time (rewritten from localhost to `openclaw-memory` DNS hostname by `_rewrite_memu_url_for_container`), the container is on `openclaw-net` bridge network, `OPENCLAW_PROJECT` identifies the project for scoping, and `SKILL_HINT` identifies task type. `curl` is available in the L3 image (`docker/l3-specialist/Dockerfile` installs `curl` and `jq`). All three CI runtimes (claude-code, codex, gemini-cli) support raw HTTP calls.

**Primary recommendation:** Two-task phase — (1) add a `## Memory Queries` section to `agents/l3_specialist/agent/SOUL.md` with a copy-pasteable curl example and usage guidance; (2) write a new test file `tests/test_l3_memory_query.py` covering success, empty-result, and network-failure paths using a mock HTTP server that mimics the retrieve response shape.

---

## Standard Stack

### Core

| Tool/Pattern | Version | Purpose | Why Standard |
|---|---|---|---|
| `curl` + `jq` | pre-installed in Dockerfile | L3 agent makes HTTP POST; parses JSON response | Already in L3 image; runtime-agnostic; no new dependencies |
| `MEMU_API_URL` env var | already injected by spawn.py | Base URL for all memU calls inside container | Established in Phase 33; rewritten to Docker DNS hostname |
| `OPENCLAW_PROJECT` env var | already injected by spawn.py | project_id for `where.user_id` scoping | Established in Phase 33 |
| `SKILL_HINT` env var | already injected by spawn.py | task_type context in query payload | Already in container env |

### Supporting

| Tool/Pattern | Version | Purpose | When to Use |
|---|---|---|---|
| `http.server` (stdlib) or `pytest-httpserver` | stdlib / pip | Mock HTTP endpoint in integration test | For testing L3 → memU interaction without a live service |
| Python `threading.Thread` | stdlib | Run mock server in background thread during test | Lightweight, no extra dependency |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|---|---|---|
| `curl` in SOUL example | `python3 -c "import urllib.request..."` | curl is more readable and is already installed in the image |
| `pytest-httpserver` | stdlib `http.server` in thread | pytest-httpserver is cleaner but adds a dependency; stdlib is sufficient for this use case |
| Python in container for HTTP | curl | Python is available but curl is more natural for a shell script context and is what SOUL should show |

**Installation:** No new packages required. `curl` and `jq` already in the L3 image. Tests use Python stdlib `http.server` or a lightweight mock.

---

## Architecture Patterns

### What Already Exists (don't re-implement)

The retrieve API shape is locked and implemented:

```
POST /retrieve
Content-Type: application/json

{
  "queries": [{"role": "user", "content": "<natural language query>"}],
  "where": {"user_id": "<project_id>"}
}
```

Response shape (from `memory_client.py` + `retrieve.py`):
- List of memory dicts: `[{"resource_url": "...", "category": "...", ...}, ...]`
- Or dict with `"items"` key: `{"items": [...], "total": N}`
- Empty result: `[]` or `{"items": []}`

### Pattern 1: SOUL Documentation Block

**What:** A new `## Memory Queries` section in `agents/l3_specialist/agent/SOUL.md` that provides copy-pasteable curl example and usage guidance.

**When to use:** L3 agent encounters unfamiliar pattern, hits an error, or needs project conventions.

**Example SOUL section:**

```markdown
## Memory Queries

You can query the project's memory service during execution for task-specific context.
This is independent of the memories injected at spawn time — use it for on-demand lookups.

**When to query:** Consider querying when you encounter an unfamiliar pattern, hit an error,
or need to check project conventions before making a decision.

**How to query (5-second timeout enforced):**

```bash
# Query memU for relevant context
QUERY="your natural language question here"
RESPONSE=$(curl -s --max-time 5 \
  -X POST "${MEMU_API_URL}/retrieve" \
  -H "Content-Type: application/json" \
  -d "{\"queries\": [{\"role\": \"user\", \"content\": \"${QUERY}\"}], \
       \"where\": {\"user_id\": \"${OPENCLAW_PROJECT}\"}}" \
  2>/dev/null || echo "[]")

# Extract memory texts (jq is available in the container)
echo "$RESPONSE" | jq -r '.[] | .resource_url // empty' 2>/dev/null || true
```

If memU is unreachable or returns no results, continue task execution — memory queries are advisory only.
A debug note will be emitted if no results match.
```

**Note:** The jq extraction handles both list response `[...]` and the `{"items": [...]}` dict shape. The `|| echo "[]"` ensures curl failure returns parseable JSON. The `2>/dev/null || true` at the jq step ensures parse failure does not abort the task.

### Pattern 2: Project Scoping Strategy (Claude's Discretion)

**Decision:** Use `where: {"user_id": OPENCLAW_PROJECT}` only — project-scoped retrieval, no global fallback.

**Rationale:** This is identical to how `memory_client.py` and `spawn.py:_retrieve_memories_sync` scope queries. The memU API maps `user_id` to `project_id` for isolation. A global fallback would risk cross-project contamination, which is explicitly out of scope in REQUIREMENTS.md ("Shared memory pool across projects — Cross-project contamination; violates per-project isolation model").

### Pattern 3: Agent Context in Query Payload

**Decision:** The query payload `where` clause uses `{"user_id": OPENCLAW_PROJECT}`. The natural language query string itself can include context like task type (the agent constructs this from `$SKILL_HINT` and the task description if relevant).

The `where` clause does NOT include `agent_type` — the existing retrieve endpoint only scopes by `user_id`. Adding extra where fields would require API changes outside this phase scope.

**Example query string with context:** `"error handling pattern for ${SKILL_HINT} task — how have similar tasks been resolved?"`

### Pattern 4: Integration Test with Mock HTTP Server

**What:** `tests/test_l3_memory_query.py` uses Python's `http.server.BaseHTTPRequestHandler` in a background thread to stand up a mock `/retrieve` endpoint. The test spawns a minimal shell command (not a full Docker container) that calls `curl` against the mock.

**Why not a full Docker integration test:** Full container spawn requires a running Docker daemon and the built L3 image — too heavy for a unit/integration test suite that currently runs in 0.20s without Docker. The decision from CONTEXT.md specifies "mock HTTP endpoint (no live memU dependency)".

**Test approach:**
1. Start mock HTTP server on a free localhost port
2. Set `MEMU_API_URL=http://localhost:<port>` in subprocess env
3. Run `curl` subprocess with the exact command from the SOUL example
4. Assert mock received the correct POST payload
5. Assert curl output contains expected memory items
6. Test the empty-result case (mock returns `[]`)
7. Test the failure case (mock not running / wrong port → curl fails → `|| echo "[]"` returns `[]`)

### Anti-Patterns to Avoid

- **Don't add a Python helper script to the image:** Decision locked — raw HTTP only, no wrapper scripts.
- **Don't hard-code the memU URL in SOUL:** SOUL must reference `$MEMU_API_URL` env var, not a fixed hostname.
- **Don't use `--fail` flag in curl:** With `--fail`, a 503/empty response would exit non-zero and could propagate up. Use `|| echo "[]"` pattern instead to guarantee silent degradation.
- **Don't omit `--max-time`:** Without a timeout flag, a slow memU hangs the task. 5 seconds is the locked decision.
- **Don't parse JSON with grep/awk:** Use `jq` (installed in image). Simpler and handles edge cases.
- **Don't test with a live memU service:** Adds external dependency to test suite. Mock is the correct pattern.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| HTTP client in container | Custom shell HTTP library | curl (pre-installed) | Already in image; battle-tested |
| JSON parsing in shell | grep/awk | jq (pre-installed) | Handles nested structures and missing keys |
| Mock HTTP server | Custom socket code | stdlib `http.server.BaseHTTPRequestHandler` | 10 lines of code; no dependency |
| memU API endpoint | New endpoint | Existing `POST /retrieve` | Fully implemented; shape verified in codebase |

**Key insight:** This phase is almost entirely documentation + testing. The hard work (network wiring, URL rewriting, retrieve endpoint) was done in Phases 29 and 33. Phase 35 teaches agents to use what already exists.

---

## Common Pitfalls

### Pitfall 1: curl `--fail` Flag Abort
**What goes wrong:** Using `curl --fail` causes curl to return a non-zero exit code on HTTP 4xx/5xx responses, which — without error handling — propagates up and fails the task.
**Why it happens:** `--fail` is commonly recommended for scripts but here the design requirement is silent degradation.
**How to avoid:** Do not use `--fail`. Use `2>/dev/null || echo "[]"` to capture both network failures and non-2xx responses as empty JSON.
**Warning signs:** Task failures that trace back to curl exit code in logs.

### Pitfall 2: Missing `--max-time` Timeout
**What goes wrong:** curl blocks indefinitely if memU is slow. Code task timeout is 600s, test task timeout is 300s — a hanging curl eats into this budget.
**Why it happens:** curl default is no timeout.
**How to avoid:** Always include `--max-time 5` in the SOUL curl example. Document this in SOUL.
**Warning signs:** Task execution time dramatically longer than expected; SOUL example shows curl without timeout.

### Pitfall 3: jq Parsing Both Response Shapes
**What goes wrong:** memU can return `[...]` (list) or `{"items": [...]}` (dict). A jq expression like `.[] | .resource_url` fails on the dict form.
**Why it happens:** The retrieve endpoint has two response shapes (verified in `memory_client.py` which handles both).
**How to avoid:** Use `jq -r '(if type == "array" then . else .items end) | .[] | .resource_url // empty'`. Or keep it simple: the SOUL example can just show `echo "$RESPONSE"` and let the LLM parse the output — the agent is reading the response, not extracting it in a pipeline.
**Warning signs:** jq errors in container output when response shape is dict.

### Pitfall 4: SOUL Section Placement
**What goes wrong:** If the Memory Queries section is placed before existing critical constraints (workspace scope, branch discipline), agents might deprioritize them.
**Why it happens:** LLMs follow recency bias — later sections get less attention.
**How to avoid:** Append the new section at the end of SOUL.md, after all existing constraint sections. This is consistent with how spawn.py appends memory context at the end of the base SOUL.
**Warning signs:** SOUL section appears before "## Security & Isolation".

### Pitfall 5: Test Suite Becoming Slow
**What goes wrong:** Integration test starts a real HTTP server that isn't cleaned up, leaving ports bound between test runs.
**Why it happens:** Missing `server.server_close()` in test teardown.
**How to avoid:** Use `try/finally` or pytest fixture with `yield` to guarantee server shutdown. Bind to port 0 (OS assigns a free port) to avoid hardcoded port conflicts.
**Warning signs:** "Address already in use" errors on repeated test runs.

---

## Code Examples

### SOUL curl Command (verified against existing API shape)

```bash
# Source: docker/memory/memory_service/routers/retrieve.py + models.py
QUERY="your natural language question here"
RESPONSE=$(curl -s --max-time 5 \
  -X POST "${MEMU_API_URL}/retrieve" \
  -H "Content-Type: application/json" \
  -d "{\"queries\": [{\"role\": \"user\", \"content\": \"${QUERY}\"}], \
       \"where\": {\"user_id\": \"${OPENCLAW_PROJECT}\"}}" \
  2>/dev/null || echo "[]")
echo "$RESPONSE" | jq -r '(if type == "array" then . else .items // [] end)[] | .resource_url // empty' 2>/dev/null || true
```

### Mock HTTP Server for Tests (stdlib pattern)

```python
# Source: Python stdlib http.server documentation
import http.server
import json
import threading

class MockMemuHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        self.server.last_request_body = json.loads(body)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        response = self.server.mock_response
        self.wfile.write(json.dumps(response).encode())

    def log_message(self, format, *args):
        pass  # Suppress test output

def start_mock_server(mock_response):
    server = http.server.HTTPServer(("127.0.0.1", 0), MockMemuHandler)
    server.mock_response = mock_response
    server.last_request_body = None
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, server.server_address[1]  # returns server + assigned port
```

### Test Pattern for RET-05 Validation

```python
import subprocess, json, os

def test_l3_curl_retrieves_memories():
    """L3 curl command returns memory items from mock endpoint."""
    mock_items = [{"resource_url": "Use asyncio for concurrent tasks", "category": "l3_outcome"}]
    server, port = start_mock_server(mock_items)
    try:
        result = subprocess.run(
            ["bash", "-c",
             f'RESPONSE=$(curl -s --max-time 5 -X POST "http://127.0.0.1:{port}/retrieve" '
             f'-H "Content-Type: application/json" '
             f'-d \'{{"queries": [{{"role": "user", "content": "test query"}}], '
             f'"where": {{"user_id": "testproj"}}}}\' 2>/dev/null || echo "[]"); '
             f'echo "$RESPONSE"'],
            capture_output=True, text=True, timeout=10
        )
        data = json.loads(result.stdout.strip())
        assert data == mock_items
        # Verify request payload scoping
        assert server.last_request_body["where"]["user_id"] == "testproj"
    finally:
        server.shutdown()
        server.server_close()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| SOUL context only at spawn time | Spawn-time injection (Phase 29/33) + on-demand mid-execution queries (Phase 35) | Phase 35 | Agents can fetch context exactly when needed, not just at start |
| localhost memU URL | Docker DNS `openclaw-memory` hostname (Phase 33) | Phase 33 | Containers can reach memU without host networking |

---

## Open Questions

1. **jq response shape handling in SOUL**
   - What we know: `memory_client.py` handles both list and `{"items": [...]}` dict shapes
   - What's unclear: Which shape the live memU service returns most often (Phase 26 comment says "Shape can be a list or a dict with an 'items' key")
   - Recommendation: SOUL example should use the safe jq expression that handles both shapes; alternatively simplify to just `echo "$RESPONSE"` and let the LLM process it naturally

2. **Agent context enrichment in query string**
   - What we know: `where` clause only takes `user_id`; agent_type not supported as a filter
   - What's unclear: Whether agents should explicitly mention `$SKILL_HINT` in their query string
   - Recommendation: SOUL can suggest including skill type in the query string naturally (e.g., "common errors in {skill_hint} tasks"), not as a structured field

---

## Validation Architecture

Nyquist validation is not configured in `.planning/config.json` (no `workflow.nyquist_validation` key). However, this phase has a clear testable success criterion and an existing test suite (58 tests, 0.20s runtime). Including test mapping for planning clarity.

### Test Framework

| Property | Value |
|---|---|
| Framework | pytest (stdlib unittest.mock) |
| Config file | none — pytest auto-discovers |
| Quick run command | `python3 -m pytest tests/test_l3_memory_query.py -v` |
| Full suite command | `python3 -m pytest tests/ -v` |
| Estimated runtime | ~0.5s (mock server starts/stops per test) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| RET-05 | L3 curl POST to /retrieve returns memory items | integration (mock HTTP) | `python3 -m pytest tests/test_l3_memory_query.py::test_l3_curl_retrieves_memories -x` | Wave 0 gap |
| RET-05 | L3 continues if memU unreachable (fail silently) | integration (mock HTTP) | `python3 -m pytest tests/test_l3_memory_query.py::test_l3_curl_graceful_on_unreachable -x` | Wave 0 gap |
| RET-05 | Empty result from memU — debug log emitted, task continues | integration (mock HTTP) | `python3 -m pytest tests/test_l3_memory_query.py::test_l3_curl_empty_result_continues -x` | Wave 0 gap |
| RET-05 | MEMU_API_URL env var resolves to reachable endpoint | integration (mock HTTP) | `python3 -m pytest tests/test_l3_memory_query.py::test_memu_api_url_env_used -x` | Wave 0 gap |

### Wave 0 Gaps

- `tests/test_l3_memory_query.py` — new test file covering RET-05 (all four test cases above)
- No framework install needed — stdlib `http.server` + existing pytest setup

---

## Sources

### Primary (HIGH confidence)
- `/home/ollie/.openclaw/docker/memory/memory_service/routers/retrieve.py` — exact POST /retrieve endpoint signature and response handling
- `/home/ollie/.openclaw/docker/memory/memory_service/models.py` — `RetrieveRequest` Pydantic model confirming payload shape
- `/home/ollie/.openclaw/orchestration/memory_client.py` — confirmed retrieve payload: `{"queries": [{"role":"user","content":"..."}], "where": {"user_id": "..."}}`; confirmed both list and dict response shapes handled
- `/home/ollie/.openclaw/skills/spawn_specialist/spawn.py` — confirmed `MEMU_API_URL`, `OPENCLAW_PROJECT`, `SKILL_HINT` env vars injected at spawn; confirmed `openclaw-net` network; confirmed `curl` + `jq` in Dockerfile
- `/home/ollie/.openclaw/docker/l3-specialist/Dockerfile` — confirmed `curl` and `jq` installed in base image
- `/home/ollie/.openclaw/docker/l3-specialist/entrypoint.sh` — confirmed SOUL injection pattern and env var availability
- `/home/ollie/.openclaw/agents/l3_specialist/agent/SOUL.md` — read current SOUL content; confirmed section placement strategy (append at end)
- `/home/ollie/.openclaw/tests/test_spawn_memory.py` — existing test patterns (mock httpx.Client, MagicMock setup) that this phase's tests should follow for consistency

### Secondary (MEDIUM confidence)
- Python stdlib `http.server.BaseHTTPRequestHandler` — confirmed available in Python 3.x; commonly used for mock servers in tests

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all tools (curl, jq, MEMU_API_URL, existing /retrieve endpoint) verified directly in codebase
- Architecture: HIGH — SOUL placement, curl pattern, and test design follow established project conventions
- Pitfalls: HIGH — identified from direct inspection of curl behavior, existing code patterns, and test infrastructure

**Research date:** 2026-02-24
**Valid until:** 2026-04-24 (stable — no fast-moving dependencies)
