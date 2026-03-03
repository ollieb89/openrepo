# Phase 62: Structure Proposal Engine - Research

**Researched:** 2026-03-03
**Domain:** LLM-driven topology proposal generation, constraint validation, multi-dimensional rubric scoring, CLI presentation
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Outcome Input Design**
- Hybrid input: start with freeform text, engine asks 1-2 clarifying questions (risk tolerance, timeline pressure) before generating proposals
- Entry point: both CLI command (`openclaw propose`) and L1 directive. CLI is primary interface; L1 calls the same underlying engine
- Adaptive detail level: accept whatever the user gives. Minimal input → engine fills gaps with defaults and flags assumptions. Detailed input → engine respects all specifics
- Context-aware by default: read topology/changelog.json to avoid repeating rejected patterns. `--fresh` flag to generate without history influence

**Proposal Presentation**
- Comparative matrix layout: side-by-side with rows = dimensions (roles, scores, risk), columns = archetypes. Highlights where proposals differ most. Full justification below the matrix
- Rank-ordered by overall confidence (highest first). Position implies preference without labeling one as "the" recommendation. Non-prescriptive
- ASCII DAG visualization for topology structure: roles as nodes, edges labeled by type (delegation, coordination, etc.). Visual and immediately readable in terminal
- Assumptions shown in shared section above proposals: one "Assumptions" block with common inferences shown once. Keeps proposals clean

**Constraint Linter Behavior**
- Unknown agent roles: reject the invalid proposal variant and regenerate with valid roles only. Show what was rejected and why. User never sees invalid proposals
- Pool limit violations: auto-constrain — automatically adjust topology to fit within max_concurrent limits (reduce parallelism, sequence work). Note the constraint and show what changed
- Lint timing: after LLM generation. LLM generates freely with constraints as prompt guidance, linter validates and rejects/adjusts after. Simpler pipeline
- Retry limit: 2 retries max (3 total attempts). If all fail linting, show best-effort proposals with constraint violations highlighted. User decides

**Rubric Scoring Display**
- Score format: 0-10 integers per dimension. Easy to compare at a glance. "Complexity: 3/10, Risk: 7/10"
- Emphasis: highlight the 2-3 dimensions where proposals differ most. Show all 7, but visually call out key differentiators
- Preference fit pre-Phase 64: default baseline of 5/10 (neutral) for all proposals with note "No correction history yet". Keeps rubric structure consistent. Phase 64 replaces with real scores
- Overall confidence: weighted average of 7 dimensions. Weights configurable in topology config. Transparent, reproducible, tunable
- Low confidence warning: visual warning on proposal if overall confidence < threshold. "Low confidence — consider simplifying the outcome or adding constraints." Non-blocking, informational

### Claude's Discretion
- LLM prompt engineering strategy (single prompt vs per-archetype)
- Exact clarifying questions in hybrid input flow
- ASCII DAG rendering algorithm
- Constraint injection format in LLM prompts
- Rubric dimension weight defaults
- Error handling for LLM API failures
- JSON schema for proposal output validation

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PROP-01 | User can submit an outcome description and receive 2-3 topology proposals (Lean/Balanced/Robust archetypes) | Hybrid input flow + LLM generation pipeline + CLI entry point pattern |
| PROP-02 | Each proposal includes: roles, hierarchy, delegation boundaries, coordination model, risk assessment, estimated complexity, and confidence level | JSON schema for LLM output + Pydantic model for proposal data object |
| PROP-03 | Each proposal is scored across a common rubric: complexity, coordination overhead, risk containment, time-to-first-output, cost estimate, preference fit, overall confidence | RubricScorer class pattern mirroring ConfidenceFactors; weighted average with configurable weights |
| PROP-04 | Each proposal includes written justification explaining why this structure fits the given outcome | LLM structured output with justification field per archetype |
| PROP-05 | System validates proposals against constraints (available agent types, resource limits, project config) before presenting to user | ConstraintLinter reads AgentRegistry + project max_concurrent; reject/adjust loop up to 3 attempts |
| PROP-06 | Proposal confidence scores are comparative across candidates (not absolute) so user can see relative strengths | Comparative matrix renderer highlights dimension deltas between proposals |
</phase_requirements>

---

## Summary

Phase 62 builds the Structure Proposal Engine on top of the topology data model from Phase 61. The engine has four major components: (1) a hybrid input pipeline that asks 1-2 clarifying questions before invoking the LLM, (2) an LLM generation layer that produces structured JSON topology proposals for each archetype, (3) a constraint linter that validates and auto-adjusts proposals against `AgentRegistry` and `max_concurrent` limits, and (4) a CLI presenter that renders a comparative matrix with ASCII DAG visualizations.

The key architectural insight is that this is a pure Python CLI command (`openclaw-propose`) registered as a `[project.scripts]` entry point in `pyproject.toml`, following the exact same pattern as `openclaw-monitor`, `openclaw-project`, `openclaw-suggest`, and `openclaw-config`. The LLM call produces structured JSON (validated by a Pydantic model), the linter operates on that model before it ever reaches the terminal, and the renderer formats the result. All three concerns are cleanly separable modules.

The most nuanced design challenge is the LLM prompt strategy. A single prompt requesting all three archetypes simultaneously is preferred over three per-archetype calls — it produces comparative thinking naturally and avoids three separate round trips. The JSON schema for the LLM response must be strict enough to pass Pydantic validation but permissive enough to allow the LLM creative latitude on role naming within valid registry bounds.

**Primary recommendation:** Build as `packages/orchestration/src/openclaw/topology/` subpackage. LLM generation in `proposer.py`, constraint linting in `linter.py`, rubric scoring in `rubric.py`, ASCII rendering in `renderer.py`, and CLI entry point in `cli/propose.py`.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pydantic` | v2 (via existing project deps or add) | Proposal JSON schema validation, LLM output parsing | Already patterns for dataclass usage; Pydantic v2 is the ecosystem standard for structured LLM output parsing |
| `anthropic` or `httpx` | existing `httpx>=0` in deps | LLM API calls for proposal generation | Project already uses `httpx` for async HTTP; Anthropic SDK or raw httpx call both work |
| `argparse` | stdlib | CLI argument parsing | Used by ALL existing CLI commands; no deviation |
| `fcntl` | stdlib | File locking for topology/changelog.json reads | Established pattern from `state_engine.py` |
| `json` | stdlib | Topology file I/O | Used throughout codebase |
| `dataclasses` | stdlib | Internal data objects where Pydantic not needed | Established pattern (AgentSpec, JarvisState) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `jsonschema` | `>=4.26.0` (already in deps) | Schema-validate LLM output before Pydantic parse | First line of defense before Pydantic; already imported in project |
| `textwrap` | stdlib | ASCII table formatting, DAG indentation | Terminal formatting |
| `shutil.get_terminal_size` | stdlib | Adaptive terminal width for matrix layout | Terminal width detection |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Single LLM prompt for 3 archetypes | 3 separate per-archetype LLM calls | Single prompt is faster and produces naturally comparative output; per-archetype allows more focused prompting but 3x cost/latency |
| Pydantic v2 for LLM output parsing | Custom JSON schema + manual validation | Pydantic v2 gives free field validation, error messages, and `.model_dump()` for serialization |
| `argparse` CLI | `click` | `argparse` is the established project pattern — all 4 existing CLIs use it |

**Installation:**
No new packages required. If Pydantic not already available:
```bash
uv add pydantic
```
Check first: `uv run python -c "import pydantic; print(pydantic.__version__)"` — if already transitive, no action needed.

---

## Architecture Patterns

### Recommended Project Structure
```
packages/orchestration/src/openclaw/
├── topology/                    # New subpackage (Phase 61 + 62)
│   ├── __init__.py              # Exports TopologyGraph, TopologyProposal
│   ├── models.py                # Phase 61: TopologyGraph, TopologyNode, TopologyEdge
│   ├── classifier.py            # Phase 61: ArchetypeClassifier
│   ├── storage.py               # Phase 61: fcntl-based topology file I/O
│   ├── proposer.py              # Phase 62: LLM generation pipeline
│   ├── linter.py                # Phase 62: ConstraintLinter (AgentRegistry validation)
│   ├── rubric.py                # Phase 62: RubricScorer (7-dimension scoring)
│   └── renderer.py              # Phase 62: ASCII DAG + comparative matrix
└── cli/
    └── propose.py               # Phase 62: openclaw-propose CLI entry point
```

### Pattern 1: LLM Proposal Generation (Single Prompt, All Archetypes)

**What:** One structured LLM call requesting a JSON object with three archetype keys. The prompt embeds the outcome description, clarifying answers, context from changelog.json (unless `--fresh`), and available agent roles from AgentRegistry.

**When to use:** Always. Per-archetype calls are reserved only if the single prompt consistently fails schema validation after retry exhaustion.

**Example:**
```python
# packages/orchestration/src/openclaw/topology/proposer.py

PROPOSAL_SYSTEM_PROMPT = """
You are an expert at designing multi-agent swarm topologies.
Given an outcome description, generate exactly 3 topology proposals:
one Lean (minimal roles, fast), one Balanced (moderate structure), one Robust (safe, redundant).

Available agent roles: {available_roles}
Project constraint: max {max_concurrent} concurrent L3 agents

Return ONLY valid JSON matching this schema:
{json_schema}

Do not include markdown fences or explanation outside the JSON.
"""

async def generate_proposals(
    outcome: str,
    clarifications: dict[str, str],
    registry: AgentRegistry,
    project_max_concurrent: int,
    changelog_context: str | None,  # None when --fresh
) -> dict:
    """Call LLM and return raw JSON dict. Validation happens in linter."""
    available_roles = [s.id for s in registry._agents.values()]
    prompt = PROPOSAL_SYSTEM_PROMPT.format(
        available_roles=available_roles,
        max_concurrent=project_max_concurrent,
        json_schema=PROPOSAL_JSON_SCHEMA,
    )
    # httpx call to LLM API
    response = await _call_llm(prompt, outcome, clarifications, changelog_context)
    return json.loads(response)
```

### Pattern 2: Constraint Linter with Retry Loop

**What:** Validate each archetype proposal against AgentRegistry known IDs and project max_concurrent. Reject invalid roles (regenerate), auto-constrain pool violations (adjust). Up to 3 total attempts.

**When to use:** Always — runs between LLM generation and CLI presentation.

```python
# packages/orchestration/src/openclaw/topology/linter.py

class LintResult:
    valid: bool
    adjusted: bool          # True if pool sizes were auto-constrained
    rejected_roles: list[str]  # Roles not in registry
    adjustments: list[str]  # Human-readable change log (e.g., "4 parallel L3 → 3 (max_concurrent limit)")
    proposal: dict          # The (possibly adjusted) proposal

class ConstraintLinter:
    def __init__(self, registry: AgentRegistry, max_concurrent: int):
        self.registry = registry
        self.max_concurrent = max_concurrent

    def lint(self, archetype: str, proposal_data: dict) -> LintResult:
        """
        Returns LintResult:
        - If unknown roles: valid=False, rejected_roles=[...], proposal unchanged
        - If pool violations: valid=True, adjusted=True, adjustments=[...], proposal auto-corrected
        - If clean: valid=True, adjusted=False
        """
        # Step 1: Check all node roles against registry
        # Step 2: If bad roles → return invalid (trigger LLM retry with bad roles listed)
        # Step 3: If pool violations → auto-constrain parallelism, log adjustments
        ...

MAX_RETRIES = 2  # 3 total attempts (initial + 2 retries)
```

### Pattern 3: Rubric Scoring (7-Dimension)

**What:** Score each proposal 0-10 across 7 dimensions. Derive from proposal topology structure, not LLM opinion. Weighted average produces overall_confidence.

**When to use:** After linting succeeds. Scores are computed deterministically from the topology data object.

```python
# packages/orchestration/src/openclaw/topology/rubric.py

DIMENSIONS = [
    "complexity",          # node count, edge count
    "coordination_overhead",  # coordination edge count
    "risk_containment",    # review gate count, fallback role presence
    "time_to_first_output", # chain depth (shorter = faster)
    "cost_estimate",       # total role count (proxy for token/resource cost)
    "preference_fit",      # 5/10 default until Phase 64
    "overall_confidence",  # weighted average of above 6
]

DEFAULT_WEIGHTS = {
    "complexity": 0.15,
    "coordination_overhead": 0.15,
    "risk_containment": 0.20,
    "time_to_first_output": 0.20,
    "cost_estimate": 0.10,
    "preference_fit": 0.20,
}

@dataclass
class RubricScore:
    complexity: int
    coordination_overhead: int
    risk_containment: int
    time_to_first_output: int
    cost_estimate: int
    preference_fit: int       # Always 5 pre-Phase 64
    overall_confidence: int   # Weighted average rounded to int
    key_differentiators: list[str]  # Dimensions where this proposal differs most vs others

def score_proposal(topology: TopologyGraph, weights: dict = DEFAULT_WEIGHTS) -> RubricScore:
    ...
```

### Pattern 4: ASCII DAG Renderer

**What:** Render topology nodes as box-drawn ASCII with edges as labeled connectors. `tree`-command aesthetic with edge type labels.

**When to use:** Per proposal, rendered below the comparative matrix.

```
Lean Topology:
  [clawdia_prime] ─(delegation)→ [l3_specialist]

Balanced Topology:
  [clawdia_prime]
    ─(delegation)→ [pumplai_pm]
        ─(delegation)→ [l3_specialist_a]
        ─(coordination)→ [l3_specialist_b]
    ─(review-gate)→ [docs_pm]

Robust Topology:
  [clawdia_prime]
    ─(delegation)→ [pumplai_pm]
        ─(delegation)→ [l3_specialist_a]
        ─(delegation)→ [l3_specialist_b]
        ─(escalation)→ [clawdia_prime]
    ─(review-gate)→ [docs_pm]
    ─(coordination)→ [nextjs_pm]
```

**Algorithm:** Topological sort on DAG nodes, then DFS-style indented rendering with edge type annotations. Use `textwrap` for line length control. Pure string manipulation — no external libraries.

### Pattern 5: Comparative Matrix Layout

**What:** Terminal-width-adaptive table. Rows = rubric dimensions + roles summary. Columns = archetypes. Key differentiators highlighted with ANSI bold.

```
ASSUMPTIONS
  - Risk tolerance: medium (from clarifying answers)
  - Timeline pressure: not specified → defaulting to moderate

╔═══════════════════════╦══════════════╦══════════════╦══════════════╗
║ Dimension             ║ Lean         ║ Balanced     ║ Robust       ║
╠═══════════════════════╬══════════════╬══════════════╬══════════════╣
║ Complexity            ║ 2/10         ║ 5/10         ║ 8/10         ║
║ Coordination overhead ║ 1/10         ║ 4/10         ║ 7/10 *       ║
║ Risk containment      ║ 3/10 *       ║ 6/10         ║ 9/10 *       ║
║ Time to first output  ║ 9/10 *       ║ 6/10         ║ 4/10         ║
║ Cost estimate         ║ 9/10         ║ 6/10         ║ 3/10         ║
║ Preference fit        ║ 5/10 ~       ║ 5/10 ~       ║ 5/10 ~       ║
║ Overall confidence    ║ 6/10         ║ 6/10         ║ 6/10         ║
╚═══════════════════════╩══════════════╩══════════════╩══════════════╝
* = key differentiator  ~ = no correction history yet
```

### Pattern 6: Context-Aware History Reading

**What:** Before LLM call (unless `--fresh`), read `topology/changelog.json` and extract rejected patterns to inject as negative examples.

```python
def _load_rejection_context(project_id: str) -> str | None:
    """Read changelog.json, filter entries with correction_type='rejected',
    return formatted string of rejected pattern summaries for LLM prompt."""
    changelog_path = get_project_root() / "workspace" / ".openclaw" / project_id / "topology" / "changelog.json"
    if not changelog_path.exists():
        return None
    # Filter for rejected entries, summarize archetype + reason
    # Return: "Previously rejected: flat topology (low risk containment) on 2026-02-01"
    ...
```

### Anti-Patterns to Avoid

- **Validating LLM output inside the prompt system:** The linter is a separate Python class — do not embed constraint enforcement in prompt text only. Prompt guidance is advisory; linter enforcement is authoritative.
- **Caching LLM responses between runs:** Proposal generation is inherently context-sensitive (outcome text, changelog state changes). No response caching.
- **Blocking clarifying question loop in non-interactive mode:** If stdin is not a TTY (`not sys.stdin.isatty()`), skip clarifying questions and proceed with defaults flagged as assumptions. Same `_is_interactive()` pattern used in `cli/project.py`.
- **Writing topology/current.json from the proposal engine:** Phase 62 only proposes — it does NOT write approved topology. Writing is Phase 63 (correction/approval). Proposal output is ephemeral (printed to terminal only).
- **Separate config key collision:** Never use `autonomy.confidence_threshold` for topology. Use `topology.proposal_confidence_warning_threshold`. This is a locked v2.0 decision.
- **Exposing Phase 64 preference_fit logic here:** Phase 62 hardcodes `preference_fit = 5/10` with a note. Phase 64 will override the scoring function. Do not build placeholder hooks that increase complexity now.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM structured output parsing | Custom regex parser | Pydantic model + `jsonschema` pre-validation | JSON schema validation catches structural errors; Pydantic provides field-level validation with clear error messages |
| Terminal width detection | Hardcoded 80-char assumption | `shutil.get_terminal_size(fallback=(80, 24))` | stdlib; handles piped output gracefully |
| JSON atomic write | Direct `open().write()` | Write to `.tmp`, then `Path.rename()` | Atomic rename prevents corrupt state on crash; already established in `suggest.py` |
| File locking | Custom lock files | `fcntl.flock()` per `state_engine.py` pattern | Proven pattern already in codebase; handles concurrent access correctly |
| Archetype classification | Re-implement in proposer | Import Phase 61 `ArchetypeClassifier` | Phase 61 owns this; use it to validate that generated proposals actually match claimed archetypes |

**Key insight:** The LLM is not the source of truth for archetype labels. The LLM proposes structure; the `ArchetypeClassifier` from Phase 61 verifies the label is accurate. Mismatch = flag it (not fail it) since the topology might be a valid hybrid.

---

## Common Pitfalls

### Pitfall 1: LLM Returns Markdown-Wrapped JSON
**What goes wrong:** Many LLM providers wrap JSON in ```json ... ``` fences even when instructed not to. `json.loads()` fails.
**Why it happens:** LLMs default to markdown formatting in chat contexts.
**How to avoid:** Strip markdown fences before parse: `text = re.sub(r'^```json\s*|\s*```$', '', text.strip())`. Apply before `json.loads()` always.
**Warning signs:** `json.JSONDecodeError` on `{` or `[` not being first char.

### Pitfall 2: Retry Loop Infinite on Persistent Registry Mismatch
**What goes wrong:** LLM keeps generating the same role name that isn't in the registry across all 3 attempts (e.g., inventing `"ml_engineer"` that doesn't exist).
**Why it happens:** The LLM prompt lists available roles but the model ignores it when the invented role seems "obviously correct" for the outcome.
**How to avoid:** On retry, explicitly inject the rejected role names: `"DO NOT use these roles (not in registry): ml_engineer, data_scientist"`. Hard-list them in the retry prompt.
**Warning signs:** Same role rejected on attempt 1 and attempt 2 → ensure retry prompt includes the explicit blocklist.

### Pitfall 3: Auto-Constrain Silently Removes Critical Edges
**What goes wrong:** Pool limit enforcement reduces parallelism by removing parallel nodes, but the removed node held the only review-gate edge. Topology becomes less safe but linter reports "valid".
**Why it happens:** Linter auto-constrains by counting nodes, not by analyzing edge semantics.
**How to avoid:** When auto-constraining, prefer collapsing coordination edges before removing review-gate edges. If removing a node would eliminate all review-gate edges, log a warning in adjustments: `"WARNING: Pool reduction removed the only review gate; consider Lean archetype instead"`. Non-blocking but visible.
**Warning signs:** Robust proposal after auto-constrain has `risk_containment` score < Balanced proposal.

### Pitfall 4: Clarifying Question Loop Blocks L1 Directive Path
**What goes wrong:** When `openclaw-propose` is called from L1 router (non-interactive), the clarifying question loop hangs waiting for stdin.
**Why it happens:** `input()` blocks when stdin is piped from the router.
**How to avoid:** Use the `_is_interactive()` pattern from `cli/project.py`. If `not sys.stdin.isatty()`: skip clarifying questions entirely, log defaults used as assumptions in the output, proceed to LLM call immediately.
**Warning signs:** Router dispatch hangs indefinitely; no timeout triggers.

### Pitfall 5: Comparative Matrix Unreadable on Narrow Terminals
**What goes wrong:** The 4-column matrix (label + 3 archetypes) exceeds terminal width on 80-char terminals, causing wrapping that destroys alignment.
**Why it happens:** Table assumes wide terminal.
**How to avoid:** Use `shutil.get_terminal_size(fallback=(80, 24)).columns`. If terminal < 100 chars, switch from side-by-side to stacked layout (one archetype block at a time). The stacked layout still shows all dimensions but not simultaneously.
**Warning signs:** Test in an 80-col terminal explicitly.

### Pitfall 6: config.py Schema Rejecting New `topology` Key
**What goes wrong:** `OPENCLAW_JSON_SCHEMA` in `config.py` uses `"additionalProperties": False` at the top level. Adding `topology.proposal_confidence_warning_threshold` to `openclaw.json` causes schema validation to fail at startup.
**Why it happens:** The schema validator enforces no unknown top-level keys.
**How to avoid:** Add `"topology": {"type": "object", "properties": {...}}` to `OPENCLAW_JSON_SCHEMA["properties"]` in `config.py` as part of Phase 62. Required — not optional.
**Warning signs:** Config validation error at startup after updating `openclaw.json`.

---

## Code Examples

### CLI Entry Point (Following project.py Pattern)
```python
# packages/orchestration/src/openclaw/cli/propose.py
import argparse
import sys
from openclaw.config import get_project_root
from openclaw.project_config import get_active_project_id
from openclaw.agent_registry import AgentRegistry
from openclaw.topology.proposer import generate_proposals_sync
from openclaw.topology.linter import ConstraintLinter, MAX_RETRIES
from openclaw.topology.rubric import score_proposals, find_key_differentiators
from openclaw.topology.renderer import render_matrix, render_dags

class Colors:
    # Match existing ANSI pattern from project.py, monitor.py
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

def _is_interactive() -> bool:
    return sys.stdin.isatty()

def main() -> int:
    parser = argparse.ArgumentParser(description="OpenClaw Structure Proposal Engine")
    parser.add_argument("outcome", nargs="?", help="Outcome description (or reads from stdin)")
    parser.add_argument("--project", help="Project ID (default: active project)")
    parser.add_argument("--fresh", action="store_true", help="Generate without changelog history influence")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of formatted table")
    args = parser.parse_args()

    project_id = args.project or get_active_project_id()
    root = get_project_root()
    registry = AgentRegistry(root)
    # ... main flow
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### pyproject.toml Entry Point Registration
```toml
# packages/orchestration/pyproject.toml — add to [project.scripts]
openclaw-propose = "openclaw.cli.propose:main"
```

### Config Schema Extension
```python
# packages/orchestration/src/openclaw/config.py — add to OPENCLAW_JSON_SCHEMA properties
"topology": {
    "type": "object",
    "properties": {
        "proposal_confidence_warning_threshold": {
            "type": "number",
            "minimum": 0,
            "maximum": 10,
            "default": 5
        },
        "rubric_weights": {
            "type": "object",
            "properties": {
                "complexity":             {"type": "number"},
                "coordination_overhead":  {"type": "number"},
                "risk_containment":       {"type": "number"},
                "time_to_first_output":   {"type": "number"},
                "cost_estimate":          {"type": "number"},
                "preference_fit":         {"type": "number"},
            }
        }
    }
},
```

### LLM Output JSON Schema (for prompt injection and jsonschema validation)
```python
# packages/orchestration/src/openclaw/topology/proposer.py

PROPOSAL_JSON_SCHEMA = {
    "type": "object",
    "required": ["lean", "balanced", "robust"],
    "properties": {
        "lean":     {"$ref": "#/$defs/archetype_proposal"},
        "balanced": {"$ref": "#/$defs/archetype_proposal"},
        "robust":   {"$ref": "#/$defs/archetype_proposal"},
    },
    "$defs": {
        "archetype_proposal": {
            "type": "object",
            "required": ["roles", "hierarchy", "delegation_boundaries",
                         "coordination_model", "risk_assessment", "justification"],
            "properties": {
                "roles": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["id", "level", "intent", "risk_level"],
                        "properties": {
                            "id":         {"type": "string"},
                            "level":      {"type": "integer", "enum": [1, 2, 3]},
                            "intent":     {"type": "string"},
                            "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
                        }
                    }
                },
                "hierarchy": {"type": "array", "items": {
                    "type": "object",
                    "required": ["from_role", "to_role", "edge_type"],
                    "properties": {
                        "from_role": {"type": "string"},
                        "to_role":   {"type": "string"},
                        "edge_type": {"type": "string",
                                     "enum": ["delegation", "coordination", "review_gate",
                                              "information_flow", "escalation"]},
                    }
                }},
                "delegation_boundaries": {"type": "string"},
                "coordination_model":    {"type": "string"},
                "risk_assessment":       {"type": "string"},
                "justification":         {"type": "string"},
            }
        }
    }
}
```

### Topology Config Helper (get_topology_config)
```python
# Add to packages/orchestration/src/openclaw/config.py

def get_topology_config() -> dict:
    """Return topology configuration with defaults."""
    try:
        from openclaw.project_config import load_and_validate_openclaw_config
        config = load_and_validate_openclaw_config()
        topology = config.get("topology", {})
    except Exception:
        topology = {}
    return {
        "proposal_confidence_warning_threshold": topology.get(
            "proposal_confidence_warning_threshold", 5
        ),
        "rubric_weights": topology.get("rubric_weights", {
            "complexity": 0.15,
            "coordination_overhead": 0.15,
            "risk_containment": 0.20,
            "time_to_first_output": 0.20,
            "cost_estimate": 0.10,
            "preference_fit": 0.20,
        }),
    }
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single-turn LLM proposal | Hybrid input with clarifying questions | 2024+ (multi-turn UX pattern) | More targeted proposals; fewer "misses" on risk tolerance |
| Global confidence threshold | Separate topology vs autonomy threshold config keys | Phase 62 decision | Prevents mis-tuning: topology proposals have different semantics than autonomy execution confidence |
| JSON without schema enforcement | Structured output with jsonschema pre-validation + Pydantic | Post-GPT-4o widespread adoption | LLM outputs consistently parseable; fail fast before presentation |

**Deprecated/outdated:**
- Single monolithic "proposal" field on state: Topology proposals are ephemeral (print-only in Phase 62). Only Phase 63 approval persists to `topology/current.json`.

---

## Open Questions

1. **LLM Provider for Proposal Generation**
   - What we know: Project uses `google-gemini-cli/gemini-2.5-flash` as default model (from `openclaw.json`). The CLI tools (`openclaw-monitor`, etc.) are pure Python and call the orchestration layer, not an LLM directly. The proposal engine needs an LLM call.
   - What's unclear: Is there a centralized LLM client in the orchestration package, or should the proposer call the Anthropic/Gemini API via httpx directly? No existing `llm_client.py` found in the package.
   - Recommendation: Build a minimal `topology/llm_client.py` with provider-configurable async call (httpx). Support Anthropic and Gemini via env vars. Do not couple to a specific provider SDK to keep the package lightweight. Planner should create a task to decide provider default.

2. **Phase 61 Topology Model Availability**
   - What we know: Phase 61 context is defined; the `topology/` subpackage models are planned but Phase 61 has not been planned or executed yet. Phase 62 depends on Phase 61's data models (`TopologyGraph`, `TopologyNode`, `TopologyEdge`, `ArchetypeClassifier`).
   - What's unclear: The exact class names, field names, and module structure Phase 61 will produce.
   - Recommendation: Phase 62 planning should define Phase 61 interface contracts (import paths, class names) that Phase 62 assumes. The planner should create Phase 61 as a prerequisite wave or note the dependency explicitly. Phase 62 can stub-import Phase 61 classes during development and integrate when Phase 61 completes.

3. **Changelog.json Rejection Context Format**
   - What we know: Phase 61 defines `correction_type` field in diff entries. Phase 62 reads this file to avoid repeating rejected patterns.
   - What's unclear: The exact JSON structure Phase 61 will produce for `topology/changelog.json` — specifically what a "rejected" entry looks like vs an "approved" entry.
   - Recommendation: Phase 62 should defensively handle missing/unexpected changelog structures. Read changelog with `try/except`, gracefully degrade to `--fresh` behavior if format is unexpected.

---

## Integration Checklist for Planner

The following integration points are certain (HIGH confidence) and must each be a task or sub-task:

1. **`OPENCLAW_JSON_SCHEMA` update** — Add `topology` key to schema in `config.py` + `get_topology_config()` helper
2. **`pyproject.toml` entry point** — Add `openclaw-propose = "openclaw.cli.propose:main"` to `[project.scripts]`
3. **`openclaw.json` update** — Add `topology.proposal_confidence_warning_threshold` and `topology.rubric_weights` with defaults
4. **`topology/` subpackage** — `__init__.py`, `proposer.py`, `linter.py`, `rubric.py`, `renderer.py`
5. **`cli/propose.py`** — CLI entry point with `_is_interactive()` guard, `--project`, `--fresh`, `--json` flags
6. **`AgentRegistry` integration** — Linter imports `AgentRegistry` from `agent_registry.py` (already exists, no changes needed)
7. **Phase 61 import contract** — Define import path assumptions: `from openclaw.topology.models import TopologyGraph` etc.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `packages/orchestration/src/openclaw/agent_registry.py` — AgentSpec fields, AgentRegistry API
- Direct codebase inspection: `packages/orchestration/src/openclaw/autonomy/confidence.py` — ConfidenceFactors pattern, weighted aggregate scoring
- Direct codebase inspection: `packages/orchestration/src/openclaw/cli/project.py` — CLI pattern, `_is_interactive()`, `argparse` structure, `Colors` class
- Direct codebase inspection: `packages/orchestration/pyproject.toml` — Entry point registration pattern
- Direct codebase inspection: `packages/orchestration/src/openclaw/config.py` — `OPENCLAW_JSON_SCHEMA`, `additionalProperties: false` constraint, `get_autonomy_config()` pattern
- Direct codebase inspection: `openclaw.json` — Live config structure, no `topology` key yet
- Direct codebase inspection: `.planning/phases/62-structure-proposal-engine/62-CONTEXT.md` — All locked decisions
- Direct codebase inspection: `.planning/phases/61-topology-foundation/61-CONTEXT.md` — Phase 61 interface contract context

### Secondary (MEDIUM confidence)
- Project pattern inference: `textwrap`, `shutil.get_terminal_size` for terminal rendering — standard library, confirmed available
- Pattern from `cli/suggest.py`: atomic write via `.tmp` + `rename()`, lazy imports for circular import avoidance
- Pattern from `state_engine.py`: `fcntl.flock()` for topology file reading

### Tertiary (LOW confidence)
- LLM provider integration: assumed httpx-based call; no existing LLM client module found in package. Provider selection is Claude's discretion per CONTEXT.md.
- Pydantic v2 availability: not explicitly listed in `pyproject.toml` dependencies. May be a transitive dependency. Requires verification before planning.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are stdlib or already in pyproject.toml
- Architecture: HIGH — follows established codebase patterns exactly
- Pitfalls: HIGH — all derived from direct code analysis + well-known LLM integration patterns
- LLM integration details: MEDIUM — no existing LLM client in package; provider unknown

**Research date:** 2026-03-03
**Valid until:** 2026-04-03 (stable patterns, no fast-moving dependencies)
