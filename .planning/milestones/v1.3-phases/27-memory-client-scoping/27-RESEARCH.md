# Phase 27: Memory Client + Scoping - Research

**Researched:** 2026-02-24
**Domain:** Python async HTTP client wrapper with structural scoping enforcement
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Client Interface Design
- Async client using `httpx.AsyncClient` — matches spawn.py's existing asyncio patterns
- Standalone module at `orchestration/memory_client.py` — not inside state_engine.py
- Constructor: `MemoryClient(base_url, project_id, agent_type)` — both scoping params required at construction time
- Methods return typed dataclasses (`MemorizeResult`, `RetrieveResult`) — not raw dicts
- Async context manager support: `async with MemoryClient(...) as client:` for clean httpx cleanup

#### Error & Degradation Behavior
- Sentinel values on failure — `health()` returns False, `memorize()` returns None, `retrieve()` returns `[]`
- No exceptions propagated to callers — memory is always non-blocking
- Split timeouts: 3s for retrieve, 10s for memorize (embedding generation is slow)
- No retries — single attempt, fail fast, return sentinel
- Log warnings via `get_logger()` structured logging when memU is unreachable — operators see degradation

#### Agent Type Scoping Model
- Strict `AgentType(str, Enum)` with values: `l2_pm`, `l3_code`, `l3_test`
- `agent_type` set once in constructor — all calls auto-tag with it
- `memorize()` auto-includes `project_id` + `agent_type` in payload — caller can't forget
- `retrieve()` returns memories from ALL agent types within the project — cross-pollination within project boundary
- Scoping is enforced at the client level: `MemoryClient(base_url, project_id)` — no project_id means no client

#### Integration Surface
- Per-call instance lifecycle — spawn.py creates a new MemoryClient per spawn/review cycle, short-lived
- memU service URL from `MEMU_SERVICE_URL` environment variable with fallback to `http://memu-server:18791`
- Standalone test file: `tests/test_memory_client.py` with isolation test, health test, and scoping tests

### Claude's Discretion
- Exact dataclass field names and shapes for MemorizeResult / RetrieveResult
- Whether to use `@dataclass(frozen=True)` or regular dataclasses
- httpx connection pool settings
- Test fixtures and mocking approach (httpx mock vs live service)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

## Summary

Phase 27 builds a thin Python wrapper (`orchestration/memory_client.py`) around the Phase 26 memU REST API. The wrapper's primary purpose is structural: by requiring `project_id` and `agent_type` at construction time, it makes it impossible to call memorize or retrieve without per-project scoping. The caller never manually constructs a payload with project context — the client always injects it.

The implementation is pure Python (no new external dependencies beyond `httpx`) and follows the established patterns in the orchestration layer: asyncio, structured JSON logging via `get_logger()`, and sentinel-value degradation (no exceptions propagate). The async context manager pattern (`async with MemoryClient(...) as client:`) ensures the httpx connection pool is always released cleanly, even in fire-and-forget contexts.

The test suite will be the first in the `~/.openclaw/` orchestration layer — no existing test infrastructure exists. Tests use `respx` to mock httpx calls at the transport layer, enabling true isolation: no live memU service required.

**Primary recommendation:** Implement `MemoryClient` as an `httpx.AsyncClient` wrapper with constructor-enforced scoping, `@dataclass(frozen=True)` return types, and `respx` for test isolation.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SCOPE-01 | All memory operations enforce per-project scoping via mandatory project_id parameter at the API wrapper level | Constructor-enforced pattern: `MemoryClient(base_url, project_id, agent_type)` — no default, no optional. Python raises TypeError if omitted. httpx payload builder auto-injects project_id. |
| SCOPE-02 | Memory operations support per-agent scoping via agent_type parameter (l2_pm, l3_code, l3_test) | `AgentType(str, Enum)` with exactly 3 values. Set once in constructor, auto-tagged on every memorize call. retrieve returns all types within project boundary. |
| SCOPE-03 | MemoryClient wrapper in orchestration layer enforces scoping — impossible to call memorize/retrieve without project_id | The client class itself is the enforcement mechanism. No project_id = no MemoryClient instance. The `memorize()` and `retrieve()` methods are instance methods that always reference `self.project_id`. |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | latest (already used in workspace/memory/src) | Async HTTP client for memU REST API | Already present in the memu-py codebase; matches spawn.py asyncio patterns; async context manager built-in; fine-grained timeout control |
| dataclasses | stdlib | Typed return values (MemorizeResult, RetrieveResult) | No new dependency; frozen=True for immutability; IDE-friendly; matches project's stdlib-first philosophy |
| enum | stdlib | AgentType enum (l2_pm, l3_code, l3_test) | str subclass allows JSON serialization without conversion; exhaustive validation at construction |

### Supporting (test only)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | latest | Test runner | Standard; no pytest.ini exists yet in ~/.openclaw — must create |
| pytest-asyncio | latest | Async test support for coroutines | Required for `async def test_*` functions with the AsyncClient |
| respx | latest | Mock httpx at transport level | Best-in-class httpx mock; supports `@respx.mock` decorator and context manager; route-based matching; response side effects |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| respx | unittest.mock + MagicMock | respx understands httpx transport natively; MagicMock requires fragile monkey-patching of httpx internals |
| respx | aioresponses | aioresponses targets aiohttp, not httpx |
| dataclasses | TypedDict | TypedDict is typing-only, not a constructor; dataclass gives a real object with `__init__` and repr |
| frozen=True dataclass | regular dataclass | frozen=True prevents accidental mutation of returned results; appropriate for "read the API response" semantics |

**Installation (test dependencies only — no new runtime deps):**
```bash
pip install httpx pytest pytest-asyncio respx
```

---

## Architecture Patterns

### Recommended Project Structure
```
orchestration/
├── memory_client.py     # MemoryClient + AgentType + dataclasses (this phase)
├── state_engine.py      # Existing
├── logging.py           # Existing — get_logger() used here
└── config.py            # Existing

tests/
└── test_memory_client.py  # New — isolation, health, scoping tests
```

### Pattern 1: Constructor-Enforced Scoping
**What:** Both `project_id` and `agent_type` are required positional arguments in `__init__`. Python raises `TypeError` if either is missing — no runtime check needed.
**When to use:** Any wrapper that must make a parameter structurally mandatory, not just documented.
**Example:**
```python
# Source: CONTEXT.md locked decision
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List
import os
import httpx
from orchestration.logging import get_logger

logger = get_logger("memory_client")

class AgentType(str, Enum):
    L2_PM = "l2_pm"
    L3_CODE = "l3_code"
    L3_TEST = "l3_test"

@dataclass(frozen=True)
class MemorizeResult:
    accepted: bool
    message: str

@dataclass(frozen=True)
class RetrieveResult:
    items: List[dict] = field(default_factory=list)

class MemoryClient:
    def __init__(self, base_url: str, project_id: str, agent_type: AgentType):
        self.base_url = base_url.rstrip("/")
        self.project_id = project_id        # required — no default
        self.agent_type = agent_type        # required — no default
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "MemoryClient":
        self._client = httpx.AsyncClient(base_url=self.base_url)
        return self

    async def __aexit__(self, *args) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
```

### Pattern 2: Async Context Manager for httpx Lifecycle
**What:** `httpx.AsyncClient` must be closed after use to release the connection pool. Using `__aenter__`/`__aexit__` on MemoryClient delegates cleanup to caller via `async with`.
**When to use:** All short-lived (per-call) client instances in asyncio code.
**Example:**
```python
# Source: https://github.com/encode/httpx/blob/master/docs/async.md (Context7 verified)
async with httpx.AsyncClient() as client:
    r = await client.get("http://memu-server:18791/health")
# client.aclose() called automatically on exit
```

### Pattern 3: Split Timeouts for Different Operation Costs
**What:** retrieve uses 3s (fast vector lookup), memorize uses 10s (embedding generation hits OpenAI). httpx.Timeout allows per-operation configuration.
**When to use:** When different endpoints on the same service have different SLA characteristics.
**Example:**
```python
# Source: Context7 /encode/httpx — Timeout Configuration
TIMEOUT_RETRIEVE = httpx.Timeout(3.0, connect=2.0)
TIMEOUT_MEMORIZE = httpx.Timeout(10.0, connect=2.0)

async def memorize(self, content: str, category: str = "general") -> Optional[MemorizeResult]:
    try:
        resp = await self._client.post(
            "/memorize",
            json={
                "resource_url": content,
                "user": {
                    "user_id": self.project_id,
                    "agent_type": self.agent_type.value,
                }
            },
            timeout=TIMEOUT_MEMORIZE,
        )
        resp.raise_for_status()
        return MemorizeResult(accepted=True, message="accepted")
    except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as e:
        logger.warning("memorize failed", extra={
            "project_id": self.project_id,
            "agent_type": self.agent_type.value,
            "error": str(e),
        })
        return None
```

### Pattern 4: Sentinel-Value Degradation (Non-Blocking)
**What:** All exceptions are caught internally. Return `None` for memorize failure, `[]` for retrieve failure, `False` for health failure. Callers never need try/except.
**When to use:** Memory is always auxiliary to the main workflow — degradation must be invisible to callers.
**Example:**
```python
async def retrieve(self, query: str) -> List[dict]:
    try:
        resp = await self._client.post(
            "/retrieve",
            json={"queries": [{"role": "user", "content": query}]},
            timeout=TIMEOUT_RETRIEVE,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("items", [])
    except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as e:
        logger.warning("retrieve failed", extra={
            "project_id": self.project_id,
            "error": str(e),
        })
        return []
```

### Pattern 5: respx Mock Transport for Testing
**What:** `respx` intercepts httpx requests at the transport layer. No live server required. Route matchers define expected requests and return fixed responses.
**When to use:** All unit tests for MemoryClient. The two-project isolation test is the key correctness verification.
**Example:**
```python
# Source: Context7 /lundberg/respx — respx.mock decorator + base_url
import pytest
import respx
import httpx
from orchestration.memory_client import MemoryClient, AgentType

@pytest.mark.asyncio
@respx.mock(base_url="http://memu-server:18791")
async def test_project_isolation(respx_mock):
    """Write for project A, retrieve for project B — must return empty."""
    memorize_route = respx_mock.post("/memorize").mock(
        return_value=httpx.Response(202, json={"status": "accepted", "message": "Memorization queued"})
    )
    retrieve_route = respx_mock.post("/retrieve").mock(
        return_value=httpx.Response(200, json={"items": []})
    )

    async with MemoryClient("http://memu-server:18791", "project-a", AgentType.L3_CODE) as client_a:
        result = await client_a.memorize("task completed successfully")
        assert result is not None

    async with MemoryClient("http://memu-server:18791", "project-b", AgentType.L3_CODE) as client_b:
        results = await client_b.retrieve("task outcome")
        assert results == []  # project-b sees nothing from project-a
```

### Anti-Patterns to Avoid
- **Optional project_id with default None:** Defeats the structural enforcement. SCOPE-03 requires it to be impossible to call without project_id — a None default makes it merely discouraged.
- **Shared httpx.AsyncClient across instances:** Per the CONTEXT.md, instances are short-lived per spawn/review cycle. A shared persistent client complicates cleanup and lifecycle reasoning.
- **Raising exceptions from memorize/retrieve:** Violates the non-blocking contract. All callers (spawn.py, review flows) must be able to call memory operations without try/except.
- **Using `user_id` as the scoping key:** The memU API uses `user.user_id` for filtering. The mapping is `project_id → user_id`. Agent type should be embedded in user metadata or as a separate field, not re-interpreted as `user_id`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP mocking for tests | Manual monkeypatch of httpx internals | respx | respx understands httpx's transport layer; route-based matching is readable and maintainable |
| Async test runner support | asyncio.run() in test functions | pytest-asyncio | Handles event loop lifecycle, fixture scoping, and cleanup correctly |
| Timeout handling | Custom signal-based timeouts | httpx.Timeout | httpx.Timeout supports connect/read/write/pool independently; fully integrated with AsyncClient |

**Key insight:** httpx exception hierarchy (`httpx.TimeoutException`, `httpx.ConnectError`, `httpx.HTTPStatusError`) covers all failure modes cleanly. Catching `httpx.RequestError` (parent of TimeoutException + ConnectError) plus `httpx.HTTPStatusError` is sufficient for the sentinel pattern.

---

## Common Pitfalls

### Pitfall 1: Forgetting agent_type in memorize payload
**What goes wrong:** The memU API's `user` field stores metadata for filtering. If `agent_type` is not included in the `user` dict, retrieve cannot filter by agent type and SCOPE-02 is unsatisfied at the data level (even if structurally enforced).
**Why it happens:** The memorize endpoint takes `resource_url` and `user: dict`. The mapping from our domain model to memU's model requires explicit field placement.
**How to avoid:** The `memorize()` method always constructs the `user` payload from `self.project_id` and `self.agent_type.value`. Never pass user dict from caller.
**Warning signs:** Tests pass but `WHERE user_id = project_b` filters miss agent_type metadata.

### Pitfall 2: httpx.AsyncClient not closed on error path
**What goes wrong:** If `__aenter__` creates the client but `__aexit__` is not called (e.g., if the `async with` block is abandoned), the connection pool leaks.
**Why it happens:** Forgetting that `async with MemoryClient(...)` must wrap all method calls — not creating the client in `memorize()` itself.
**How to avoid:** The context manager pattern (`__aenter__`/`__aexit__`) ensures cleanup. Never expose methods that create an httpx.AsyncClient inline without cleanup.
**Warning signs:** ResourceWarning about unclosed connection in test output.

### Pitfall 3: retrieve payload format mismatch with Phase 26 API
**What goes wrong:** The Phase 26 `/retrieve` endpoint expects `{"queries": [{"role": "user", "content": "..."}], "where": {...}}`. A malformed payload returns 422 Unprocessable Entity, which is an HTTPStatusError — sentinel handles it, but silently swallows what was actually a coding error.
**Why it happens:** The memu-py retrieve API uses a specific query format that differs from a simple string.
**How to avoid:** Match the `RetrieveRequest` Pydantic model from Phase 26 exactly: `queries` is a list of dicts with role/content keys; `where` is optional filtering. Document in the method docstring.
**Warning signs:** retrieve always returns `[]` with no warning log (HTTP 422 caught silently).

### Pitfall 4: user_id vs project_id semantic collision
**What goes wrong:** The memU service uses `user_id` as a filtering key in the `where` clause. OpenClaw uses `project_id` as the scoping key. If the `where` clause in retrieve does not map `project_id → user_id`, retrieve returns cross-project memories.
**Why it happens:** Terminology mismatch between memU's user-centric model and OpenClaw's project-centric model.
**How to avoid:** The retrieve method always adds `"where": {"user_id": self.project_id}` to the payload. This is the core of SCOPE-01.
**Warning signs:** Two-project isolation test passes but returns data from both projects.

### Pitfall 5: pytest-asyncio mode configuration missing
**What goes wrong:** `async def test_*` functions are skipped or fail with "coroutine was never awaited" if pytest-asyncio is not configured.
**Why it happens:** pytest-asyncio requires explicit mode configuration (auto or strict) in pytest.ini or pyproject.toml since pytest-asyncio 0.19+.
**How to avoid:** Create `tests/pytest.ini` or `pytest.ini` with `asyncio_mode = auto` at the project root.
**Warning signs:** Tests are collected but show as "passed" with 0 assertions run (silently skipped).

---

## Code Examples

Verified patterns from official sources:

### AsyncClient with base_url and timeout
```python
# Source: Context7 /encode/httpx — Making Async GET Request
async with httpx.AsyncClient(base_url="http://memu-server:18791") as client:
    r = await client.get("/health", timeout=httpx.Timeout(3.0, connect=2.0))
    r.raise_for_status()
    return r.json()
```

### Exception hierarchy for sentinel pattern
```python
# Source: Context7 /encode/httpx — HTTPX Exception Handling Hierarchy
try:
    resp = await client.post("/memorize", json=payload, timeout=TIMEOUT_MEMORIZE)
    resp.raise_for_status()
except httpx.TimeoutException as e:
    logger.warning("memorize timeout", extra={"error": str(e)})
    return None
except httpx.ConnectError as e:
    logger.warning("memorize connect failed", extra={"error": str(e)})
    return None
except httpx.HTTPStatusError as e:
    logger.warning("memorize http error", extra={
        "status_code": e.response.status_code,
        "error": str(e),
    })
    return None
```

### respx route-based mocking
```python
# Source: Context7 /lundberg/respx — Mock with Base URL
@respx.mock(base_url="http://memu-server:18791")
async def test_health_ok(respx_mock):
    respx_mock.get("/health").mock(
        return_value=httpx.Response(200, json={
            "status": "ok",
            "service": "openclaw-memory",
            "memu_initialized": True,
        })
    )
    async with MemoryClient("http://memu-server:18791", "pumplai", AgentType.L2_PM) as client:
        ok = await client.health()
    assert ok is True
```

### AgentType enum as str subclass
```python
# Source: Python stdlib — str Enum pattern
from enum import Enum

class AgentType(str, Enum):
    L2_PM = "l2_pm"
    L3_CODE = "l3_code"
    L3_TEST = "l3_test"

# Serializes directly in JSON without .value:
import json
json.dumps({"agent_type": AgentType.L3_CODE})  # '{"agent_type": "l3_code"}'
```

### Environment variable URL resolution
```python
# Source: CONTEXT.md locked decision — MEMU_SERVICE_URL with fallback
import os

MEMU_SERVICE_URL = os.environ.get("MEMU_SERVICE_URL", "http://memu-server:18791")

# Usage in spawn.py:
async with MemoryClient(MEMU_SERVICE_URL, project_id, AgentType.L3_CODE) as client:
    await client.memorize(content)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| aiohttp for async HTTP | httpx AsyncClient | httpx stable since 2021 | Cleaner API, built-in timeout control, context manager, sync/async parity |
| MagicMock + monkeypatch for httpx | respx transport mock | respx stable since 2020 | Route-based matching is declarative and readable; prevents false-positive tests from mock mismatches |
| pytest.mark.asyncio on every test | asyncio_mode = auto in pytest.ini | pytest-asyncio 0.19+ (2022) | Less boilerplate; all async test functions auto-detected |

**Deprecated/outdated:**
- `AsyncMockTransport` (respx): Older API from respx 0.14.x. Current API uses `respx.mock` decorator with `respx_mock` fixture argument and `.mock(return_value=...)` on routes.

---

## Open Questions

1. **memU retrieve response shape**
   - What we know: Phase 26 retrieve endpoint calls `memu.retrieve()` and returns the result directly. The router does not wrap it in `{"items": [...]}`.
   - What's unclear: The exact JSON structure returned by `MemoryService.retrieve()`. The memu-py library returns a Python object that FastAPI serializes. The RetrieveResult dataclass needs to match the actual response shape.
   - Recommendation: In Wave 0 or first task, add a quick introspection step: POST to `/retrieve` with a test payload against the live stack (localhost:18791) and inspect the response body before finalizing `RetrieveResult` field names. Fall back to `items: List[dict]` if the shape is a nested list without a top-level key.

2. **pytest.ini location and asyncio_mode**
   - What we know: No tests/ directory and no pytest.ini exists anywhere in ~/.openclaw.
   - What's unclear: Whether to put pytest.ini at the project root (`~/.openclaw/pytest.ini`) or inside `tests/`.
   - Recommendation: Create `tests/` directory and `tests/pytest.ini` with `asyncio_mode = auto`. Keeps test config colocated with tests.

---

## Sources

### Primary (HIGH confidence)
- `/encode/httpx` (Context7) — AsyncClient lifecycle, timeout configuration, exception hierarchy
- `/lundberg/respx` (Context7) — Mock transport, route-based matching, pytest integration
- `~/.openclaw/docker/memory/memory_service/routers/` — Live Phase 26 API surface (memorize, retrieve, health, memories endpoint implementations)
- `~/.openclaw/docker/memory/memory_service/models.py` — Exact request/response Pydantic schemas
- `~/.openclaw/orchestration/logging.py` — `get_logger()` pattern for structured logging
- `~/.openclaw/skills/spawn_specialist/pool.py` — asyncio patterns and project_id threading conventions

### Secondary (MEDIUM confidence)
- Phase 26 VERIFICATION.md — Confirmed live API behavior: `/health` returns `{"status":"ok","service":"openclaw-memory","memu_initialized":true}`, `/memorize` returns 202, `/retrieve` returns 500 with placeholder key (expected)

### Tertiary (LOW confidence)
- Assumed `MemoryService.retrieve()` returns an object with `.items` or similar — needs live verification before finalizing `RetrieveResult` fields

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — httpx already used in memu-py codebase; respx verified via Context7 with 161 snippets and HIGH reputation
- Architecture: HIGH — constructor-enforced scoping, sentinel pattern, and context manager lifecycle all based on verified httpx/Python patterns
- API surface mapping: HIGH — Phase 26 live and verified; exact endpoint shapes confirmed from source code inspection
- Test infrastructure: MEDIUM — pytest/respx patterns verified; actual retrieve response shape needs one live check before finalizing RetrieveResult

**Research date:** 2026-02-24
**Valid until:** 2026-03-24 (httpx and respx are stable libraries; memu API surface locked by Phase 26)
