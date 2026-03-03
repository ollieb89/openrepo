# Phase 63: Correction System and Approval Gate - Research

**Researched:** 2026-03-03
**Domain:** Interactive CLI session management, soft/hard topology correction, approval gate, diff-based changelog, pushback notes
**Confidence:** HIGH — this phase builds on well-understood Phase 62 code; all domain research grounded in existing codebase inspection

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Soft Correction Flow**
- Same-session conversational loop: after proposals display, CLI stays interactive. User types feedback inline (e.g., "flatten the hierarchy", "add a review gate between coordinator and workers")
- Re-proposal scope is Claude's discretion: broad feedback regenerates all 3 archetypes, specific feedback targets only the relevant archetype(s)
- Re-proposals show diff (highlighted delta) AND full updated proposal below — user sees both the evolution and the complete picture
- 3-cycle limit (CORR-06): when hit, system presents the best version so far, explains what feedback asked for vs what the engine achieved, and offers to approve or directly edit. "Here's where I landed. Approve this or edit it yourself."
- Each re-proposal round goes through the same constraint linter pipeline as initial proposals

**Hard Correction UX**
- Export-edit-import workflow: system exports the selected proposal to `topology/proposal-draft.json` in annotated JSON format (JSONC with field descriptions, role names as keys, readable edge types). User edits in their editor, then the system imports on approval
- Tiered validation on import: unknown agent roles block execution with error. Pool limit violations get non-blocking warnings. Matches the constraint linter's existing reject/auto-adjust split
- File lives in project-scoped topology directory: `workspace/.openclaw/{project_id}/topology/proposal-draft.json`
- Parser strips annotations on import and converts back to TopologyGraph via from_dict()

**Approval Gate**
- Inline confirmation in the same session: after proposals display (or after correction), prompt user to approve by selecting the archetype name/number
- Proposals persist on session exit: saved to `topology/pending-proposals.json` so user can resume later with `openclaw approve` to pick up where they left off
- Approval writes directly to `current.json` and appends to `changelog.json` with the diff from previous version (if any). No intermediate staging step
- L1 directive approval is configurable per-project: `topology.auto_approve_l1` config key (default: false). Projects can opt into auto-approval for L1-generated proposals. Human-in-the-loop by default
- No L3 container spawn occurs until a topology version has been explicitly approved (CORR-07)

**High-Confidence Pushback**
- Surfaces both inline AND persisted to changelog: user sees the note immediately after approval, and it's written to `changelog.json` as an annotation on the diff entry for Phase 64 structural memory
- Separate higher threshold: new config key `topology.pushback_threshold` (e.g., 8/10) distinct from `topology.proposal_confidence_warning_threshold`. Only pushes back when system was very confident
- Dimension-specific detail: note names the exact rubric dimensions that shifted and by how much (e.g., "Your edit reduced risk containment from 8/10 to 3/10 by removing the review gate")
- Latest-only inline display: only show the most recent pushback note in the session. All notes are persisted to changelog for historical review
- Note is always non-blocking — never prevents execution (CORR-05)

### Claude's Discretion
- Session state management implementation (in-memory vs file-based for the interactive loop)
- Exact annotated JSON format and comment style for proposal-draft.json
- Re-proposal prompt engineering (how feedback gets injected into the LLM prompt)
- Diff rendering format for re-proposal deltas
- Exact wording of cycle-limit and pushback messages

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CORR-01 | User can give textual feedback on a proposal and receive a re-proposal that addresses the feedback (soft correction) | Interactive loop in propose.py extended with feedback input; re-proposal reuses generate_proposals_sync with feedback injected into prompt |
| CORR-02 | User can directly edit a proposed topology (add/remove/modify roles, change hierarchy) and the system executes the edited version (hard correction) | Export to proposal-draft.json via TopologyGraph.to_json(); import via TopologyGraph.from_dict() after stripping JSONC comments; ConstraintLinter validates on import |
| CORR-03 | System computes and stores the diff between proposed and approved topology after every correction | topology_diff() already exists; append_changelog() already exists; diff record written at approval time |
| CORR-04 | On hard correction, system executes immediately then analyzes the diff asynchronously | save_topology() + asyncio background task for diff recording; no blocking on diff analysis |
| CORR-05 | When system had high confidence and edit contradicts it, surfaces non-blocking informational note | RubricScore dimensions before vs after; compare using score_proposal(); note never raises exception or blocks |
| CORR-06 | System enforces a cycle limit (max 3 re-proposals per soft correction loop) | In-memory counter in interactive loop; at limit, present best-so-far ProposalSet and offer approve-or-edit |
| CORR-07 | User must explicitly approve a topology before it can be used for execution (approval gate) | approval gate check in skills/router/index.js before L3 dispatch; load_topology() checks for approved version |
</phase_requirements>

---

## Summary

Phase 63 adds an interactive correction layer on top of the Phase 62 proposal pipeline. The implementation is purely additive: all the data models, storage layer, diff engine, and rendering primitives already exist. The work is wiring them into a session loop with user-facing prompts, a file-based export/import path for hard corrections, and a gate check in the L1 router.

The interactive CLI session is the core design challenge. The `openclaw-propose` command must shift from a fire-and-exit pattern to a stateful loop that retains the current ProposalSet in memory, accepts user input, dispatches to either the re-proposal pipeline (soft) or the export/import path (hard), enforces the 3-cycle limit, and handles approval by writing to storage. Session exit saves `pending-proposals.json` so the user can resume with `openclaw approve`.

The approval gate for L1 routing is a check in `skills/router/index.js` that calls into Python (`load_topology()`) or checks the topology directory before dispatching an L3 spawn. This is a firewall boundary: if no approved topology exists, the directive is held or escalated.

**Primary recommendation:** Extend `openclaw-propose` main() into a session class with explicit state transitions; keep all data flowing through the established dataclass + fcntl + changelog pipeline.

---

## Standard Stack

### Core (already in project — no new installs required)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python dataclasses | stdlib | Session state, diff records | All topology models use @dataclass pattern |
| fcntl | stdlib | File locking for storage | Established Jarvis Protocol pattern |
| asyncio | stdlib | Async LLM calls, background diff analysis | Already used in generate_proposals() |
| json / JSONC stripping | stdlib + custom | Serialization and annotated draft import | TopologyGraph.to_dict/from_dict round-trip |
| jsonschema | 4.26.0+ | Validate LLM re-proposal output | Already in pyproject.toml dependencies |
| pytest | 7.0+ | Unit tests | Already in dev dependencies |
| unittest.mock | stdlib | Mock LLM calls in tests | Pattern in test_cli_propose.py and test_proposer.py |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| shutil | stdlib | Terminal width detection for rendering | render_matrix() already uses it |
| textwrap | stdlib | Word wrap in pushback notes and cycle-limit messages | render_justifications() uses it |
| subprocess / $EDITOR | stdlib | Open user's editor for hard correction draft | Only needed if interactive editor launch is wanted |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| In-memory session state | File-based session state | In-memory is simpler; file-based adds crash recovery but overkill for a short CLI session |
| Custom JSONC comment stripper | json5 library | json5 is not in dependencies; a 10-line regex strip is sufficient and adds no dependency |
| asyncio background task for diff | threading.Thread | asyncio is already used for LLM calls; mixing thread primitives is unnecessary |

**Installation:** No new packages required. All dependencies are stdlib or already in `pyproject.toml`.

---

## Architecture Patterns

### Recommended Project Structure

New files this phase creates:

```
packages/orchestration/src/openclaw/
├── cli/
│   ├── propose.py            # EXTEND: add session loop, approval prompt, export/import
│   └── approve.py            # NEW: `openclaw-approve` resume command
├── topology/
│   ├── correction.py         # NEW: CorrectionSession, soft/hard correction logic
│   ├── approval.py           # NEW: approve_topology(), approval gate check
│   └── storage.py            # EXTEND: save/load pending-proposals.json, proposal-draft.json
packages/orchestration/tests/
├── test_correction.py         # NEW: soft correction loop, cycle limit, re-proposal
├── test_approval.py           # NEW: approval gate, pending-proposals persistence
├── test_cli_approve.py        # NEW: openclaw-approve CLI
└── test_cli_propose.py        # EXTEND: session loop tests
skills/router/
└── index.js                  # EXTEND: approval gate check before L3 dispatch
```

### Pattern 1: CorrectionSession — In-Memory Session State

**What:** A dataclass that carries all mutable state for one interactive correction loop. Passed through the propose.py main loop by reference.

**When to use:** Every interactive propose session that stays alive past the initial proposal display.

```python
# packages/orchestration/src/openclaw/topology/correction.py
from dataclasses import dataclass, field
from typing import List, Optional
from openclaw.topology.proposal_models import ProposalSet, TopologyProposal

@dataclass
class CorrectionSession:
    """Mutable state for one interactive correction session."""
    outcome: str
    project_id: str
    proposal_set: ProposalSet          # Current proposals (updated each round)
    best_proposal_set: ProposalSet     # Best seen so far (for cycle-limit fallback)
    cycle_count: int = 0              # Incremented per soft correction round
    max_cycles: int = 3               # CORR-06: lock at 3
    approved_proposal: Optional[TopologyProposal] = None
    correction_history: List[dict] = field(default_factory=list)  # For changelog

    @property
    def cycle_limit_reached(self) -> bool:
        return self.cycle_count >= self.max_cycles
```

### Pattern 2: Soft Correction — Feedback-Injected Re-Proposal

**What:** User types feedback string; the session appends it to the next LLM prompt as explicit constraint context, then runs the full generate → lint → score → classify pipeline again.

**When to use:** After initial proposals display, when user types feedback text (not when user selects "edit directly").

```python
# In correction.py or propose.py interactive loop
SOFT_CORRECTION_SYSTEM_PROMPT_ADDENDUM = (
    "\nUser feedback on previous proposal: {feedback}\n"
    "Revise the proposals to address this feedback. "
    "Explain in each justification field what changed and why."
)

def apply_soft_correction(session: CorrectionSession, feedback: str) -> ProposalSet:
    """Re-run the proposal pipeline with feedback injected into the prompt."""
    # Increment cycle counter BEFORE generating — so we can check limit
    session.cycle_count += 1

    # Build augmented clarifications with feedback
    augmented = dict(session.clarifications)
    augmented["user_feedback"] = feedback

    # Re-run full pipeline (generate -> lint -> score)
    raw = generate_proposals_sync(
        outcome=session.outcome,
        project_id=session.project_id,
        registry=session.registry,
        max_concurrent=session.max_concurrent,
        clarifications=augmented,
    )
    # ... lint, score, classify as in original propose.py main()
```

**Re-proposal prompt engineering (Claude's discretion decision):** Inject feedback as a structured addendum after the outcome line in the user message. This keeps the system prompt stable (schema, constraints) and puts feedback in user-turn context where it naturally belongs in chat-based LLMs.

### Pattern 3: Hard Correction — Export-Edit-Import

**What:** Export selected proposal to `proposal-draft.json` as annotated JSONC, wait for user to confirm they've edited it, then import and validate.

**When to use:** When user selects "edit directly" or at cycle limit.

```python
# packages/orchestration/src/openclaw/topology/correction.py

DRAFT_FIELD_COMMENTS = {
    "nodes": "# Each node: id (string), level (1/2/3), intent (what role does), risk_level (low/medium/high)",
    "edges": "# Each edge: from_role (id), to_role (id), edge_type (delegation/coordination/review_gate/escalation/information_flow)",
}

def export_draft(proposal: TopologyProposal, project_id: str) -> Path:
    """Write annotated proposal-draft.json and return the path."""
    topo_dir = _topology_dir(project_id)
    draft_path = topo_dir / "proposal-draft.json"

    data = proposal.topology.to_dict()
    # Add field-level comments as __comment__ keys (stripped on import)
    data["__comment__nodes"] = DRAFT_FIELD_COMMENTS["nodes"]
    data["__comment__edges"] = DRAFT_FIELD_COMMENTS["edges"]

    with open(draft_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return draft_path


def import_draft(project_id: str, registry, max_concurrent: int) -> tuple:
    """Load, strip comments, validate, and return (TopologyGraph, LintResult)."""
    topo_dir = _topology_dir(project_id)
    draft_path = topo_dir / "proposal-draft.json"

    raw = json.loads(draft_path.read_text(encoding="utf-8"))
    # Strip __comment__ keys
    clean = {k: v for k, v in raw.items() if not k.startswith("__comment__")}
    graph = TopologyGraph.from_dict(clean)

    # Tiered validation: unknown roles = error, pool violation = warning
    linter = ConstraintLinter(registry, max_concurrent)
    proposal_dict = {"roles": [n.to_dict() for n in graph.nodes], "edges": [e.to_dict() for e in graph.edges]}
    lint_result = linter.lint("hard_correction", proposal_dict)

    return graph, lint_result
```

### Pattern 4: Approval Gate

**What:** `approve_topology()` function that atomically writes `current.json`, appends a diff changelog entry (with correction type and pushback annotation if relevant), and saves `pending-proposals.json` to signal approval.

**When to use:** After user explicitly selects an archetype to approve.

```python
# packages/orchestration/src/openclaw/topology/approval.py
import datetime
from openclaw.topology.storage import save_topology, load_topology, append_changelog
from openclaw.topology.diff import topology_diff

def approve_topology(
    project_id: str,
    approved_graph,
    proposed_graph,
    correction_type: str,  # "soft", "hard", or "initial"
    pushback_note: str = "",
) -> dict:
    """
    Persist the approved topology and write a changelog entry with diff.

    Returns the changelog entry dict (for the caller to display pushback note).
    """
    # Compute diff from previous approved topology (not proposed)
    previous = load_topology(project_id)
    diff = topology_diff(previous, approved_graph) if previous else None

    entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "correction_type": correction_type,
        "diff": diff.to_dict() if diff else None,
        "annotations": {
            "pushback_note": pushback_note,
        } if pushback_note else {},
    }

    # Atomic write: current.json first, then changelog
    save_topology(project_id, approved_graph)
    append_changelog(project_id, entry)

    return entry
```

### Pattern 5: High-Confidence Pushback

**What:** After approval, compare the approved topology's rubric score against the originally proposed topology's rubric score. If the system's proposed version had `overall_confidence >= pushback_threshold` AND any dimension dropped by >= 2 points, emit a non-blocking informational note.

**When to use:** After every approval where an original proposal existed with rubric scores.

```python
# packages/orchestration/src/openclaw/topology/approval.py
from openclaw.topology.rubric import score_proposal

def compute_pushback_note(
    original_score,  # RubricScore of what system proposed
    approved_graph,  # What user approved
    weights: dict,
    pushback_threshold: int = 8,
) -> str:
    """
    Returns a non-blocking informational note if system was confident and
    user's approved topology scores significantly lower on any dimension.

    Returns empty string if no pushback warranted.
    """
    if original_score.overall_confidence < pushback_threshold:
        return ""

    approved_score = score_proposal(approved_graph, weights)

    dimension_notes = []
    DIMENSION_LABELS = {
        "complexity": "Complexity",
        "coordination_overhead": "Coordination Overhead",
        "risk_containment": "Risk Containment",
        "time_to_first_output": "Time To First Output",
        "cost_estimate": "Cost Estimate",
    }

    for dim, label in DIMENSION_LABELS.items():
        orig_val = getattr(original_score, dim)
        new_val = getattr(approved_score, dim)
        if orig_val - new_val >= 2:  # Significant drop
            dimension_notes.append(f"{label}: {orig_val}/10 -> {new_val}/10")

    if not dimension_notes:
        return ""

    return (
        "Note: My original proposal scored higher on "
        + ", ".join(dimension_notes)
        + ". This is informational only."
    )
```

### Pattern 6: Pending-Proposals Persistence

**What:** On session exit (or after generating proposals), serialize the current ProposalSet to `topology/pending-proposals.json`. The `openclaw-approve` CLI command loads this file for resume.

**When to use:** Always after proposal generation, updated after each correction round.

```python
# In topology/storage.py (extend)
def save_pending_proposals(project_id: str, proposal_set_dict: dict) -> None:
    """Persist the current ProposalSet to pending-proposals.json."""
    topo_dir = _topology_dir(project_id)
    path = topo_dir / "pending-proposals.json"
    tmp = topo_dir / "pending-proposals.json.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            json.dump(proposal_set_dict, f, indent=2)
            f.flush()
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    tmp.rename(path)


def load_pending_proposals(project_id: str):
    """Load pending-proposals.json; returns None if not found."""
    topo_dir = _topology_dir(project_id)
    path = topo_dir / "pending-proposals.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_SH)
        try:
            return json.load(f)
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

### Pattern 7: L1 Router Approval Gate

**What:** In `skills/router/index.js`, before dispatching an L3 spawn directive, check that the project has an approved topology in `current.json`. If not, hold the directive and escalate.

**When to use:** Every L1 → L2 dispatch that involves spawning L3 containers.

```javascript
// skills/router/index.js — extend existing dispatch logic
const fs = require('fs');
const path = require('path');

function hasApprovedTopology(projectId, workspaceRoot) {
    const topoPath = path.join(
        workspaceRoot, 'workspace', '.openclaw', projectId, 'topology', 'current.json'
    );
    return fs.existsSync(topoPath);
}

// Before spawning L3:
if (!autoApproveL1 && !hasApprovedTopology(projectId, workspaceRoot)) {
    // Log directive as pending, surface to user via monitor
    throw new Error(`No approved topology for project ${projectId}. Run openclaw-propose to generate and approve a topology.`);
}
```

### Anti-Patterns to Avoid

- **Reading `current.json` with fs.readFileSync in Node without checking for existence:** Always check `fs.existsSync()` first — the file is absent on fresh projects.
- **Blocking execution on pushback note display:** The pushback note is printed before control returns. It must never be a prompt or await user confirmation.
- **Modifying proposal-draft.json in-place without a tmp rename:** All writes to topology/ files follow the `.tmp` + rename pattern from `storage.py`. Do not break this for proposal-draft.json writes.
- **Reusing the interactive `input()` loop inside `openclaw-approve`:** The approve command is a standalone CLI (not a session continuation); it loads pending-proposals.json and prompts once for archetype selection, then exits.
- **Writing JSONC comments as actual JSON5/JSONC syntax (/* */ or //):** Python's standard json module will fail to parse these on import. Use `__comment__` key prefixes (custom convention) that are stripped before `from_dict()`.
- **Running the full LLM pipeline synchronously on each soft correction cycle without checking cycle limit first:** The cycle limit check must happen BEFORE the LLM call so the user isn't charged for a request that won't be presented.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Topology serialization | Custom JSON serializer | `TopologyGraph.to_dict()` / `from_dict()` | Already handles all fields, edge types, null handling |
| Structural delta computation | Custom diff algorithm | `topology_diff()` from `topology/diff.py` | Handles node/edge match by id/endpoint, edge_type modification detection |
| Changelog persistence | Custom file writer | `append_changelog()` from `topology/storage.py` | fcntl-locked read-modify-write, atomic tmp+rename, handles missing file |
| Proposal scoring | Custom rubric scorer | `score_proposal()` from `topology/rubric.py` | 7-dimension weighted scoring; `find_key_differentiators()` computes spread |
| Terminal rendering | Custom table/DAG renderer | `render_full_output()` from `topology/renderer.py` | Width-adaptive (wide vs stacked), box-drawing characters, indented DAGs |
| Role validation | Custom registry check | `ConstraintLinter` from `topology/linter.py` | Handles unknown-role rejection AND pool-limit auto-adjust with review-gate cost model |
| Proposal generation | Custom LLM prompt | `generate_proposals_sync()` from `topology/proposer.py` | Handles rejection context, clarifications, jsonschema validation, markdown fence stripping |
| File locking | `threading.Lock` | `fcntl.flock(LOCK_EX)` | fcntl works across processes (Docker containers share volumes); threading.Lock does not |

**Key insight:** The topology subsystem is already complete infrastructure. Phase 63 is orchestration-level wiring, not new algorithms. Avoid duplicating any serialization, validation, or storage logic.

---

## Common Pitfalls

### Pitfall 1: Interactive Loop Blocking on Non-TTY

**What goes wrong:** The soft correction loop calls `input()` when stdin is not a TTY (e.g., piped input, test environment). This hangs indefinitely or raises EOFError.

**Why it happens:** The propose.py `_is_interactive()` check is only used for clarifications today. The new session loop adds another `input()` call for approval selection and feedback.

**How to avoid:** Gate every interactive `input()` call behind `_is_interactive()`. In non-interactive mode, default to no correction loop (just output proposals and return 0). Tests mock `_is_interactive` as `False` and test the main pipeline directly.

**Warning signs:** Tests timing out, `EOFError` in CI runs.

### Pitfall 2: Changelog Entry Serialization Fails on EdgeType Enum

**What goes wrong:** `topology_diff()` returns `TopologyDiff` with `modified_edges` entries containing `EdgeType` enum values. These are NOT JSON-serializable directly.

**Why it happens:** The `format_diff()` function correctly handles this for display, but when persisting to `changelog.json` via `append_changelog()`, if you pass `diff` dict directly without calling `diff.to_dict()`, the EdgeType enum breaks `json.dump()`.

**How to avoid:** Always call `diff.to_dict()` before passing to `append_changelog()`. The `to_dict()` method stores `edge_type.value` (the string), not the enum.

**Warning signs:** `TypeError: Object of type EdgeType is not JSON serializable` in append_changelog.

### Pitfall 3: Proposal-Draft Import Loses Edge Type

**What goes wrong:** User edits `proposal-draft.json` and changes an edge_type to a string that isn't in the EdgeType enum (e.g., "dependency" instead of "delegation"). `TopologyGraph.from_dict()` raises `ValueError`.

**Why it happens:** `TopologyEdge.from_dict()` calls `EdgeType(data["edge_type"])` with no fallback.

**How to avoid:** Wrap `from_dict()` in a try/except during import; surface a clear error message listing valid edge_type values. The constraint linter does NOT catch this — it's a deserialization failure, not a role constraint violation.

**Warning signs:** `ValueError: 'dependency' is not a valid EdgeType` at import time.

### Pitfall 4: Cycle Limit Message Doesn't Surface Best-So-Far

**What goes wrong:** At cycle limit, the system only says "limit reached" without showing the best proposal found across all rounds.

**Why it happens:** `best_proposal_set` on `CorrectionSession` is only updated if the new ProposalSet scores higher, but it might not be updated if scoring is skipped.

**How to avoid:** Always update `best_proposal_set` after each successful re-proposal round by comparing `overall_confidence` of the top proposal. At cycle limit, render `best_proposal_set`, not `current proposal_set`.

**Warning signs:** Cycle-limit message shown but no proposals displayed; user can't evaluate what was achieved.

### Pitfall 5: Approval Gate False-Positive on Fresh Projects

**What goes wrong:** L1 router blocks all directives on a fresh project that has never had a topology proposal, even for tasks that don't need topology approval (e.g., monitoring commands).

**Why it happens:** The approval gate check is applied unconditionally to all L1 directives.

**How to avoid:** The `topology.auto_approve_l1` config key (default: false) should be used as a project-level override. Additionally, the approval gate should only apply to L3-spawning directives, not administrative directives (status checks, logs). Check directive type in router before applying gate.

**Warning signs:** `openclaw-monitor` becomes non-functional after routing changes.

### Pitfall 6: JSONC Comment Strip Is Too Greedy

**What goes wrong:** Regex that strips "// comment" style lines from proposal-draft.json also strips legitimate string values that contain "//".

**Why it happens:** URL values (e.g., `"endpoint": "https://api.example.com/..."`) contain `//` and naive regex strips the line.

**How to avoid:** Use the `__comment__` key prefix convention instead of line-comment stripping. A `{k: v for k, v in raw.items() if not k.startswith("__comment__")}` dict comprehension is safe and cannot strip legitimate content.

**Warning signs:** Topology import silently loses node or edge data; `from_dict()` raises KeyError.

---

## Code Examples

Verified patterns from existing codebase:

### Re-Proposal with Feedback Context Injection

```python
# Source: topology/proposer.py (generate_proposals_sync pattern)
# Soft correction: inject feedback as additional clarification key
augmented_clarifications = {**original_clarifications, "user_feedback": feedback}

# In proposer.py generate_proposals(), the clarification_notes block becomes:
risk = clarifications.get("risk_tolerance", "medium")
timeline = clarifications.get("timeline_pressure", "moderate")
feedback = clarifications.get("user_feedback", "")

clarification_notes = f"\nContext: risk_tolerance={risk}, timeline_pressure={timeline}"
if feedback:
    clarification_notes += f"\nUser correction feedback: {feedback}\nAddress this feedback in revised proposals."
```

### Atomic Save of Pending Proposals

```python
# Source: topology/storage.py (save_topology pattern)
from pathlib import Path
import fcntl, json

def save_pending_proposals(project_id: str, data: dict) -> None:
    topo_dir = _topology_dir(project_id)
    path = topo_dir / "pending-proposals.json"
    tmp = topo_dir / "pending-proposals.json.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            json.dump(data, f, indent=2)
            f.flush()
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    tmp.rename(path)
```

### Approval with Diff Changelog Entry

```python
# Source: topology/storage.py append_changelog + diff.py topology_diff
from openclaw.topology.diff import topology_diff
from openclaw.topology.storage import save_topology, load_topology, append_changelog
import datetime

def approve_topology(project_id, approved_graph, correction_type, pushback_note=""):
    previous = load_topology(project_id)  # Returns None on first approval
    diff = topology_diff(previous, approved_graph) if previous else None

    entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "correction_type": correction_type,  # "initial", "soft", "hard"
        "diff": diff.to_dict() if diff else None,  # MUST call .to_dict() for JSON safety
        "annotations": {"pushback_note": pushback_note} if pushback_note else {},
    }

    save_topology(project_id, approved_graph)  # atomic write
    append_changelog(project_id, entry)        # fcntl-locked append
    return entry
```

### Hard Correction: JSONC Comment Convention

```python
# Source: topology/models.py (to_dict pattern)
# Export: add __comment__ keys (stripped on import)
def export_draft(proposal, project_id):
    data = proposal.topology.to_dict()
    data["__comment__nodes"] = (
        "Nodes: each has id (string), level (1/2/3), "
        "intent (what role does), risk_level (low/medium/high)"
    )
    data["__comment__edges"] = (
        "Edges: from_role/to_role (node ids), edge_type: "
        "delegation | coordination | review_gate | escalation | information_flow"
    )
    # ... write to proposal-draft.json

# Import: strip comment keys before from_dict()
def import_draft(project_id):
    raw = json.loads(draft_path.read_text())
    clean = {k: v for k, v in raw.items() if not k.startswith("__comment__")}
    return TopologyGraph.from_dict(clean)
```

### L1 Router Gate Check (Node.js)

```javascript
// Source: skills/router/index.js (execFileSync pattern from CLAUDE.md)
const fs = require('fs');
const path = require('path');

function checkApprovalGate(projectId, workspaceRoot, autoApproveL1) {
    if (autoApproveL1) return { approved: true };

    const topoPath = path.join(
        workspaceRoot, 'workspace', '.openclaw',
        projectId, 'topology', 'current.json'
    );

    if (!fs.existsSync(topoPath)) {
        return {
            approved: false,
            reason: `No approved topology for project '${projectId}'. ` +
                    `Run 'openclaw-propose' to generate and approve a topology.`
        };
    }
    return { approved: true };
}
```

### Config Schema Extension for New Keys

```python
# Source: packages/orchestration/src/openclaw/config.py (OPENCLAW_JSON_SCHEMA)
# Add to "topology" properties:
"auto_approve_l1": {
    "type": "boolean",
    "default": False,
},
"pushback_threshold": {
    "type": "number",
    "minimum": 0,
    "maximum": 10,
    "default": 8,
},
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fire-and-exit CLI proposal | Stateful interactive session loop | Phase 63 | propose.py grows a session class; exit saves state |
| proposals displayed, session ends | Proposals saved to pending-proposals.json | Phase 63 | `openclaw-approve` resume command becomes possible |
| No gate on L3 spawn | Approval gate in L1 router | Phase 63 | No L3 dispatch without current.json present |
| changelog entry has no correction_type | changelog entry typed as soft/hard/initial | Phase 63 | Phase 64 structural memory can filter by type |

**Deprecated/outdated:**
- The `propose.py` main() function's single-pass pattern: after Phase 63, the function may enter a loop. The existing pipeline (generate → lint → score → classify → render) remains intact as an inner function.

---

## Open Questions

1. **Should `openclaw-approve` (resume) also support adding new proposals or only choosing from the persisted set?**
   - What we know: decisions say "resume later with `openclaw approve` to pick up where they left off"
   - What's unclear: whether the resume command supports soft/hard corrections too, or is approval-only
   - Recommendation: Approval-only for Phase 63. Corrections require the full active session context (outcome, clarifications, registry). A resume that can correct would need to serialize the full CorrectionSession, adding scope; that's Phase 64 territory.

2. **How should the approval gate interact with existing autonomy config (`autonomy.confidence_threshold`)?**
   - What we know: `topology.auto_approve_l1` is the new key; `autonomy.confidence_threshold` is for the existing autonomous escalation system
   - What's unclear: Whether high-autonomy projects should bypass the topology gate
   - Recommendation: Keep them independent. `topology.auto_approve_l1` is topology-specific; autonomy config is for task confidence. A project can have high autonomy confidence AND still require topology approval.

3. **Should `openclaw-approve` delete `pending-proposals.json` after a successful approval?**
   - What we know: no decision made
   - What's unclear: whether a "pending" file that stays on disk after approval creates confusion
   - Recommendation: Yes, delete after approval. The approved topology is in `current.json`. `pending-proposals.json` being absent = nothing pending, consistent with the "pending" semantic.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 7.0+ |
| Config file | `packages/orchestration/pyproject.toml` (no pytest.ini; uses pyproject) |
| Quick run command | `uv run pytest packages/orchestration/tests/test_correction.py packages/orchestration/tests/test_approval.py -x` |
| Full suite command | `uv run pytest packages/orchestration/tests/ -v` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CORR-01 | Soft correction re-runs proposal pipeline with feedback | unit | `uv run pytest packages/orchestration/tests/test_correction.py::TestSoftCorrection -x` | Wave 0 |
| CORR-01 | Cycle count increments per soft correction round | unit | `uv run pytest packages/orchestration/tests/test_correction.py::TestCycleLimit -x` | Wave 0 |
| CORR-02 | Hard correction: export_draft writes valid JSONC | unit | `uv run pytest packages/orchestration/tests/test_correction.py::TestHardCorrection::test_export_draft -x` | Wave 0 |
| CORR-02 | Hard correction: import_draft strips comments and returns TopologyGraph | unit | `uv run pytest packages/orchestration/tests/test_correction.py::TestHardCorrection::test_import_draft -x` | Wave 0 |
| CORR-02 | Hard correction: unknown roles in draft block import with error | unit | `uv run pytest packages/orchestration/tests/test_correction.py::TestHardCorrection::test_import_unknown_role -x` | Wave 0 |
| CORR-03 | Approval writes diff entry to changelog with correction_type | unit | `uv run pytest packages/orchestration/tests/test_approval.py::TestApproveTopology::test_diff_recorded -x` | Wave 0 |
| CORR-04 | Hard correction: diff analysis does not block execution | unit | `uv run pytest packages/orchestration/tests/test_approval.py::TestApproveTopology::test_hard_correction_immediate -x` | Wave 0 |
| CORR-05 | Pushback note: returned as string, never raises | unit | `uv run pytest packages/orchestration/tests/test_approval.py::TestPushbackNote -x` | Wave 0 |
| CORR-05 | Pushback note: empty when original confidence below threshold | unit | `uv run pytest packages/orchestration/tests/test_approval.py::TestPushbackNote::test_no_pushback_low_confidence -x` | Wave 0 |
| CORR-06 | Cycle limit reached: best_proposal_set returned, not current | unit | `uv run pytest packages/orchestration/tests/test_correction.py::TestCycleLimit::test_best_fallback -x` | Wave 0 |
| CORR-07 | Approval gate: blocks when current.json absent | unit | `uv run pytest packages/orchestration/tests/test_approval.py::TestApprovalGate -x` | Wave 0 |
| CORR-07 | Approval gate: passes when current.json present | unit | `uv run pytest packages/orchestration/tests/test_approval.py::TestApprovalGate::test_gate_passes_with_topology -x` | Wave 0 |
| CORR-07 | Approval gate: bypassed when auto_approve_l1=true | unit | `uv run pytest packages/orchestration/tests/test_approval.py::TestApprovalGate::test_auto_approve_bypass -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest packages/orchestration/tests/test_correction.py packages/orchestration/tests/test_approval.py -x`
- **Per wave merge:** `uv run pytest packages/orchestration/tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `packages/orchestration/tests/test_correction.py` — covers CORR-01, CORR-02, CORR-06
- [ ] `packages/orchestration/tests/test_approval.py` — covers CORR-03, CORR-04, CORR-05, CORR-07
- [ ] `packages/orchestration/src/openclaw/topology/correction.py` — CorrectionSession, export_draft, import_draft, apply_soft_correction
- [ ] `packages/orchestration/src/openclaw/topology/approval.py` — approve_topology, compute_pushback_note, approval gate helpers

*(No framework install needed — pytest already in dev dependencies)*

---

## Sources

### Primary (HIGH confidence)

- Codebase inspection: `packages/orchestration/src/openclaw/topology/` — all modules read directly
- Codebase inspection: `packages/orchestration/src/openclaw/cli/propose.py` — existing session entry point
- Codebase inspection: `packages/orchestration/src/openclaw/topology/storage.py` — fcntl patterns, file layout
- Codebase inspection: `packages/orchestration/src/openclaw/topology/diff.py` — TopologyDiff structure, to_dict() serialization note
- Codebase inspection: `packages/orchestration/src/openclaw/topology/linter.py` — tiered validation pattern
- Codebase inspection: `packages/orchestration/src/openclaw/topology/rubric.py` — RubricScore, score_proposal, DIMENSIONS
- Codebase inspection: `packages/orchestration/src/openclaw/config.py` — OPENCLAW_JSON_SCHEMA topology section
- Codebase inspection: `packages/orchestration/tests/` — test patterns, mock strategies

### Secondary (MEDIUM confidence)

- CONTEXT.md: all locked decisions validated against existing code; no contradictions found
- REQUIREMENTS.md: CORR-01 through CORR-07 mapped to concrete implementation paths

### Tertiary (LOW confidence)

- None — all findings are grounded in code inspection, no speculative claims.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use; no new dependencies needed
- Architecture patterns: HIGH — all patterns derived from existing code; CorrectionSession pattern is additive
- Pitfalls: HIGH — all identified from direct code analysis (EdgeType serialization, JSONC stripping, TTY detection)

**Research date:** 2026-03-03
**Valid until:** 2026-06-03 (stable codebase; no fast-moving dependencies)
