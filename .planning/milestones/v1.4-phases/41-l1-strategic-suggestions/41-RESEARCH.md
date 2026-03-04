# Phase 41: L1 Strategic Suggestions - Research

**Researched:** 2026-02-24
**Domain:** Pattern extraction from task activity logs, SOUL amendment generation, approval gate UI
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Suggestion card design**
- Primary card display: pattern description + evidence count (e.g. "Agents frequently ignore user-specified file paths (7 occurrences)")
- Expanded suggestion view uses a unified diff format showing exactly what would be appended/changed in soul-override.md
- Evidence shown: count + 2–3 example task excerpts (task ID + short rejection reason) — enough context without overwhelming
- Suggestions ordered by evidence count descending — highest-frequency patterns surface first

**Approval flow**
- On accept: inline confirmation on the card ("Applied to soul-override.md") + updated SOUL content visible on the same page immediately
- On reject: optional text field appears (not required) — operator can dismiss with one click or add context; reason is memorized if provided
- Rejected suggestions move to a Dismissed tab/archive — not permanently deleted, visible if operator wants to review
- Accept-as-is only — no inline editing of the diff before accepting; operator edits soul-override.md directly if they want different wording

**Trigger and cadence**
- Pattern extraction is on-demand: a "Run analysis" button on the Suggestions dashboard page
- Also triggerable via CLI: `python3 orchestration/suggest.py --project X` so L1 can initiate analysis programmatically
- New pending suggestions surface via a badge on the Suggestions nav item (count visible without navigating)
- If a run finds no patterns meeting the threshold: show a clear empty state — "Last run: [timestamp]. No patterns met the threshold." — confirms the engine ran

**Lookback window and thresholds**
- Default lookback window: last 30 days of task history
- Configurable per project via `suggestion_lookback_days` in `l3_overrides` in project.json
- Pattern engine analyzes per-task activity log entries in workspace-state.json (already captured by Jarvis Protocol)
- Rejection suppression: if a pattern was rejected, do not re-surface it unless significantly more new evidence accumulates (target: ~2× the original threshold before re-suggesting)
- Minimum threshold for generating a suggestion: ≥3 similar rejections within the lookback window (fixed per requirements)

### Claude's Discretion
- Exact similarity algorithm for clustering similar failure patterns
- Specific wording of the pattern description generated from clusters
- How "similar rejections" are detected (embedding similarity, keyword frequency, or hybrid)
- Dismissed tab placement and visual treatment within the Suggestions page layout
- Exact threshold multiplier for re-surfacing rejected patterns (the "~2×" is a target, not a hard rule)

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ADV-01 | Pattern extraction engine queries memU for rejection clusters and identifies recurring failure patterns via frequency counting (threshold: ≥3 similar rejections within lookback window) | `orchestration/suggest.py` module using `MemoryClient.retrieve()` with rejection-specific queries; frequency counting via keyword grouping (see Architecture Patterns) |
| ADV-02 | Suggestion generator produces concrete diff-style SOUL amendments with pattern description, evidence count, and exact text to add to soul-override.md | `soul_renderer.py` shows how soul-override.md is a section-level markdown file; diff format is append-or-replace of a `## PATTERN NOTES` section |
| ADV-03 | Pending suggestions stored in `workspace/.openclaw/<project_id>/soul-suggestions.json` | Path mirrors existing `workspace/.openclaw/<project_id>/workspace-state.json` pattern; JSON file with suggestions array + metadata |
| ADV-04 | L2 acceptance flow reads pending suggestions and accepts (appends to soul-override.md, re-renders SOUL) or rejects (memorizes rejection reason) | `write_soul()` in `soul_renderer.py` handles re-render; `MemoryClient.memorize()` handles rejection reason storage |
| ADV-05 | Dashboard surfaces pending SOUL suggestions with accept/reject actions for operator review | New `/suggestions` page in occc, new nav item in Sidebar.tsx with badge count, new API routes at `/api/suggestions/` |
| ADV-06 | Auto-apply of suggestions without human approval is structurally prevented (mandatory approval gate) | API route validates payload before writing; `soul-suggestions.json` is read-only from pattern engine's perspective; write path only via accept endpoint |
</phase_requirements>

---

## Summary

Phase 41 adds L1 strategic intelligence: the system watches for recurring task failures and proposes targeted SOUL amendments. The feature has three distinct layers — (1) the pattern extraction engine (`orchestration/suggest.py`) that reads task activity logs and memU rejection memories, (2) the suggestion store (`soul-suggestions.json`) as a durable pending queue, and (3) the dashboard approval UI that gives an operator the final say before any SOUL file is modified.

The critical architectural constraint is the approval gate: the pattern engine must never write to `soul-override.md` directly. Instead, it writes only to `soul-suggestions.json`. The accept API endpoint is the sole write path to `soul-override.md`, and it must validate the payload before writing. This structural separation is the core of ADV-06 and is what prevents prompt injection via suggested amendments.

The project's existing stack handles almost everything needed. `MemoryClient.retrieve()` provides access to past rejection memories. `soul_renderer.py` already implements section-level merging and `write_soul()` for re-rendering. The dashboard pattern from Phase 40 (HealthTab, ConflictPanel, the run-button + timestamp empty-state) is a direct template for the Suggestions page.

**Primary recommendation:** Build the approval gate (API route with validation) first, then the pattern engine, then the UI — in that order, per the STATE.md instruction "Build approval gate before suggestion pipeline."

---

## Standard Stack

### Core (existing — no new installs required)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python 3 stdlib (`json`, `re`, `collections`, `pathlib`) | 3.x | Pattern extraction engine | No external deps; keeps `suggest.py` importable in test env like `scan_engine.py` |
| `orchestration.memory_client.MemoryClient` | project | Query memU for past rejection memories | Already scoped per-project; `retrieve()` returns list of dicts |
| `orchestration.soul_renderer.render_soul`, `write_soul` | project | Re-render SOUL.md after accept | Existing section-merge logic handles append correctly |
| `orchestration.project_config.get_state_path`, `_find_project_root` | project | Resolve `soul-suggestions.json` path | Consistent with state file path resolution |
| Next.js 16 App Router (Server Actions / Route Handlers) | 16 | Dashboard API routes and page | Existing occc stack |
| React 19 + Tailwind CSS | 19 / v4 | Suggestions page UI | Existing component stack |
| `react-toastify` | existing | Accept/reject feedback toasts | Already wired in layout.tsx |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `asyncio` | stdlib | `suggest.py` CLI uses async for `MemoryClient` | Already the pattern in pool.py and memory_client.py |
| `collections.Counter` | stdlib | Frequency counting for keyword-based clustering | Use when embedding-based clustering isn't available |
| `difflib.unified_diff` | stdlib | Generating unified diff text for proposals | Use for formatting the `diff_text` field in suggestions |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Keyword frequency clustering | Embedding similarity (cosine) | Embeddings require live memU with numpy; keyword frequency works with plain text and stdlib — use as primary with embedding as optional enhancement |
| Appending to soul-override.md | Full section replacement | Append is safer and simpler; section replacement risks destroying existing overrides |
| Separate `suggest.py` CLI | Baking extraction into a new FastAPI endpoint | CLI matches existing pattern (`soul_renderer.py`, `project_cli.py`); keeps the extraction testable without Next.js |

**Installation:** No new packages required. The entire stack uses existing dependencies.

---

## Architecture Patterns

### Recommended File Structure

```
orchestration/
└── suggest.py                  # Pattern extraction engine + CLI entry point

workspace/.openclaw/<project_id>/
└── soul-suggestions.json       # Pending suggestion queue (written by suggest.py)

projects/<project_id>/
└── soul-override.md            # ONLY modified by accept endpoint (never by suggest.py)

workspace/occc/src/
├── app/
│   ├── suggestions/
│   │   └── page.tsx            # Suggestions dashboard page
│   └── api/
│       └── suggestions/
│           ├── route.ts         # GET (list) + POST (run analysis)
│           └── [id]/
│               └── action/
│                   └── route.ts # POST action: accept | reject
├── components/
│   └── suggestions/
│       ├── SuggestionsPanel.tsx    # Top-level panel (tab host)
│       ├── SuggestionCard.tsx      # Single suggestion card
│       └── DismissedTab.tsx        # Dismissed archive view
└── lib/
    └── types/
        └── suggestions.ts          # Shared TypeScript interfaces
```

### Pattern 1: Suggestion Store Schema (`soul-suggestions.json`)

**What:** JSON file holding pending and dismissed suggestions with full audit trail.
**When to use:** Both the Python extraction engine and the Next.js API routes read/write this file.

```python
# orchestration/suggest.py — write pattern
import json, time
from pathlib import Path

SUGGESTION_SCHEMA = {
    "version": "1.0",
    "last_run": None,          # ISO timestamp of last extraction run
    "suggestions": [
        {
            "id": "sug-<uuid4-short>",
            "status": "pending",          # pending | accepted | rejected
            "created_at": 1708800000.0,   # Unix timestamp
            "pattern_description": "...", # Human-readable pattern summary
            "evidence_count": 7,          # Number of matching rejections
            "evidence_examples": [        # Up to 3 task excerpts
                {"task_id": "T-001", "excerpt": "Agent ignored file path..."}
            ],
            "diff_text": "## BEHAVIORAL PROTOCOLS\n- ...",  # Exact text to append
            "rejected_at": None,          # Unix timestamp if rejected
            "rejection_reason": None,     # String if operator provided one
            "accepted_at": None,
        }
    ]
}

def _suggestions_path(project_id: str) -> Path:
    """Path: workspace/.openclaw/<project_id>/soul-suggestions.json"""
    from orchestration.project_config import _find_project_root
    root = _find_project_root()
    return root / "workspace" / ".openclaw" / project_id / "soul-suggestions.json"
```

### Pattern 2: Pattern Extraction Engine (`orchestration/suggest.py`)

**What:** Queries memU for past task rejection memories, clusters by keyword frequency, generates suggestions when cluster size >= threshold.
**When to use:** Run on-demand via CLI or triggered by dashboard "Run analysis" button.

```python
# orchestration/suggest.py — extraction flow

import asyncio
import re
from collections import defaultdict, Counter
from typing import List, Dict

REJECTION_QUERY = "task failed rejected error agent mistake"
MIN_CLUSTER_SIZE = 3  # ADV-01 requirement

def _extract_keywords(text: str) -> List[str]:
    """Normalize and extract meaningful keywords from a rejection memory entry."""
    text = text.lower()
    # Strip boilerplate; extract noun phrases / action patterns
    stopwords = {"the", "a", "an", "to", "in", "of", "and", "or", "was", "is"}
    words = re.findall(r"[a-z][a-z_-]+", text)
    return [w for w in words if len(w) > 3 and w not in stopwords]

def _cluster_memories(memories: List[dict], lookback_days: int) -> Dict[str, List[dict]]:
    """
    Cluster rejection memories by dominant keyword.
    Returns {keyword: [memory, ...]} for clusters with >= MIN_CLUSTER_SIZE items.
    """
    import time
    cutoff = time.time() - (lookback_days * 86400)
    recent = [
        m for m in memories
        if (m.get("created_at") or m.get("timestamp", 0)) >= cutoff
    ]

    keyword_to_memories: Dict[str, List[dict]] = defaultdict(list)
    for mem in recent:
        content = mem.get("content", mem.get("resource_url", ""))
        for kw in _extract_keywords(content):
            keyword_to_memories[kw].append(mem)

    # Keep only clusters meeting threshold
    return {
        kw: mems
        for kw, mems in keyword_to_memories.items()
        if len(mems) >= MIN_CLUSTER_SIZE
    }

async def run_extraction(project_id: str, memu_url: str, lookback_days: int = 30) -> List[dict]:
    """Full extraction pipeline — returns list of new suggestion dicts."""
    from orchestration.memory_client import MemoryClient, AgentType

    async with MemoryClient(memu_url, project_id, AgentType.L2_PM) as client:
        memories = await client.retrieve(REJECTION_QUERY)

    clusters = _cluster_memories(memories, lookback_days)
    suggestions = []
    for keyword, mems in clusters.items():
        suggestion = _build_suggestion(keyword, mems)
        suggestions.append(suggestion)
    return suggestions
```

### Pattern 3: Approval Gate — API Route Validation (ADV-06)

**What:** The accept endpoint validates the `diff_text` payload before writing to `soul-override.md`.
**When to use:** Every accept action goes through this gate — no bypass.

```typescript
// workspace/occc/src/app/api/suggestions/[id]/action/route.ts
import { NextRequest } from 'next/server';
import fs from 'fs/promises';
import path from 'path';

const OPENCLAW_ROOT = process.env.OPENCLAW_ROOT || '~/.openclaw';
const MAX_DIFF_LINES = 100;  // ADV-06 constraint
const FORBIDDEN_PATTERNS = [
  /cap_drop/i,
  /no-new-privileges/i,
  /LOCK_TIMEOUT/i,
  /shell=/i,
  /exec\s*\(/i,
  /subprocess/i,
  /os\.system/i,
  /`[^`]+`/,         // backtick shell commands
  /\$\([^)]+\)/,     // shell substitution
];

function validateDiffText(diffText: string): { valid: boolean; reason?: string } {
  const lines = diffText.split('\n');
  if (lines.length > MAX_DIFF_LINES) {
    return { valid: false, reason: `Diff exceeds ${MAX_DIFF_LINES} lines (got ${lines.length})` };
  }
  for (const pattern of FORBIDDEN_PATTERNS) {
    if (pattern.test(diffText)) {
      return { valid: false, reason: `Diff contains forbidden pattern: ${pattern}` };
    }
  }
  return { valid: true };
}

export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const body = await request.json();
  const { action, rejection_reason, project } = body;

  if (action === 'accept') {
    const { diff_text } = body;
    const validation = validateDiffText(diff_text);
    if (!validation.valid) {
      return Response.json({ error: validation.reason }, { status: 422 });
    }
    // Only after validation: append to soul-override.md
    const overridePath = path.join(OPENCLAW_ROOT, 'projects', project, 'soul-override.md');
    await fs.appendFile(overridePath, '\n\n' + diff_text.trim(), 'utf-8');
    // Then re-render SOUL via Python CLI (subprocess call or direct file manipulation)
    // ...
  }
  // reject path: update soul-suggestions.json status + memorize reason
}
```

### Pattern 4: Suggestions Page Badge Count

**What:** The Sidebar nav item shows a pending count badge, polling the suggestions API.
**When to use:** Layout-level; renders regardless of which page is active.

```typescript
// In Sidebar.tsx — add badge to Suggestions nav item
// Fetch pending count from /api/suggestions?project=<id>&status=pending
// Display as red badge pill overlaid on the icon
// Pattern: same as notification badges in other dashboard contexts
// Poll interval: 30s (low priority background refresh)
```

### Pattern 5: Re-rendering SOUL After Accept

**What:** After appending to soul-override.md, the accept endpoint must re-render SOUL.md for the project's L2 agent.
**When to use:** Every accept action triggers this.

The cleanest approach given Next.js server-side constraints:
- **Option A (recommended):** Python subprocess from the API route: `python3 orchestration/soul_renderer.py --project <id> --write --force`
- **Option B:** Direct file manipulation in Node.js — replicate the merge logic. Avoid this; duplicates Python logic.

Use Option A. The API route spawns a subprocess call to `soul_renderer.py --write --force`. This keeps the SOUL rendering logic in a single authoritative Python module.

```typescript
import { execFile } from 'child_process';
import { promisify } from 'util';
const execFileAsync = promisify(execFile);

async function rerenderSoul(projectId: string): Promise<void> {
  await execFileAsync('python3', [
    path.join(OPENCLAW_ROOT, 'orchestration', 'soul_renderer.py'),
    '--project', projectId,
    '--write',
    '--force',
  ]);
}
```

### Anti-Patterns to Avoid

- **Pattern engine writes to soul-override.md directly:** The engine writes ONLY to `soul-suggestions.json`. The accept API is the sole writer of `soul-override.md`.
- **Embedding-based clustering without fallback:** memU retrieval returns plain text dicts, not pre-computed embeddings. Don't assume `.embedding` exists on retrieved items — use keyword frequency as primary clustering.
- **Global soul-suggestions.json:** The file lives at `workspace/.openclaw/<project_id>/soul-suggestions.json`, scoped per-project exactly like `workspace-state.json`. Never write a root-level file.
- **Inline diff editing in UI:** The CONTEXT.md locks "accept-as-is only". Do not add a textarea for editing the diff before accepting.
- **Re-surfacing rejected patterns immediately:** Track rejected suggestion pattern fingerprints in `soul-suggestions.json` and suppress re-generation until evidence count approximately doubles.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SOUL section merge | Custom string concatenation logic | `soul_renderer.render_soul()` + `parse_sections()` + `merge_sections()` | Already handles section ordering, whitespace normalization, template substitution |
| Soul-override.md path resolution | Hardcoded paths | `_find_project_root() / "projects" / project_id / "soul-override.md"` | Consistent with existing resolver; works with `OPENCLAW_ROOT` env var |
| State file path | Manual construction | `get_state_path(project_id)` from `orchestration.project_config` | Raises `ProjectNotFoundError` on missing manifest — correct guard |
| Memory retrieval | Direct HTTP to memU | `MemoryClient.retrieve()` | Handles timeout (3s), error degradation (returns `[]`), project scoping |
| Rejection memory storage | Custom DB | `MemoryClient.memorize()` with category hint | Already wired; graceful degradation on failure |
| Subprocess call safety | Shell string interpolation | `execFile` with argument arrays (not `exec`) | Prevents injection — same pattern as `router_skill/index.js` uses `execFileSync` with arrays |

**Key insight:** The extraction engine is pure computation; delegate all I/O to existing modules. `suggest.py` should import from `orchestration.*` rather than implementing its own file handling.

---

## Common Pitfalls

### Pitfall 1: Pattern Engine Writes soul-override.md Directly
**What goes wrong:** Developer places the append logic inside `suggest.py` for convenience. An auto-run trigger (L1 scheduler) silently modifies SOUL without operator review. This is the primary security failure mode.
**Why it happens:** It's simpler to write in one place. The separation feels artificial during development.
**How to avoid:** `suggest.py` has no knowledge of `soul-override.md`. It only writes to `soul-suggestions.json`. The accept API route is the only code path that touches `soul-override.md`.
**Warning signs:** If `suggest.py` imports `soul_renderer` write functions, stop and refactor.

### Pitfall 2: Clustering Returns Too Many Low-Quality Suggestions
**What goes wrong:** Keyword frequency clustering is too coarse — common words like "failed" or "error" form huge clusters that produce generic, unhelpful suggestions ("Agents sometimes fail").
**Why it happens:** Stopword list is too small; minimum keyword length threshold is too low.
**How to avoid:** Use 4+ character minimum for keywords. Add domain-specific stopwords (`task`, `agent`, `error`, `failed`, `status`, `completed`). Weight by TF-IDF-style inverse frequency (common-across-all-clusters terms get downweighted). If a cluster spans >50% of all rejection memories, discard it as too generic.
**Warning signs:** Suggestions with evidence_count approaching total task count.

### Pitfall 3: Rejection Suppression Not Implemented
**What goes wrong:** Operator rejects a suggestion; next extraction run re-generates the same suggestion immediately. Operator sees it again, gets frustrated, dismisses it again.
**Why it happens:** Suppression logic is planned but not coded before the extraction loop runs.
**How to avoid:** Before creating a new suggestion, check existing `soul-suggestions.json` for rejected entries with the same pattern fingerprint. Re-surface only when new evidence count ≥ 2× the original evidence count at rejection time. Store `suppressed_until_count` on rejected entries.
**Warning signs:** Dismissed tab fills up with identical entries.

### Pitfall 4: Validation Bypass via Missing Fields
**What goes wrong:** Accept endpoint receives a payload missing `diff_text` or with `diff_text: null`. Validation passes (no lines to check), `soul-override.md` gets `null` appended.
**Why it happens:** Validation only checks content of `diff_text`, not its presence/type.
**How to avoid:** Validate that `diff_text` is a non-empty string before content validation. Return 422 on missing or empty `diff_text`.
**Warning signs:** `soul-override.md` contains `null` or `undefined` text.

### Pitfall 5: soul-override.md Path for Projects Without Override File
**What goes wrong:** Accept endpoint tries to append to a file that doesn't exist yet. `fs.appendFile` creates it — but if the path directory doesn't exist, it throws.
**Why it happens:** Some projects have no `soul-override.md` (it's optional per `soul_renderer.py` design).
**How to avoid:** `fs.mkdir(path.dirname(overridePath), { recursive: true })` before `fs.appendFile`. This is safe even when the directory already exists.
**Warning signs:** ENOENT error on first accept for a project with no existing soul-override.md.

### Pitfall 6: Badge Count Stale After Accept/Reject
**What goes wrong:** Operator accepts a suggestion. Badge still shows old count. Navigates away and back — count updates. Confusing.
**Why it happens:** SWR cache not invalidated after mutation.
**How to avoid:** After accept/reject API call succeeds, trigger SWR `mutate()` on the suggestions list key to force immediate refresh of badge count.
**Warning signs:** Badge count doesn't decrement immediately after action.

---

## Code Examples

### soul-suggestions.json Schema (full example)

```json
{
  "version": "1.0",
  "last_run": "2026-02-24T10:30:00+00:00",
  "suggestions": [
    {
      "id": "sug-a1b2c3",
      "status": "pending",
      "created_at": 1708770600.0,
      "pattern_description": "Agents frequently ignore user-specified file paths (7 occurrences)",
      "evidence_count": 7,
      "evidence_examples": [
        {"task_id": "T-042", "excerpt": "Ignored --output-path flag, wrote to default location"},
        {"task_id": "T-051", "excerpt": "Created files in /tmp instead of specified workspace"},
        {"task_id": "T-063", "excerpt": "Used hardcoded path instead of $WORKSPACE variable"}
      ],
      "diff_text": "## BEHAVIORAL PROTOCOLS\n- **Path Discipline:** Always use the path provided in the task directive. Never substitute hardcoded paths or defaults.\n",
      "rejected_at": null,
      "rejection_reason": null,
      "suppressed_until_count": null,
      "accepted_at": null
    },
    {
      "id": "sug-d4e5f6",
      "status": "rejected",
      "created_at": 1708684200.0,
      "pattern_description": "Agents skip test runs before committing (4 occurrences)",
      "evidence_count": 4,
      "evidence_examples": [
        {"task_id": "T-038", "excerpt": "Committed without running test suite"}
      ],
      "diff_text": "## BEHAVIORAL PROTOCOLS\n- **Test Gate:** Run tests before every commit.\n",
      "rejected_at": 1708770000.0,
      "rejection_reason": "Already covered by entrypoint.sh — not needed in SOUL",
      "suppressed_until_count": 8,
      "accepted_at": null
    }
  ]
}
```

### suggest.py CLI Entry Point Pattern

```python
# orchestration/suggest.py — main block pattern
# Source: mirrors project_cli.py and soul_renderer.py CLI patterns

if __name__ == "__main__":
    import argparse, asyncio, json, sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from orchestration.project_config import get_active_project_id, get_memu_config

    parser = argparse.ArgumentParser(description="Generate SOUL amendment suggestions")
    parser.add_argument("--project", help="Project ID (default: active project)")
    parser.add_argument("--dry-run", action="store_true", help="Print suggestions without saving")
    args = parser.parse_args()

    project_id = args.project or get_active_project_id()
    memu_cfg = get_memu_config()
    memu_url = memu_cfg.get("memu_api_url", "")

    if not memu_url:
        print("ERROR: memu_api_url not configured in openclaw.json", file=sys.stderr)
        sys.exit(1)

    suggestions = asyncio.run(run_extraction(project_id, memu_url))
    if args.dry_run:
        print(json.dumps(suggestions, indent=2))
    else:
        _save_suggestions(project_id, suggestions)
        print(f"Saved {len(suggestions)} suggestion(s) to soul-suggestions.json")
```

### Dashboard API — GET Suggestions Route Pattern

```typescript
// workspace/occc/src/app/api/suggestions/route.ts
// Source: mirrors /api/memory/route.ts pattern

import { NextRequest } from 'next/server';
import fs from 'fs/promises';
import path from 'path';

const OPENCLAW_ROOT = process.env.OPENCLAW_ROOT || '~/.openclaw';

function suggestionsPath(projectId: string): string {
  return path.join(OPENCLAW_ROOT, 'workspace', '.openclaw', projectId, 'soul-suggestions.json');
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const projectId = searchParams.get('project');
  if (!projectId) {
    return Response.json({ error: 'project required' }, { status: 400 });
  }
  try {
    const raw = await fs.readFile(suggestionsPath(projectId), 'utf-8');
    const data = JSON.parse(raw);
    return Response.json(data);
  } catch {
    // File doesn't exist yet — return empty state
    return Response.json({ version: '1.0', last_run: null, suggestions: [] });
  }
}
```

### Sidebar Badge Pattern

```typescript
// In Sidebar.tsx — suggestions nav item with badge
// Source: project pattern from memory page; badge pattern is standard Tailwind

{
  href: '/suggestions',
  label: 'Suggestions',
  badge: pendingCount > 0 ? pendingCount : undefined,
  icon: (/* brain/lightbulb SVG */),
}

// In nav render:
<Link href={item.href} className={...}>
  <div className="relative">
    {item.icon}
    {item.badge !== undefined && (
      <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
        {item.badge > 9 ? '9+' : item.badge}
      </span>
    )}
  </div>
  {item.label}
</Link>
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual SOUL editing by developer | Section-level override file (`soul-override.md`) merged at render time | Phase 28 (v1.3) | Enables targeted amendments without replacing the entire default template |
| L3 containers silently fail | Activity logs in workspace-state.json via Jarvis Protocol | Phase 1 (v1.0) | All task outcomes persisted — available as corpus for pattern extraction |
| No memory of failures | memU integration with per-project scoping | Phase 26 (v1.3) | Rejection memories available for semantic retrieval |

---

## Open Questions

1. **memU retrieval corpus quality for rejection patterns**
   - What we know: `MemoryClient.retrieve()` does semantic search against all memories for the project. Rejection memories are only present if L2 or L3 explicitly memorized rejection reasons during task review.
   - What's unclear: Current projects may have sparse rejection memory corpus (STATE.md notes "Rejection corpus may be too small for ≥3-cluster threshold at current project scale"). The activity_log in workspace-state.json is a complementary source.
   - Recommendation: Query BOTH memU (semantic search for "task rejected failed") AND workspace-state.json activity logs (scan all `failed`/`interrupted` status entries). Use activity log as primary corpus; memU as supplementary. This makes the engine work even when memU is empty.

2. **Keyword vs. embedding clustering**
   - What we know: Claude's Discretion allows any similarity algorithm. Embeddings require live memU + numpy at extraction time. Activity log entries are plain text strings.
   - What's unclear: Whether activity log entries contain enough natural language to cluster semantically vs. structurally (e.g., "SIGTERM received" is structural, not semantic).
   - Recommendation: Use keyword frequency as primary, with a commented placeholder for embedding enhancement. This matches the `scan_engine.py` pattern of lazy imports for optional deps.

3. **soul-override.md append vs. section upsert**
   - What we know: `soul_renderer.py`'s `merge_sections()` does section-level replacement — if a section in soul-override.md matches a section in soul-default.md by name, it replaces it. Appending is simpler but may create duplicate sections.
   - What's unclear: Whether suggestions should target specific existing sections (e.g., `## BEHAVIORAL PROTOCOLS`) or create new named sections.
   - Recommendation: Suggestions target `## BEHAVIORAL PROTOCOLS` or a new `## PATTERN GUIDANCE` section. The diff_text must start with `## <section name>` so the renderer merges it cleanly. Document this constraint in suggestion generation.

---

## Sources

### Primary (HIGH confidence)
- `~/.openclaw/orchestration/soul_renderer.py` — `render_soul()`, `write_soul()`, `parse_sections()`, `merge_sections()` — authoritative SOUL rendering logic
- `~/.openclaw/orchestration/memory_client.py` — `MemoryClient.retrieve()`, `memorize()` API contract
- `~/.openclaw/orchestration/project_config.py` — `get_state_path()`, `_find_project_root()`, `get_memu_config()`, `_POOL_CONFIG_DEFAULTS` pattern
- `~/.openclaw/orchestration/state_engine.py` — activity log schema: `{timestamp, status, entry}` per task
- `~/.openclaw/docker/memory/memory_service/scan_engine.py` — pure-stdlib module pattern for testable extraction logic
- `~/.openclaw/workspace/occc/src/app/api/memory/[id]/route.ts` — PUT validation + proxy pattern
- `~/.openclaw/workspace/occc/src/app/api/memory/health-scan/route.ts` — run-button API route pattern
- `~/.openclaw/workspace/occc/src/components/layout/Sidebar.tsx` — nav item structure; badge requires extending current `navItems` array
- `~/.openclaw/workspace/occc/src/lib/openclaw.ts` — `OPENCLAW_ROOT` env var, `readOpenClawConfig()`, per-project state path construction
- `~/.openclaw/.planning/phases/41-l1-strategic-suggestions/41-CONTEXT.md` — locked decisions and discretion areas
- `~/.openclaw/.planning/REQUIREMENTS.md` — ADV-01 through ADV-06 definitions
- `~/.openclaw/.planning/STATE.md` — "Build approval gate before suggestion pipeline" directive; Phase 41 Blocker note about sparse rejection corpus

### Secondary (MEDIUM confidence)
- `skills/router_skill/index.js` — `execFileSync` with array args pattern (referenced for subprocess injection prevention in API route)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all required modules already exist; verified by direct file inspection
- Architecture: HIGH — patterns derived directly from existing Phase 40 code (scan_engine, health-scan route, HealthTab); no novel infrastructure needed
- Pitfalls: HIGH for structural pitfalls (approval gate, path creation); MEDIUM for tuning pitfalls (clustering quality, suppression threshold)

**Research date:** 2026-02-24
**Valid until:** 2026-03-25 (stable — all dependencies are internal project code, no external library churn)
