# OpenClaw Advanced Integration Plan

> Deep integration of the `openclaw/` agent runtime with `packages/orchestration/` and the `agents/` hierarchy — moving from CLI-level coupling to programmatic API-level integration.

**Date**: 2026-03-03
**Status**: Draft
**Builds on**: OPENCLAW_PLAN.md (Phases 1–5)
**Scope**: 6 advanced phases (A1–A6) across the orchestration engine, agent hierarchy, and runtime

---

## Context: Where OPENCLAW_PLAN.md Leaves Off

The base plan formalizes the existing coupling: submodule wiring, skill loading via `extraDirs`, memory hardening, dashboard cross-links, and Docker base image sharing. Those are **infrastructure-level** improvements.

This advanced plan goes deeper — into the **programmatic integration** between the Python orchestration engine (`packages/orchestration/`) and the TypeScript openclaw runtime (`openclaw/`). The goal: replace brittle CLI dispatch and manual config duplication with shared protocols, typed contracts, and event-driven coordination.

### Current Integration Surface

| Integration Point | Current Mechanism | Limitation |
|---|---|---|
| L1→L2 dispatch | `execFileSync('openclaw', [...])` in `router/index.js` | Synchronous, 5-min timeout, no streaming, no structured errors |
| L2→L3 spawn | `docker.containers.run()` in `spawn.py` | Separate from openclaw's own sandbox system |
| State sync | `fcntl.flock()` on `workspace-state.json` | File-level locking, no event notification |
| Memory injection | HTTP to memU REST API, format in Python, mount as file | Two-step indirection, no real-time memory updates during task |
| Agent config | Duplicated between `agents/*/config.json` and `openclaw.json agents.list` | Config drift, manual sync required |
| Autonomy | Python `autonomy/` framework, L3 HTTP self-reporting | Not connected to openclaw's Pi agent loop |
| Review | Stub in `review.py`, real review is manual | No integration with openclaw's tool execution layer |

---

## Phase A1: Programmatic Agent Dispatch — Replace CLI with Gateway API

**Priority**: P0 (do first)
**Effort**: ~4 hours
**Risk**: Medium
**Depends on**: Base Phase 1 (submodule wired)

### Rationale

The current L1→L2 dispatch in `skills/router/index.js` uses `execFileSync('openclaw', ...)` — a synchronous subprocess call with a 5-minute timeout. This blocks the Node.js event loop, provides no streaming feedback, and makes error handling opaque (exit codes only).

The openclaw runtime already exposes an Express 5 gateway on port 18789. We should dispatch via HTTP instead of CLI, gaining:
- Non-blocking async dispatch with streaming responses
- Structured JSON error responses
- Request correlation via `runId`
- Timeout control at the HTTP level (not process-level)

### Steps

#### A1.1 — Create Gateway Client in Orchestration Package

Add `packages/orchestration/src/openclaw/gateway_client.py`:

```python
"""HTTP client for the openclaw gateway (port 18789)."""

import httpx
from dataclasses import dataclass
from typing import AsyncIterator, Optional
from openclaw.config import get_gateway_config
from openclaw.logging import get_logger

logger = get_logger("gateway_client")

@dataclass
class DispatchResult:
    run_id: str
    status: str  # "ok" | "error"
    output: Optional[str] = None
    error: Optional[str] = None

@dataclass
class GatewayClient:
    base_url: str
    auth_token: str
    timeout: float = 300.0  # 5 minutes default

    @classmethod
    def from_config(cls) -> "GatewayClient":
        config = get_gateway_config()
        return cls(
            base_url=f"http://localhost:{config['port']}",
            auth_token=config.get("token", ""),
        )

    async def dispatch(
        self, agent_id: str, message: str, timeout: Optional[float] = None
    ) -> DispatchResult:
        """Dispatch a directive to an agent via the gateway API."""
        async with httpx.AsyncClient(timeout=timeout or self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/agent/{agent_id}/message",
                json={"message": message},
                headers={"Authorization": f"Bearer {self.auth_token}"},
            )
            data = response.json()
            return DispatchResult(
                run_id=data.get("runId", ""),
                status="ok" if response.is_success else "error",
                output=data.get("output"),
                error=data.get("error"),
            )

    async def dispatch_stream(
        self, agent_id: str, message: str
    ) -> AsyncIterator[dict]:
        """Stream dispatch — yields incremental updates as the agent works."""
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/agent/{agent_id}/message",
                json={"message": message, "stream": True},
                headers={"Authorization": f"Bearer {self.auth_token}"},
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        yield json.loads(line[6:])
```

#### A1.2 — Update Router Skill to Use Gateway Client

Refactor `skills/router/index.js` to use HTTP dispatch instead of `execFileSync`:

```javascript
// Replace execFileSync with fetch-based dispatch
async function dispatchDirective(targetId, directive) {
  const gatewayUrl = config.gateway?.endpoint || 'http://localhost:18789';
  const token = process.env.OPENCLAW_GATEWAY_TOKEN || config.gateway?.token;

  const response = await fetch(`${gatewayUrl}/api/agent/${targetId}/message`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ message: directive }),
    signal: AbortSignal.timeout(300_000), // 5 min
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new DispatchError(targetId, error.message || response.statusText);
  }

  return response.json(); // { runId, status, output }
}
```

Keep the `execFileSync` path as a fallback when the gateway is unreachable.

#### A1.3 — Add Gateway Health Probe to Orchestration

Add `get_gateway_config()` to `config.py` and a health check:

```python
def get_gateway_config() -> dict:
    """Extract gateway config from openclaw.json."""
    config = load_and_validate_openclaw_config()
    return config.get("gateway", {"port": 18789})

async def gateway_healthy(base_url: str = "http://localhost:18789") -> bool:
    """Check if the openclaw gateway is responding."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{base_url}/health")
            return r.status_code == 200
    except httpx.HTTPError:
        return False
```

#### A1.4 — Add Meta-PM Python Router

Create `agents/main/skills/route_directive/router.py` — a Python implementation of the routing logic that uses `GatewayClient` instead of CLI:

```python
"""Route directives from L1 to the appropriate L2 PM via gateway API."""

from openclaw.gateway_client import GatewayClient
from openclaw.project_config import load_and_validate_openclaw_config

class DirectiveRouter:
    def __init__(self):
        self.client = GatewayClient.from_config()
        self.config = load_and_validate_openclaw_config()

    async def route(self, directive: str, context: dict = None) -> dict:
        """Analyze directive and route to the best PM agent."""
        target = self._resolve_target(directive, context)
        result = await self.client.dispatch(target, directive)
        return {"target": target, "run_id": result.run_id, "status": result.status}

    def _resolve_target(self, directive: str, context: dict) -> str:
        """Resolve target agent using project registry and keyword matching."""
        # Uses agents/main/agent/config.json project_registry
        # Priority: explicit mention → stack detection → generic → escalate
        ...
```

### Validation

| Check | Command | Expected |
|---|---|---|
| Gateway client works | `python -c "from openclaw.gateway_client import GatewayClient"` | No import errors |
| HTTP dispatch succeeds | Start gateway + `await client.dispatch("main", "echo test")` | Returns `DispatchResult(status="ok")` |
| Fallback works | Stop gateway → router falls back to `execFileSync` | CLI dispatch succeeds |
| Streaming works | `async for chunk in client.dispatch_stream(...)` | Yields incremental updates |

### Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Gateway not running | Dispatch fails | Keep execFileSync fallback; add health check before dispatch |
| Auth token mismatch | 401 errors | Read token from same `openclaw.json` config both sides use |
| Streaming format changes | Client breaks | Pin to gateway API version; add integration test |

---

## Phase A2: Unified Agent Registry — Single Source of Truth

**Priority**: P0 (do first, parallel with A1)
**Effort**: ~3 hours
**Risk**: Medium
**Depends on**: Base Phase 1

### Rationale

Agent configuration is currently duplicated:
1. `openclaw.json` → `agents.list[]` — defines agents for the openclaw runtime (id, name, model, provider)
2. `agents/*/config.json` — defines agents for the orchestration layer (level, reports_to, skills, container config)
3. `agents/*/agent/IDENTITY.md` — agent identity/role description
4. `agents/*/agent/SOUL.md` — behavioral constraints

This duplication causes drift. When a new agent is added, it must be configured in multiple places. The advanced plan unifies this into a single registry that both systems read.

### Steps

#### A2.1 — Define Unified Agent Schema

Create `packages/orchestration/src/openclaw/agent_registry.py`:

```python
"""Unified agent registry that merges openclaw.json agents with agents/ directory."""

from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Optional, List, Dict
import json

class AgentLevel(IntEnum):
    L1 = 1  # Strategic orchestrator
    L2 = 2  # Tactical project manager
    L3 = 3  # Ephemeral specialist

@dataclass
class AgentSpec:
    id: str
    name: str
    level: AgentLevel
    reports_to: Optional[str] = None
    subordinates: List[str] = field(default_factory=list)

    # From openclaw.json
    model: Optional[str] = None
    provider: Optional[str] = None

    # From agents/*/config.json
    role: Optional[str] = None  # "coordinator", "domain", "executor"
    projects: List[str] = field(default_factory=list)
    max_concurrent: int = 3
    skill_registry: Dict[str, dict] = field(default_factory=dict)

    # From agents/*/agent/
    identity_path: Optional[Path] = None
    soul_path: Optional[Path] = None

    # L3-specific
    container: Optional[dict] = None
    runtime: Optional[dict] = None

    @property
    def is_orchestrator(self) -> bool:
        return self.level <= AgentLevel.L2

    @property
    def is_ephemeral(self) -> bool:
        return self.level == AgentLevel.L3

class AgentRegistry:
    """Merges openclaw.json agent list with agents/ directory configs."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self._agents: Dict[str, AgentSpec] = {}
        self._load()

    def _load(self):
        """Load from both sources, agents/ dir takes precedence for orchestration fields."""
        self._load_openclaw_json()
        self._load_agents_directory()
        self._validate_hierarchy()

    def get(self, agent_id: str) -> Optional[AgentSpec]:
        return self._agents.get(agent_id)

    def list_by_level(self, level: AgentLevel) -> List[AgentSpec]:
        return [a for a in self._agents.values() if a.level == level]

    def get_hierarchy(self, agent_id: str) -> List[AgentSpec]:
        """Walk up the reports_to chain."""
        chain = []
        current = self.get(agent_id)
        while current:
            chain.append(current)
            current = self.get(current.reports_to) if current.reports_to else None
        return chain

    def get_subordinates(self, agent_id: str, recursive: bool = False) -> List[AgentSpec]:
        """Get direct (or all recursive) subordinates."""
        direct = [a for a in self._agents.values() if a.reports_to == agent_id]
        if not recursive:
            return direct
        result = []
        for sub in direct:
            result.append(sub)
            result.extend(self.get_subordinates(sub.id, recursive=True))
        return result
```

#### A2.2 — Add Agent Registration to openclaw.json

Extend the `agents.list` entries in `openclaw.json` with orchestration fields:

```json
{
  "agents": {
    "list": [
      {
        "id": "clawdia_prime",
        "name": "ClawdiaPrime - Head of Development",
        "level": 1,
        "reports_to": null,
        "subordinates": ["pumplai_pm"],
        "model": "google-gemini-cli/gemini-2.5-flash",
        "orchestration": {
          "role": "strategic",
          "max_concurrent": 4,
          "skill_registry": ["router", "swarm_query"],
          "identity_ref": "agents/clawdia_prime/agent/IDENTITY.md",
          "soul_ref": "agents/clawdia_prime/agent/SOUL.md"
        }
      }
    ]
  }
}
```

This embeds the orchestration metadata directly in `openclaw.json`, making `agents/*/config.json` derivable rather than authoritative.

#### A2.3 — Generate agents/*/config.json from Registry

Add a CLI command to generate agent configs from the unified registry:

```python
# openclaw-config sync-agents
# Reads openclaw.json agents.list → writes agents/*/config.json
```

This keeps the directory structure for backward compatibility while the registry becomes the source of truth.

#### A2.4 — Validate Hierarchy at Startup

Extend `config_validator.py` to validate the full agent hierarchy:

```python
def validate_agent_hierarchy_advanced(registry: AgentRegistry) -> List[str]:
    """Validate the complete agent hierarchy."""
    errors = []

    # Every agent (except L1) must have a valid reports_to
    for agent in registry._agents.values():
        if agent.level > AgentLevel.L1 and not agent.reports_to:
            errors.append(f"{agent.id}: L{agent.level} agent must have reports_to")
        if agent.reports_to and not registry.get(agent.reports_to):
            errors.append(f"{agent.id}: reports_to '{agent.reports_to}' not found")

    # L3 agents must have container config
    for agent in registry.list_by_level(AgentLevel.L3):
        if not agent.container:
            errors.append(f"{agent.id}: L3 agent missing container config")

    # No circular reports_to chains
    for agent in registry._agents.values():
        chain = registry.get_hierarchy(agent.id)
        ids = [a.id for a in chain]
        if len(ids) != len(set(ids)):
            errors.append(f"{agent.id}: circular hierarchy detected")

    return errors
```

### Validation

| Check | Command | Expected |
|---|---|---|
| Registry loads | `python -c "from openclaw.agent_registry import AgentRegistry; r = AgentRegistry(Path('.'))"` | No errors |
| Hierarchy valid | `openclaw-config validate` | No hierarchy errors |
| Both systems see same agents | Compare `openclaw skills list` agent count with `AgentRegistry.list_by_level()` | Match |
| Sync generates configs | `openclaw-config sync-agents` | `agents/*/config.json` files updated |

---

## Phase A3: Event-Driven State Bridge — Replace Polling with Events

**Priority**: P1 (high)
**Effort**: ~5 hours
**Risk**: Medium-High
**Depends on**: A1 (gateway client)

### Rationale

The Jarvis Protocol state engine uses file-based locking with polling (`POLL_INTERVAL_ACTIVE = 2s`). This works but introduces latency and unnecessary I/O. The openclaw runtime has its own event system (Pi agent loop events).

An event bridge would allow:
- Real-time state change notification (task created → L2 notified immediately)
- Reduced polling overhead (event-driven instead of 2s intervals)
- Bidirectional: orchestration events → openclaw runtime, and vice versa

### Architecture

```
                   Event Bridge
                   ┌─────────────────────┐
Orchestration      │  Redis Pub/Sub      │      openclaw Runtime
(Python)           │  or Unix Socket     │      (TypeScript)
┌──────────┐       │                     │       ┌──────────────┐
│ JarvisState ─────┤► openclaw.task.*    ├──────►│ Pi Agent Loop │
│ event_bus  ◄─────┤◄ openclaw.agent.*   │◄──────┤ Event System  │
│ autonomy   ─────►│► openclaw.autonomy.*│       │               │
└──────────┘       └─────────────────────┘       └──────────────┘
```

### Steps

#### A3.1 — Define Event Protocol

Create `packages/orchestration/src/openclaw/events/protocol.py`:

```python
"""Cross-runtime event protocol — shared between Python and TypeScript."""

from enum import Enum
from dataclasses import dataclass, asdict
from typing import Optional
import json
import time

class EventDomain(str, Enum):
    TASK = "openclaw.task"
    AGENT = "openclaw.agent"
    AUTONOMY = "openclaw.autonomy"
    MEMORY = "openclaw.memory"
    POOL = "openclaw.pool"

class EventType(str, Enum):
    # Task lifecycle
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_ESCALATED = "task.escalated"

    # Agent lifecycle
    AGENT_DISPATCHED = "agent.dispatched"
    AGENT_RESPONSE = "agent.response"
    AGENT_ERROR = "agent.error"

    # Autonomy
    AUTONOMY_STATE_CHANGED = "autonomy.state_changed"
    AUTONOMY_CONFIDENCE_UPDATED = "autonomy.confidence_updated"
    AUTONOMY_ESCALATION = "autonomy.escalation"

    # Memory
    MEMORY_STORED = "memory.stored"
    MEMORY_RECALLED = "memory.recalled"

    # Pool
    POOL_SLOT_ACQUIRED = "pool.slot_acquired"
    POOL_SLOT_RELEASED = "pool.slot_released"
    POOL_OVERFLOW = "pool.overflow"

@dataclass
class OrchestratorEvent:
    type: EventType
    domain: EventDomain
    project_id: str
    agent_id: Optional[str] = None
    task_id: Optional[str] = None
    payload: Optional[dict] = None
    timestamp: float = None
    correlation_id: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, data: str) -> "OrchestratorEvent":
        d = json.loads(data)
        d["type"] = EventType(d["type"])
        d["domain"] = EventDomain(d["domain"])
        return cls(**d)
```

#### A3.2 — Implement Event Transport (Unix Socket)

For single-machine deployment, use a Unix domain socket for low-latency IPC:

```python
# packages/orchestration/src/openclaw/events/transport.py

class UnixSocketTransport:
    """Bidirectional event transport over Unix domain socket."""

    SOCKET_PATH = "/tmp/openclaw-events.sock"

    async def publish(self, event: OrchestratorEvent):
        """Publish event to all connected subscribers."""
        ...

    async def subscribe(self, pattern: str, handler: Callable):
        """Subscribe to events matching pattern (e.g., 'openclaw.task.*')."""
        ...
```

#### A3.3 — Wire JarvisState to Event Bus

Extend `state_engine.py` to emit events on state changes:

```python
# In JarvisState.create_task():
self._event_bus.emit(OrchestratorEvent(
    type=EventType.TASK_CREATED,
    domain=EventDomain.TASK,
    project_id=self.project_id,
    task_id=task_id,
    payload={"skill_hint": skill_hint, "metadata": metadata}
))
```

#### A3.4 — Wire Autonomy Framework to Events

Replace the current `AutonomyEventBus` (internal pub/sub) with the cross-runtime event bridge:

```python
# In autonomy/hooks.py on_task_spawn():
event_bridge.publish(OrchestratorEvent(
    type=EventType.AUTONOMY_STATE_CHANGED,
    domain=EventDomain.AUTONOMY,
    project_id=project_id,
    task_id=task_id,
    payload={"state": "PLANNING", "confidence": 1.0}
))
```

#### A3.5 — TypeScript Event Listener (openclaw side)

Create an openclaw extension or gateway middleware that connects to the event socket:

```typescript
// openclaw/extensions/orchestration-bridge/index.ts
import { connect } from 'node:net';

const socket = connect('/tmp/openclaw-events.sock');
socket.on('data', (data) => {
  const event = JSON.parse(data.toString());
  // Route to Pi agent loop, update gateway state, etc.
});
```

### Validation

| Check | Command | Expected |
|---|---|---|
| Event protocol parses | `OrchestratorEvent.from_json(event.to_json()) == event` | Round-trips correctly |
| Socket transport works | Start publisher + subscriber, publish event | Subscriber receives event |
| JarvisState emits events | Create task → check subscriber | `TASK_CREATED` event received |
| Cross-runtime works | Python publish → TypeScript receives | Event arrives in <50ms |

---

## Phase A4: L3 Sandbox Unification — Orchestration Inside openclaw Sandbox

**Priority**: P1 (high)
**Effort**: ~6 hours
**Risk**: High
**Depends on**: A1, A2

### Rationale

Currently, L3 containers are managed entirely by `spawn.py` via the Docker SDK. The openclaw runtime has its own sandbox system (`src/agents/sandbox/`) that provides:
- Container lifecycle management
- Tool execution inside containers
- File system isolation
- Network policies

By routing L3 spawning through openclaw's sandbox API instead of raw Docker, we gain:
- Unified container management (one system to monitor)
- Access to openclaw's tool execution layer inside L3
- Consistent security policies
- The ability to use openclaw's sandbox health checks and recovery

### Steps

#### A4.1 — Create Sandbox Adapter in Orchestration Package

```python
# packages/orchestration/src/openclaw/sandbox_adapter.py

"""Adapter to spawn L3 containers through openclaw's sandbox API."""

from openclaw.gateway_client import GatewayClient
from openclaw.agent_registry import AgentRegistry, AgentLevel

class SandboxAdapter:
    """Routes L3 spawning through the openclaw sandbox instead of raw Docker."""

    def __init__(self, gateway: GatewayClient, registry: AgentRegistry):
        self.gateway = gateway
        self.registry = registry

    async def spawn_l3(
        self,
        task_id: str,
        skill_hint: str,
        project_id: str,
        directive: str,
        memory_context: str = "",
    ) -> dict:
        """Spawn an L3 task via the openclaw sandbox API."""
        agent_spec = self.registry.get("l3_specialist")

        result = await self.gateway.dispatch(
            agent_id="l3_specialist",
            message=self._build_l3_directive(
                task_id=task_id,
                skill_hint=skill_hint,
                directive=directive,
                memory_context=memory_context,
            ),
        )
        return {
            "task_id": task_id,
            "run_id": result.run_id,
            "status": result.status,
        }

    def _build_l3_directive(self, **kwargs) -> str:
        """Build the structured directive string for L3 execution."""
        return json.dumps({
            "type": "l3_task",
            "task_id": kwargs["task_id"],
            "skill_hint": kwargs["skill_hint"],
            "directive": kwargs["directive"],
            "memory_context": kwargs["memory_context"],
            "staging_branch": f"l3/task-{kwargs['task_id']}",
        })
```

#### A4.2 — Update spawn.py to Use Adapter (Optional Path)

Add a feature flag to `spawn.py` that routes through the sandbox adapter when the gateway is available:

```python
async def spawn_l3_specialist(task_id, skill_hint, directive, ...):
    if await gateway_healthy() and config.get("use_sandbox_adapter", False):
        adapter = SandboxAdapter(GatewayClient.from_config(), registry)
        return await adapter.spawn_l3(task_id, skill_hint, project_id, directive)
    else:
        # Existing Docker SDK path (preserved as fallback)
        return await _spawn_via_docker(task_id, skill_hint, directive, ...)
```

#### A4.3 — Preserve Volume Mounts and Environment

Ensure the sandbox adapter passes the same volume mounts and env vars that `spawn.py` currently configures:

| Mount | Container Path | Mode | Purpose |
|---|---|---|---|
| `{workspace}` | `/workspace` | rw | Working directory |
| `packages/orchestration/src` | `/openclaw_src` | ro | Orchestration library |
| `workspace/.openclaw` | `/workspace/.openclaw` | rw | Shared state |
| `soul-{task_id}.md` | `/run/openclaw/soul.md` | ro | Augmented SOUL with memory |

#### A4.4 — Pool Integration

Update `pool.py` to track tasks spawned via either path:

```python
class PoolRegistry:
    def acquire_slot(self, task_id: str, spawn_method: str = "docker"):
        """Track spawn method for recovery scanning."""
        ...
```

### Validation

| Check | Command | Expected |
|---|---|---|
| Sandbox adapter spawns | `await adapter.spawn_l3("test-001", "code", "pumplai", "write hello.py")` | Task runs in sandbox |
| Volume mounts match | Compare `docker inspect` of both paths | Same mounts present |
| Env vars match | Compare container env of both paths | Same vars set |
| Pool tracks both | `pool.active_tasks()` | Shows tasks from both spawn methods |
| Fallback works | Stop gateway → spawn falls back to Docker SDK | Task still runs |

---

## Phase A5: Orchestration-Aware SOUL Rendering — Dynamic Agent Context

**Priority**: P2 (medium)
**Effort**: ~3 hours
**Risk**: Low
**Depends on**: A2 (agent registry), A3 (events)

### Rationale

The current `soul_renderer.py` uses `string.Template.safe_substitute()` with static variables from project config. The advanced version should inject:

1. **Live hierarchy context** — who is the agent's superior, what are its peers' current states
2. **Active task context** — what tasks are in-flight across the project
3. **Memory context** — pre-fetched memories (already done for L3, extend to L2)
4. **Autonomy state** — current confidence levels, escalation history

### Steps

#### A5.1 — Extend SOUL Template Variables

Add new template sections to `agents/_templates/soul-default.md`:

```markdown
# Hierarchy Context
**Superior**: $superior_name ($superior_id)
**Peers**: $peer_agents
**Subordinates**: $subordinate_agents

# Active Project Context
**Project**: $project_name ($project_id)
**Active Tasks**: $active_task_count
**Pool Utilization**: $pool_utilization

# Memory Context
$memory_section

# Autonomy State
**Confidence**: $autonomy_confidence
**State**: $autonomy_state
```

#### A5.2 — Build Dynamic Variables in soul_renderer.py

```python
def build_dynamic_variables(project_id: str, agent_id: str, registry: AgentRegistry) -> dict:
    """Build dynamic SOUL template variables from live system state."""
    agent = registry.get(agent_id)
    jarvis = JarvisState(get_state_path(project_id))
    state = jarvis.read_state()

    subordinates = registry.get_subordinates(agent_id)
    active_tasks = [t for t in state.get("tasks", {}).values()
                    if t.get("status") in ("pending", "in_progress")]

    return {
        "superior_name": registry.get(agent.reports_to).name if agent.reports_to else "None",
        "superior_id": agent.reports_to or "N/A",
        "peer_agents": ", ".join(
            a.name for a in registry.list_by_level(agent.level) if a.id != agent_id
        ),
        "subordinate_agents": ", ".join(s.name for s in subordinates),
        "active_task_count": str(len(active_tasks)),
        "pool_utilization": f"{len(active_tasks)}/{agent.max_concurrent}",
    }
```

#### A5.3 — Inject at Spawn Time

Update `spawn.py`'s SOUL building to include dynamic variables:

```python
def _build_augmented_soul(project_root, memory_context, project_id, agent_id):
    """Build SOUL with static + dynamic + memory context."""
    static_vars = build_variables(load_project_config(project_id))
    dynamic_vars = build_dynamic_variables(project_id, agent_id, registry)
    all_vars = {**static_vars, **dynamic_vars}

    soul = render_soul(project_id, extra_variables=all_vars)
    if memory_context:
        soul += f"\n\n# Memory Context\n{memory_context}"
    return soul
```

### Validation

| Check | Command | Expected |
|---|---|---|
| Dynamic vars populate | `render_soul("pumplai", extra_variables=dynamic_vars)` | Template filled with live data |
| SOUL includes hierarchy | Inspect L3 `/run/openclaw/soul.md` | Hierarchy section present |
| Pool utilization shows | Spawn 2 tasks → check SOUL of 3rd | Shows "2/3" utilization |

---

## Phase A6: Cross-Runtime Observability — Unified Monitoring

**Priority**: P2 (medium)
**Effort**: ~4 hours
**Risk**: Low
**Depends on**: A3 (event bridge)

### Rationale

Currently there are two monitoring paths:
- `openclaw-monitor` (Python CLI) — polls `workspace-state.json` for L3 task status
- openclaw gateway UI — shows agent conversations and tool executions

Unifying these gives a single view of the entire system: L1 directives → L2 routing → L3 execution → review → merge.

### Steps

#### A6.1 — Extend Monitor to Subscribe to Events

Update `cli/monitor.py` to optionally use the event bridge instead of polling:

```python
async def tail_events(project_id: str):
    """Stream events in real-time instead of polling workspace-state.json."""
    transport = UnixSocketTransport()
    await transport.subscribe("openclaw.*", lambda event:
        render_event(event, project_id)
    )
```

#### A6.2 — Add Orchestration Metrics Endpoint

Create a metrics endpoint in the orchestration package that the dashboard can consume:

```python
# packages/orchestration/src/openclaw/metrics.py

def collect_metrics(project_id: str) -> dict:
    """Collect orchestration metrics for dashboard consumption."""
    jarvis = JarvisState(get_state_path(project_id))
    state = jarvis.read_state()

    return {
        "tasks": {
            "total": len(state.get("tasks", {})),
            "pending": len([t for t in state["tasks"].values() if t["status"] == "pending"]),
            "in_progress": len([t for t in state["tasks"].values() if t["status"] == "in_progress"]),
            "completed": len([t for t in state["tasks"].values() if t["status"] == "completed"]),
            "failed": len([t for t in state["tasks"].values() if t["status"] == "failed"]),
        },
        "pool": {
            "active_containers": pool_registry.active_count(project_id),
            "max_concurrent": get_pool_config(project_id).get("max_concurrent", 3),
        },
        "memory": {
            "healthy": await memory_client.health(),
            "last_retrieval": ...,
        },
        "autonomy": {
            "active_contexts": len(list_active_contexts()),
            "escalations_24h": ...,
        },
    }
```

#### A6.3 — Dashboard Integration

Update `packages/dashboard/` to consume the metrics endpoint and display:
- Real-time task pipeline (pending → executing → review → merged)
- Pool utilization gauge per project
- Agent hierarchy tree with live status indicators
- Memory health and recent retrievals
- Autonomy confidence heatmap

#### A6.4 — Structured Event Logging

Wire all event types to the structured JSON logger for post-hoc analysis:

```python
# In event bridge subscriber
def log_event(event: OrchestratorEvent):
    logger.info(
        f"{event.type.value}",
        extra={
            "event_domain": event.domain.value,
            "project_id": event.project_id,
            "agent_id": event.agent_id,
            "task_id": event.task_id,
            "correlation_id": event.correlation_id,
        }
    )
```

### Validation

| Check | Command | Expected |
|---|---|---|
| Event tail works | `openclaw-monitor tail --events` | Streams events in real-time |
| Metrics endpoint | `curl localhost:6987/api/metrics?project=pumplai` | Returns JSON metrics |
| Dashboard shows pipeline | Open OCCC → Tasks view | Live task pipeline visible |
| Logs are structured | `cat logs/*.jsonl \| jq '.event_domain'` | Events logged as JSON |

---

## Implementation Order & Dependencies

```
Week 1 (Foundation)
├── A1: Gateway Client (4h) ─────────────────────┐
│   └── Replace execFileSync with HTTP dispatch    │
├── A2: Agent Registry (3h) ─── parallel with A1 ─┤
│   └── Single source of truth for agent configs   │
│                                                   │
Week 2 (Integration)                                │
├── A3: Event Bridge (5h) ◄── depends on A1 ───────┘
│   └── Replace polling with event-driven state
├── A4: Sandbox Unification (6h) ◄── depends on A1, A2
│   └── Route L3 through openclaw sandbox API
│
Week 3 (Polish)
├── A5: Dynamic SOUL (3h) ◄── depends on A2, A3
│   └── Live hierarchy/state in SOUL templates
└── A6: Unified Monitoring (4h) ◄── depends on A3
    └── Real-time metrics + dashboard integration
```

**Total estimated effort**: ~25 hours across 3 weeks

---

## Success Criteria

### A1 (Gateway Dispatch)
- [x] `GatewayClient.dispatch()` replaces `execFileSync` in router
- [x] Streaming dispatch works for long-running agent tasks
- [x] Fallback to CLI when gateway is down
- [x] <100ms dispatch latency (vs ~2s for subprocess)

### A2 (Agent Registry)
- [x] Single `AgentRegistry` class loads from both config sources
- [x] `openclaw-config sync-agents` generates `agents/*/config.json`
- [x] Hierarchy validation catches circular chains and missing parents
- [x] Adding a new agent requires editing only `openclaw.json`

### A3 (Event Bridge)
- [x] Events flow from Python → TypeScript and back
- [x] `JarvisState` emits events on all state mutations
- [x] Monitor can use events instead of polling (opt-in)
- [x] Event latency <50ms within the same machine

### A4 (Sandbox Unification)
- [x] L3 tasks can spawn through openclaw sandbox API
- [x] Same volume mounts, env vars, and security policies
- [x] Pool tracks tasks from both spawn paths
- [x] Feature flag controls which path is used

### A5 (Dynamic SOUL)
- [x] SOUL templates include live hierarchy and task context
- [x] L3 SOUL shows pool utilization at spawn time
- [x] L2 SOUL includes active subordinate count

### A6 (Unified Monitoring)
- [x] `openclaw-monitor tail --events` streams real-time events
- [x] Dashboard shows task pipeline with live updates
- [x] All events logged as structured JSON
- [x] Metrics endpoint provides system-wide health view

---

## Appendix A: New Files Summary

| File | Purpose | Phase |
|---|---|---|
| `src/openclaw/gateway_client.py` | HTTP client for openclaw gateway | A1 |
| `src/openclaw/agent_registry.py` | Unified agent registry | A2 |
| `src/openclaw/events/protocol.py` | Cross-runtime event protocol | A3 |
| `src/openclaw/events/transport.py` | Unix socket event transport | A3 |
| `src/openclaw/sandbox_adapter.py` | Sandbox API adapter for L3 spawning | A4 |
| `src/openclaw/metrics.py` | Orchestration metrics collection | A6 |

## Appendix B: Modified Files Summary

| File | Change | Phase |
|---|---|---|
| `skills/router/index.js` | HTTP dispatch instead of execFileSync | A1 |
| `src/openclaw/config.py` | Add `get_gateway_config()` | A1 |
| `src/openclaw/project_config.py` | Registry integration | A2 |
| `config/openclaw.json` | Extended agent entries with `orchestration` block | A2 |
| `src/openclaw/state_engine.py` | Emit events on state mutations | A3 |
| `src/openclaw/autonomy/hooks.py` | Emit events via bridge | A3 |
| `skills/spawn/spawn.py` | Optional sandbox adapter path + dynamic SOUL | A4, A5 |
| `src/openclaw/soul_renderer.py` | Dynamic variable injection | A5 |
| `src/openclaw/cli/monitor.py` | Event-based tail mode | A6 |
| `packages/dashboard/` | Metrics integration + live pipeline | A6 |

## Appendix C: Agent Registry Schema (Unified)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["id", "name", "level"],
  "properties": {
    "id": { "type": "string", "pattern": "^[a-z_]+$" },
    "name": { "type": "string" },
    "level": { "type": "integer", "enum": [1, 2, 3] },
    "reports_to": { "type": ["string", "null"] },
    "subordinates": { "type": "array", "items": { "type": "string" } },
    "model": { "type": "string" },
    "provider": { "type": "string" },
    "orchestration": {
      "type": "object",
      "properties": {
        "role": { "type": "string", "enum": ["strategic", "coordinator", "domain", "executor"] },
        "max_concurrent": { "type": "integer", "minimum": 1 },
        "skill_registry": { "type": "array", "items": { "type": "string" } },
        "identity_ref": { "type": "string" },
        "soul_ref": { "type": "string" },
        "projects": { "type": "array", "items": { "type": "string" } },
        "container": {
          "type": "object",
          "properties": {
            "image": { "type": "string" },
            "mem_limit": { "type": "string" },
            "cpu_quota": { "type": "integer" }
          }
        },
        "runtime": {
          "type": "object",
          "properties": {
            "default": { "type": "string" },
            "supported": { "type": "array", "items": { "type": "string" } }
          }
        }
      }
    }
  }
}
```

## Appendix D: Event Protocol Wire Format

```json
{
  "type": "task.created",
  "domain": "openclaw.task",
  "project_id": "pumplai",
  "agent_id": "pumplai_pm",
  "task_id": "task-20260303-001",
  "payload": {
    "skill_hint": "code",
    "directive": "Implement user authentication",
    "metadata": { "priority": "high" }
  },
  "timestamp": 1709510400.123,
  "correlation_id": "run-abc123"
}
```

## Appendix E: Migration Path

The advanced plan is designed for **incremental adoption**:

1. **A1 (Gateway Client)** can be deployed independently — the fallback to `execFileSync` means zero downtime
2. **A2 (Agent Registry)** is read-only — it merges existing configs without modifying them until `sync-agents` is explicitly run
3. **A3 (Event Bridge)** is additive — the event bus supplements (not replaces) file-based state until the event path is proven stable
4. **A4 (Sandbox Adapter)** is behind a feature flag — `use_sandbox_adapter: false` keeps the Docker SDK path active
5. **A5 (Dynamic SOUL)** is backward compatible — new template variables use `safe_substitute()` so missing vars produce no errors
6. **A6 (Monitoring)** is opt-in — `--events` flag activates event-based tail, default remains polling

No phase requires all-at-once cutover. Each can be rolled out, validated, and rolled back independently.
