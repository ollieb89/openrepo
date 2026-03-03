# Stack Research

**Domain:** AI Swarm Orchestration — v2.0 Structural Intelligence additions
**Researched:** 2026-03-03
**Confidence:** HIGH (all versions verified via PyPI index, npm registry, official docs)

---

## Scope

This document covers ONLY net-new stack needs for v2.0. It does not re-document the validated
baseline stack from v1.0–v1.6, which ships as-is:

**Existing baseline (unchanged):**
- Python stdlib: `asyncio`, `json`, `fcntl`, `threading`, `os`, `pathlib`
- `docker>=7.1.0`, `httpx`, `jsonschema>=4.26.0` — orchestration deps
- `fastapi`, `PostgreSQL + pgvector` — memU memory service (Docker)
- `Next.js 15`, `React 19`, `SWR`, `Tailwind CSS 3`, `Recharts`, `zod`, `lucide-react` — dashboard
- `better-sqlite3`, `dockerode` — dashboard API deps already present

The five feature areas in scope for v2.0:

1. **Topology as Data** — graph data structures, JSON serialization, versioning
2. **Structure Proposal Engine** — multi-proposal generation with LLM-structured scoring rubric
3. **Dual Correction System** — structural diff analysis (soft feedback / hard edit paths)
4. **Structural Memory** — topology diffs and preference profiling via existing memU
5. **Topology Observability** — node-based graph visualization in dashboard

---

## Recommended Stack

### Core Technologies — Net New (Python)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `networkx` | `>=3.6.1` | Graph data structure for topology model (DiGraph nodes = agents, edges = delegation) | Industry-standard Python graph library. `DiGraph` gives directed edges (L1→L2→L3 delegation direction), arbitrary node/edge attributes (agent role, container config, archetype metadata), and `node_link_data()` for JSON round-trip serialization that is natively readable by `@xyflow/react` on the dashboard. Pure Python, no C extensions, Python >=3.11 compatible. v3.6.1 released Dec 2025. Alternatives (igraph, graph-tool) require C extensions and are overkill for topologies of ≤20 nodes. |
| `deepdiff` | `>=8.6.1` | Structural diff of topology JSON objects for dual correction analysis | Provides `DeepDiff(old_topology, new_topology)` returning a typed change report: `dictionary_item_added`, `dictionary_item_removed`, `values_changed`, `iterable_item_added`. This maps cleanly onto topology diff semantics: added nodes, removed nodes, edge changes, attribute changes. The `Delta` class can reconstruct the edited topology from diff + original, which is required for the async correction analysis path. v8.6.1 released Jan 2026. Pure Python, tested on 3.9+, no native deps. `dictdiffer` considered but `deepdiff`'s `Delta` object makes patch-then-analyze pattern simpler. |
| `instructor` | `>=1.14.5` | Structured LLM output for scoring rubric generation (proposal engine) | Wraps Anthropic's `tool_use` to enforce a Pydantic schema on Claude responses. The scoring rubric has 7 fixed dimensions (complexity, coordination overhead, risk containment, time-to-first-output, cost estimate, preference fit, overall confidence) — `instructor` guarantees Claude returns a validated `RubricScore` Pydantic model, not free-text. Uses `Mode.TOOLS` with the existing Anthropic SDK. Eliminates JSON parsing errors in the critical proposal path. v1.14.5 released Jan 2026, 3M+ monthly downloads, full Anthropic support. Alternative: direct `tool_use` with manual schema — more fragile, requires custom retry logic that `instructor` already provides. |

### Supporting Libraries — Net New (Python)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pydantic` | `>=2.9` (already transitive via `instructor`) | Typed models for `TopologyGraph`, `ProposalCandidate`, `RubricScore`, `CorrectionDiff` | Define the canonical data shapes that flow between proposal engine, state engine, memU storage, and dashboard API. Pydantic v2 `model_dump(mode="json")` gives JSON-serializable dicts directly; `model_validate()` deserializes from storage. Already present as a transitive dep of `instructor` — not a new install. |
| `anthropic` | `>=0.40` (already used by existing agents) | LLM calls in proposal engine and correction analyzer | Existing SDK, already in the environment. `instructor` wraps it — no direct import needed in proposal engine code. Listed here to clarify: no SDK version change required. |

### Core Technologies — Net New (TypeScript/Dashboard)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `@xyflow/react` | `>=12.10.1` | Node-based topology visualization in dashboard | De-facto standard for node-edge diagrams in React. Renders the agent topology as an interactive graph (pan, zoom, select). Accepts `nodes[]` and `edges[]` arrays that map 1:1 to NetworkX `node_link_data` format — the backend serializes with NetworkX, the frontend renders with React Flow. v12 (package: `@xyflow/react`, not deprecated `reactflow`) is the current release as of late 2025. Supports SSR/SSG needed for Next.js 15. React 19 compatible. Latest verified version: 12.10.1. |
| `@dagrejs/dagre` | `>=2.0.4` | Hierarchical layout engine for topology DAG | Computes node positions for a directed acyclic graph (Sugiyama/layered layout), which matches the L1→L2→L3 hierarchy. Used alongside `@xyflow/react` via the documented "Dagre Layout" pattern — auto-positions nodes without manual coordinate entry. v2.0.4 is the current maintained fork of the original dagre. |

### Supporting Libraries — Net New (TypeScript/Dashboard)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `elkjs` | `>=0.11.1` | Alternative layout engine for complex topology proposals | ELK provides more sophisticated layouts (layered with port assignments, force-directed) than dagre for cases where three simultaneous proposals are shown side-by-side. Import lazily — only when rendering the multi-proposal comparison view. Do not replace dagre; use elk only for the proposal comparison panel. |

---

## What is Already Available — Do NOT Add

| Capability | Where It Lives | v2.0 Use |
|------------|---------------|---------|
| memU REST API (`/memorize`, `/retrieve`) | `docker/memory/memory_service/` on port 18791 | Structural memory storage: topology diffs, correction rationales, preference profiles stored as memU memories with `agent_id="topology_engine"` namespace. No API changes needed — use existing `memory_client.py` patterns. |
| `memory_client.py` | `packages/orchestration/src/openclaw/memory_client.py` | Retrieve structural preferences on proposal generation; store diffs on correction. Reuse `memorize()` and `retrieve()` directly. |
| State engine file locking (`fcntl.flock`) | `state_engine.py` | Topology proposals stored as JSON alongside `workspace-state.json` under the same locking discipline. New `topology-proposals.json` file follows the same `LOCK_EX` write / `LOCK_SH` read pattern. |
| SSE event transport | `events/transport.py` `event_bridge` | Topology proposal events, correction events, structural diff notes emitted via existing `OrchestratorEvent` protocol. New `EventDomain.TOPOLOGY` domain constant added to `events/protocol.py`. |
| Dashboard SSE hooks | `packages/dashboard/src/hooks/useEvents.ts` | Dashboard topology panel subscribes to `TOPOLOGY` domain events via existing SSE infrastructure. No new streaming mechanism. |
| `Recharts` | Already in `package.json` at `>=3.7.0` | Confidence score timeline (RadarChart for rubric dimensions, LineChart for confidence evolution) uses existing Recharts. No new charting library. |
| `zod` | Already in `package.json` at `>=3.23.8` | Validates topology API response shapes in dashboard API routes. No new validation library. |
| `jsonschema>=4.26.0` | Already in orchestration `pyproject.toml` | Validates topology JSON schemas at load time. No new install. |
| `better-sqlite3` | Already in `package.json` at `>=12.6.2` | Dashboard API reads correction history from state files. Same pattern as existing metrics routes. |
| `asyncio` stdlib | Used throughout orchestration | Correction analysis runs as a background task via `asyncio.create_task()` — existing pattern from `_run_memory_injector()`. No new async library. |

---

## Integration Points by Feature

### Feature 1: Topology as Data

**Python model** — `packages/orchestration/src/openclaw/topology/model.py` (new module):
```python
import networkx as nx
from networkx.readwrite import json_graph
import json

def build_topology(agents: list[dict], edges: list[dict]) -> nx.DiGraph:
    G = nx.DiGraph(archetype="balanced", version=1)
    for agent in agents:
        G.add_node(agent["id"], role=agent["role"], level=agent["level"])
    for edge in edges:
        G.add_edge(edge["source"], edge["target"], delegation_type=edge.get("type", "direct"))
    return G

def topology_to_json(G: nx.DiGraph) -> dict:
    return json_graph.node_link_data(G, edges="links")

def topology_from_json(data: dict) -> nx.DiGraph:
    return json_graph.node_link_graph(data, directed=True, edges="links")
```

**Persistence** — stored as `topology-proposals.json` in `workspace/.openclaw/{project_id}/` alongside `workspace-state.json`. Same locking discipline. Versioned with `version` integer field on the graph object.

**Wire format** — `node_link_data()` output is directly consumable by `@xyflow/react` with a thin transformer (node `id` → React Flow `id`, edge `source`/`target` already match).

### Feature 2: Structure Proposal Engine

**Structured scoring via instructor**:
```python
import instructor
from anthropic import Anthropic
from pydantic import BaseModel, Field

class RubricScore(BaseModel):
    complexity: float = Field(ge=0.0, le=1.0)
    coordination_overhead: float = Field(ge=0.0, le=1.0)
    risk_containment: float = Field(ge=0.0, le=1.0)
    time_to_first_output: float = Field(ge=0.0, le=1.0)
    cost_estimate: float = Field(ge=0.0, le=1.0)
    preference_fit: float = Field(ge=0.0, le=1.0)
    overall_confidence: float = Field(ge=0.0, le=1.0)
    justification: str

class ProposalCandidate(BaseModel):
    archetype: str  # "lean" | "balanced" | "robust"
    topology: dict  # node_link_data output
    score: RubricScore

client = instructor.from_anthropic(Anthropic())

def score_proposal(archetype: str, topology_json: dict, task_context: str) -> ProposalCandidate:
    return client.chat.completions.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": f"Score this {archetype} topology for task: {task_context}"}],
        response_model=ProposalCandidate,
    )
```

**Preference retrieval** — before generating proposals, call `memory_client.retrieve(agent_id="topology_engine", query=task_context, top_k=5)` to inject past correction rationales into the prompt. This is the learning loop.

### Feature 3: Dual Correction System

**Structural diff via deepdiff**:
```python
from deepdiff import DeepDiff, Delta

def analyze_correction(original_topology: dict, edited_topology: dict) -> dict:
    diff = DeepDiff(original_topology, edited_topology, ignore_order=True)
    return {
        "added_nodes": list(diff.get("iterable_item_added", {}).keys()),
        "removed_nodes": list(diff.get("iterable_item_removed", {}).keys()),
        "changed_edges": list(diff.get("dictionary_item_changed", {}).keys()),
        "raw_diff": diff.to_dict(),
    }
```

**Async analysis path** — on hard edit (user directly edits topology), execute immediately then `asyncio.create_task(analyze_and_store_correction(...))`. Analysis runs non-blocking, surfaces a note via SSE only if `overall_confidence` of original was ≥0.8 and the diff is non-trivial (>2 node changes). Follows the same daemon thread pattern as `_run_memory_extractor()` in `state_engine.py`.

### Feature 4: Structural Memory

**Storage** — topology diffs and correction rationales stored via existing `memory_client.memorize()` with:
- `agent_id="topology_engine"`
- `project_id` scoped (existing pattern)
- Content: `json.dumps({"diff": diff_result, "rationale": user_rationale, "original_archetype": archetype})`

**Preference profiling** — retrieved via `memory_client.retrieve(query="topology preferences for {task_type}")` at proposal generation time. No new data store. PostgreSQL + pgvector handles semantic similarity retrieval natively.

**No new tables or schema changes** — memU's `memories` table already has `agent_id`, `project_id`, `content`, `embedding` columns. Topology memories are just another agent namespace.

### Feature 5: Topology Observability (Dashboard)

**React Flow component** — new `TopologyCanvas.tsx` using `@xyflow/react` with dagre layout:
```typescript
import ReactFlow, { useNodesState, useEdgesState } from '@xyflow/react';
import dagre from '@dagrejs/dagre';

// Transform node_link_data from backend → React Flow nodes/edges
function topologyToFlow(topology: NodeLinkData): { nodes: Node[], edges: Edge[] } {
  const graph = new dagre.graphlib.Graph();
  // ... dagre layout calculation
  return { nodes: layoutedNodes, edges: layoutedEdges };
}
```

**Diff timeline** — `CorrectionTimeline.tsx` using Recharts `LineChart` for confidence evolution over corrections. Uses existing Recharts already installed. No new charting library.

**SSE subscription** — `useTopology()` hook subscribes to `EventDomain.TOPOLOGY` events via existing `useEvents.ts` infrastructure.

---

## Installation

```bash
# Python — orchestration package
# Edit packages/orchestration/pyproject.toml:
# dependencies = [
#   "docker>=7.1.0", "httpx", "jsonschema>=4.26.0",
#   "networkx>=3.6.1",
#   "deepdiff>=8.6.1",
#   "instructor>=1.14.5",
# ]

uv pip install "networkx>=3.6.1" "deepdiff>=8.6.1" "instructor>=1.14.5"

# Verify
python3 -c "import networkx; print(networkx.__version__)"  # 3.6.1
python3 -c "import deepdiff; print(deepdiff.__version__)"  # 8.6.1
python3 -c "import instructor; print(instructor.__version__)"  # 1.14.5

# TypeScript — dashboard
# Edit packages/dashboard/package.json dependencies:
# "@xyflow/react": "^12.10.1",
# "@dagrejs/dagre": "^2.0.4",
# "elkjs": "^0.11.1"  (optional, lazy-load for proposal comparison view)

cd packages/dashboard
pnpm add @xyflow/react @dagrejs/dagre elkjs
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `networkx>=3.6.1` | `igraph` (Python) | Use igraph if topologies exceed 1,000+ nodes and algorithmic performance matters. OpenClaw topologies are ≤20 nodes (L1=1, L2=1-3, L3=1-10) — networkx's pure Python is ample and has built-in JSON serialization. igraph requires C extensions and changes the API completely. |
| `networkx>=3.6.1` | Plain Python `dict` with adjacency lists | Acceptable for simple topologies but loses graph algorithm support (`nx.is_dag()`, `nx.topological_sort()`, cycle detection) which are needed to validate proposed topologies. Migration to networkx mid-project is more expensive than adopting it upfront. |
| `deepdiff>=8.6.1` | `dictdiffer` | Use dictdiffer if you only need diff reporting and not patch application. deepdiff's `Delta` class is required for the "reconstruct edited topology from original + diff" use case in the correction analysis path. dictdiffer has no equivalent. |
| `deepdiff>=8.6.1` | Custom dict comparison | Custom comparison is viable but requires re-implementing typed change categories (added/removed/changed), path extraction, and serialization. deepdiff provides all of this in 1 function call. |
| `instructor>=1.14.5` | Direct `tool_use` with manual Pydantic validation | Direct tool_use works but requires custom retry logic, schema generation, and response parsing. instructor provides all three, has 3M+ monthly downloads, and is battle-tested with Anthropic specifically. For a scoring rubric that must be validated on every proposal, the retry-on-validation-failure behavior of instructor is essential. |
| `instructor>=1.14.5` | Anthropic native structured outputs (beta) | Anthropic's structured outputs (beta, Nov 2025) uses `anthropic-beta: structured-outputs-2025-11-13` header. Viable but still in public beta as of Mar 2026. instructor wraps this internally and adds retry logic. Use native structured outputs directly in v2.1+ once it exits beta. |
| `@xyflow/react>=12.10.1` | `cytoscape.js` + `react-cytoscapejs` | Cytoscape is better for large graph analysis (1000+ nodes, complex algorithms). React Flow is better for interactive node-based UIs with custom node components — which is exactly what topology observability needs (custom nodes showing agent role, container status, confidence score). Cytoscape's React integration is also less maintained. |
| `@xyflow/react>=12.10.1` | `reagraph` (WebGL) | reagraph uses WebGL for large graphs (10,000+ nodes). OpenClaw topologies are ≤20 nodes — WebGL overhead is unjustified. React Flow's SVG rendering is simpler to style with Tailwind. |
| `@dagrejs/dagre` | `elkjs` (for default layout) | ELK is more capable but heavier. Use elkjs only for the side-by-side multi-proposal comparison panel where 3 topologies must be laid out simultaneously without overlap. Default single-topology view uses dagre (lighter, simpler API). |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `pydantic-graph` (pydantic-ai sub-library) | Designed for state machine workflow execution graphs, not data model graphs. API is oriented around running nodes as async callables, not storing/serializing/diffing topology structures as data. Confusingly named but wrong tool. | `networkx.DiGraph` for topology data model + `pydantic.BaseModel` for scoring/proposal schemas. |
| `graph-tool` (Python) | Requires compiled C++ extension, complex install, only available via conda or manual build. Completely unjustified for ≤20 node topologies. | `networkx>=3.6.1` — pure Python, pip installable. |
| `reactflow` (npm package) | The old package name. Replaced by `@xyflow/react` in v12. Using `reactflow` pins to v11 which is in maintenance mode and does not support React 19. | `@xyflow/react>=12.10.1`. |
| Adding new PostgreSQL tables for topology | topology proposals are already expressible as JSON files under the Jarvis Protocol state directory. Adding Postgres tables would require schema migrations, a new ORM, and changes to the memU service — disproportionate for what is essentially structured JSON. | Store as `topology-proposals.json` alongside `workspace-state.json` under existing `fcntl.flock` discipline. Use memU only for the preference/correction memory (free-text narratives + embeddings). |
| New embedding model or vector store | memU already runs PostgreSQL + pgvector with embeddings. Structural preferences retrieved via semantic similarity fit this model exactly. | Reuse existing `memory_client.retrieve()` with `agent_id="topology_engine"` namespace. Zero infrastructure change. |
| `numpy` in orchestration package | Established constraint from v1.3–v1.5 research. Not needed for topology math (networkx handles graph algorithms natively, scoring is float arithmetic). | Float arithmetic via stdlib `statistics.mean()` if aggregation is needed. |
| A separate "proposal store" database | The dashboard already reads from state files via `better-sqlite3` for metrics. A new database for proposals adds operational complexity with no advantage at this scale. | JSON files in state directory, served by new `/api/topology` Next.js route (same pattern as `/api/metrics`). |

---

## Stack Patterns by Variant

**If the proposal engine needs to batch-score all three archetypes in parallel:**
- Use `asyncio.gather()` with three concurrent `instructor` calls
- Each archetype scored independently — no shared state between calls
- Respect Anthropic rate limits; add `asyncio.Semaphore(2)` if needed

**If topology JSON exceeds 10KB (large swarms with many L3s):**
- Store topology in a separate `topology-{version}.json` file rather than embedding in workspace-state
- The `topology-proposals.json` index file holds metadata (archetype, confidence, timestamp) with a `file` pointer
- React Flow handles graphs up to ~500 nodes without performance issues

**If correction analysis should block (synchronous) rather than async:**
- Replace `asyncio.create_task()` with direct `await analyze_correction()`
- Only do this for testing or if the correction note must appear before the user proceeds
- Default behavior: async/non-blocking to respect user authority (design decision from PROJECT.md)

**If `@dagrejs/dagre` layout produces poor results for multi-tier hierarchy:**
- Switch the proposal comparison panel to `elkjs` with `algorithm: "layered"` and `elk.direction: "DOWN"`
- ELK's layered algorithm handles the L1→L2→L3 hierarchy better than dagre for >2 levels
- Keep dagre for the single-topology default view (simpler, faster)

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `networkx>=3.6.1` | Python >=3.11 | v3.6.1 requires Python >=3.11 (upgrade from 3.10). Confirm `packages/orchestration/pyproject.toml` `requires-python` is updated to `>=3.11`. All existing code is compatible — networkx uses no deprecated 3.10 features in OpenClaw's scope. |
| `deepdiff>=8.6.1` | Python >=3.9 | Compatible with Python 3.11. No conflicts with existing deps. |
| `instructor>=1.14.5` | `anthropic>=0.40` | instructor pulls in `anthropic` as a dep. If the existing environment has anthropic<0.40, instructor's install will upgrade it. Verify no breaking changes in the anthropic SDK version used by existing agent runners. |
| `@xyflow/react>=12.10.1` | React 19, Next.js 15 | v12 explicitly supports React 19 (confirmed via official blog). Next.js 15 App Router compatible. Dashboard already on React 19 (`"react": "^19"` in package.json). |
| `@dagrejs/dagre>=2.0.4` | `@xyflow/react>=12` | Standard pairing per React Flow documentation. `@dagrejs/dagre` v2 is the maintained fork — do not use the unmaintained `dagre` v0.8.x package. |
| `elkjs>=0.11.1` | `@xyflow/react>=12` | ELK runs in a Web Worker in production for non-blocking layout computation. Next.js requires `ssr: false` in dynamic import for the ELK worker. |

---

## Sources

- [networkx PyPI](https://pypi.org/project/networkx/) — v3.6.1 current, Python >=3.11, Dec 2025 (HIGH confidence, PyPI index verified)
- [NetworkX JSON serialization docs](https://networkx.org/documentation/stable/reference/readwrite/json_graph.html) — `node_link_data`, `node_link_graph` API (HIGH confidence, official docs)
- [deepdiff PyPI](https://pypi.org/project/deepdiff/) — v8.6.1 current, Python >=3.9 (HIGH confidence, PyPI index verified)
- [deepdiff 8.6.1 docs](https://zepworks.com/deepdiff/current/) — `DeepDiff`, `Delta`, `to_dict()` API (HIGH confidence, official docs)
- [instructor PyPI](https://pypi.org/project/instructor/) — v1.14.5 current, Jan 2026 (HIGH confidence, PyPI index verified)
- [instructor Anthropic integration](https://python.useinstructor.com/integrations/anthropic/) — `Mode.TOOLS`, `from_anthropic()` pattern (HIGH confidence, official docs)
- [Anthropic structured outputs beta](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) — `structured-outputs-2025-11-13` beta header (MEDIUM confidence — still in beta as of Mar 2026)
- [@xyflow/react npm](https://www.npmjs.com/package/@xyflow/react) — v12.10.1 current (HIGH confidence, npm registry verified)
- [React Flow v12 release notes](https://xyflow.com/blog/react-flow-12-release) — React 19 + Next.js SSR support confirmed (HIGH confidence, official blog)
- [@dagrejs/dagre npm](https://www.npmjs.com/package/@dagrejs/dagre) — v2.0.4 current (HIGH confidence, npm registry verified)
- [elkjs npm](https://www.npmjs.com/package/elkjs) — v0.11.1 current (HIGH confidence, npm registry verified)
- Codebase inspection of `packages/orchestration/pyproject.toml` — confirmed existing deps: `docker>=7.1.0`, `httpx`, `jsonschema>=4.26.0` (HIGH confidence, direct inspection)
- Codebase inspection of `packages/dashboard/package.json` — confirmed existing: `recharts>=3.7.0`, `zod>=3.23.8`, `better-sqlite3>=12.6.2`, `react: ^19`, `next: 15.x` (HIGH confidence, direct inspection)
- Codebase inspection of `packages/orchestration/src/openclaw/state_engine.py` — confirmed `fcntl.flock`, `asyncio.create_task` patterns for new feature integration (HIGH confidence, direct inspection)

---

*Stack research for: OpenClaw v2.0 Structural Intelligence*
*Researched: 2026-03-03*
*Previous baseline (v1.0–v1.6): Python stdlib + docker + httpx + jsonschema + Next.js 15 + memU/FastAPI/PostgreSQL+pgvector — all unchanged.*
*v2.0 net-new Python deps: networkx>=3.6.1, deepdiff>=8.6.1, instructor>=1.14.5*
*v2.0 net-new npm deps: @xyflow/react>=12.10.1, @dagrejs/dagre>=2.0.4, elkjs>=0.11.1*
