# Phase 29: Pre-Spawn Retrieval + SOUL Injection - Research

**Researched:** 2026-02-24
**Domain:** Python tempfile, async/sync retrieval, string.Template substitution, Docker volume injection
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Retrieval query strategy**
- Retrieval scoped to current project only (project_id filter) — no cross-project memories
- Query composition (task description, skill hint, combination): Claude's discretion
- Number of results to fetch: Claude's discretion (balance with 2,000-char budget)
- Relevance threshold (cutoff vs inject all): Claude's discretion

**Memory section formatting**
- Bullet list format under a `## Memory Context` section header
- Each bullet includes a short source tag, e.g., `(from L2 review)` or `(memorized 2d ago)`
- When no memories are retrieved, the section is hidden entirely — no header, no placeholder, blank render
- Matches success criterion 4: `$memory_context` renders as blank when empty

**Spawn-time rendering flow**
- Memory retrieval and injection happens in `spawn.py` before container creation — `soul_renderer.py` stays unchanged
- spawn.py calls memU `/retrieve`, formats the memory bullets, then writes a memory-augmented SOUL to a temp file
- Temp file mounted read-only into the L3 container; L3 entrypoint reads it at a known path
- Sync vs async retrieval timing: Claude's discretion (must degrade gracefully per RET-04)
- Logging: log count + total char count on injection, e.g., "Injected 4 memories (1,847 chars) into SOUL"

**Budget allocation**
- Pure relevance-ranked ordering from memU — no type-based priority or reserved slots
- Hard budget: 2,000 characters, hardcoded as a constant (not configurable per project)
- Budget scope (whether header/markup counts against limit): Claude's discretion
- Trimming strategy (drop lowest-ranked vs truncate long items): Claude's discretion
- Memory Context section placed at the end of the SOUL, after all existing sections

### Claude's Discretion
- Query composition details (what fields to send to memU /retrieve)
- Number of results to request from memU
- Relevance score threshold (if any)
- Sync with timeout vs async retrieval approach
- Budget accounting (total rendered vs content only)
- Trimming strategy when exceeding budget

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| RET-01 | Pre-spawn context retrieval calls memU retrieve (RAG mode) before L3 container creation | `MemoryClient.retrieve()` already exists with scoping, 3s timeout, and sentinel degradation (`[]` on failure). Call site is `spawn_l3_specialist()` in `spawn.py` before `client.containers.run()`. |
| RET-02 | Retrieved memories are injected into SOUL template via soul_renderer.py with a memory context section | Decision overrides this: injection happens in `spawn.py`, NOT by modifying `soul_renderer.py`. The augmented SOUL is written to a tempfile, mounted read-only into the container at `/orchestration/SOUL.md` or a dedicated path. The `$memory_context` variable is substituted in the rendered SOUL before writing. |
| RET-03 | Retrieved memory injection has a hard 2,000-character budget cap to prevent SOUL template bloat | Budget enforcement is done in `spawn.py` after retrieval, before mounting. Bullet-drop strategy: iterate items in rank order, add bullet, stop when budget would be exceeded. |
| RET-04 | Pre-spawn retrieval degrades gracefully to empty context if memory service is unavailable | `MemoryClient.retrieve()` already returns `[]` on any network/timeout error. Empty list → empty memory context → `$memory_context` substitutes as `""`. Container spawns normally with no Memory Context section. |
</phase_requirements>

---

## Summary

Phase 29 wires memory retrieval into the L3 spawn path so each container starts with relevant past-task context embedded in its SOUL. The key implementation challenge is that `spawn_l3_specialist()` is synchronous (it calls `client.containers.run()` via the Docker SDK which is sync), but `MemoryClient.retrieve()` is async (`httpx.AsyncClient`). The solution is a thin sync wrapper using `asyncio.run()` with a short timeout — or using `httpx` sync directly since the retrieve call is a single POST with a 3-second timeout.

The delivery mechanism uses Python's `tempfile.NamedTemporaryFile` to write the augmented SOUL content before calling `client.containers.run()`. The tempfile path is added to the container's `volumes` dict as a read-only bind mount at a known container-side path (recommended: `/orchestration/SOUL.md`, which is already a mounted read-only path and the natural place for L3 behavioral context). The entrypoint does not need changes because the L3 CLI runtime (`claude-code`) reads `CLAUDE.md` or a passed `--system-prompt`-style file — the delivered SOUL file is behavioral guidance for the agent, not an entrypoint concern. The temp file must outlive the `containers.run()` call but NOT the entire spawn function — it can be cleaned up after container creation, since Docker has already bind-mounted the file's inode.

The `$memory_context` variable must be added to the SOUL template's default and/or appended as an unconditional tail section in `spawn.py`'s rendering. Since the decision says `soul_renderer.py` stays unchanged, the implementation approach is: (1) call `render_soul(project_id)` to get the base SOUL content, (2) append a `\n\n## Memory Context\n\n{formatted_bullets}` section when memories exist (or append nothing when empty), (3) write this augmented content to a tempfile, (4) mount tempfile into the container.

**Primary recommendation:** Implement retrieval as a sync call using `httpx.Client` (not `httpx.AsyncClient`) directly in a new helper function in `spawn.py`, bypassing `MemoryClient` for the sync spawn context. Use `tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False)` to write the augmented SOUL, add the path to volumes, and clean up with `Path.unlink()` after `containers.run()` returns.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx.Client (sync) | 0.27+ | Single sync POST to memU /retrieve endpoint | Already installed (httpx is a dep); sync Client avoids asyncio complexity in sync spawn function |
| tempfile (stdlib) | 3.x | Write augmented SOUL to a temp file before container creation | stdlib; `NamedTemporaryFile(delete=False)` gives a path that can be added to volumes dict |
| orchestration.soul_renderer.render_soul | existing | Render base SOUL content (without memory context) | Already exists, tested, and returns a string — caller augments before writing to tempfile |
| orchestration.memory_client.MemoryClient | Phase 27 | Retrieve memories scoped to project (async) — usable if spawn is refactored to async | Already has sentinel degradation and 3s timeout |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| orchestration.project_config.get_memu_config | Phase 28 | Get MEMU_API_URL for retrieval call | Already in spawn.py imports — used for env injection |
| pathlib.Path | stdlib | Write tempfile content, clean up after spawn | Already used throughout spawn.py |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx.Client (sync) | asyncio.run(MemoryClient.retrieve()) | `asyncio.run()` fails if called inside an already-running event loop. spawn.py is sync, so `asyncio.run()` works — but if pool.py ever calls spawn from async context, it breaks. Sync httpx.Client is safer. |
| httpx.Client (sync) | requests library | requests is not installed; httpx is. Both are equivalent for a single POST. |
| NamedTemporaryFile(delete=False) | tempfile.mkstemp | mkstemp returns (fd, path); NamedTemporaryFile is cleaner and familiar. Both work. |
| Appending memory section in spawn.py | Adding $memory_context to soul-default.md template | Adding to template requires soul_renderer.py changes (locked out by decision). Appending in spawn.py keeps soul_renderer.py unchanged as required. |

**Installation:** No new packages required — `httpx` and `tempfile` are already available.

---

## Architecture Patterns

### Recommended Project Structure

No new files needed. Changes are additive to:

```
skills/spawn_specialist/
└── spawn.py   # + _retrieve_memories_sync() + _format_memory_context()
               # + _build_augmented_soul() + tempfile volume mount logic

agents/_templates/
└── soul-default.md   # unchanged — memory context is appended by spawn.py, not via $variable
```

### Pattern 1: Sync Memory Retrieval in Spawn Path

**What:** A thin sync wrapper that calls the memU `/retrieve` endpoint directly using `httpx.Client` without going through `MemoryClient` (which is async-only).

**When to use:** Any sync function that needs a single HTTP call to memU.

**Why not `MemoryClient`:** `MemoryClient` uses `httpx.AsyncClient` and requires `async with` / `await`. `spawn_l3_specialist()` is synchronous. Wrapping with `asyncio.run()` works today but breaks if pool.py ever calls spawn from within an async context (RuntimeError: cannot be called from a running event loop).

**Recommended approach:** Direct sync `httpx.Client` POST with a 3-second timeout, mirroring `TIMEOUT_RETRIEVE = httpx.Timeout(3.0, connect=2.0)` from `memory_client.py`. Catches all exceptions and returns `[]` on any failure.

```python
# Source: httpx docs (sync client) + memory_client.py TIMEOUT_RETRIEVE pattern
import httpx

MEMORY_CONTEXT_BUDGET = 2000  # hard cap in characters
MEMORY_RETRIEVE_TIMEOUT = httpx.Timeout(3.0, connect=2.0)
MEMORY_RETRIEVE_LIMIT = 10  # max items to request from memU

def _retrieve_memories_sync(base_url: str, project_id: str, query: str) -> list:
    """
    Retrieve memories from memU synchronously.

    Returns:
        List of memory dicts on success, [] on any error (degraded gracefully).
    """
    if not base_url:
        return []
    payload = {
        "queries": [{"role": "user", "content": query}],
        "where": {"user_id": project_id},
    }
    try:
        with httpx.Client(base_url=base_url, timeout=MEMORY_RETRIEVE_TIMEOUT) as client:
            response = client.post("/retrieve", json=payload)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "items" in data:
                return data["items"]
            return []
    except Exception as exc:
        logger.warning(
            "Pre-spawn memory retrieval failed (non-blocking)",
            extra={"project_id": project_id, "error": str(exc)},
        )
        return []
```

### Pattern 2: Budget-Aware Memory Context Formatting

**What:** Convert retrieved memory dicts to bullet-point markdown, respecting a 2,000-char hard budget. Items are ordered by relevance (as returned by memU). Items are added one at a time; the loop stops before adding a bullet that would exceed the budget.

**Budget accounting:** Measure total rendered length of all bullets accumulated so far (including newlines), not just content text. This ensures the section as mounted into the container never exceeds the cap.

**Trimming strategy:** Drop whole items (lowest-ranked last) rather than truncating individual bullets. A truncated bullet is misleading; a missing bullet is honest.

**Source tag:** Use `(memorized {n}d ago)` when `created_at` is available; fall back to `(from memory)` when metadata is absent. Use `(from L2 review)` if the memory's `category` is `l2_review` (Phase 30 future-compat).

```python
def _format_memory_context(memories: list) -> str:
    """
    Format retrieved memories as a ## Memory Context markdown section.

    Returns:
        Formatted section string (including header), or "" if no memories.
        Total length is guaranteed <= MEMORY_CONTEXT_BUDGET characters.
    """
    if not memories:
        return ""

    bullets = []
    total_chars = 0

    for item in memories:
        # Extract text content — memU returns resource_url as the stored content
        content = item.get("resource_url", "") or item.get("content", "") or str(item)

        # Build source tag
        category = item.get("category", "")
        created_at = item.get("created_at", "")
        if category == "l2_review":
            source_tag = "(from L2 review)"
        elif created_at:
            # Parse age in days if possible; fall back to generic tag
            source_tag = "(from memory)"  # simplified; planner may refine
        else:
            source_tag = "(from memory)"

        bullet = f"- {content} {source_tag}"
        # Check budget before adding
        candidate_total = total_chars + len(bullet) + 1  # +1 for newline
        if candidate_total > MEMORY_CONTEXT_BUDGET:
            break  # drop remaining items

        bullets.append(bullet)
        total_chars += len(bullet) + 1

    if not bullets:
        return ""

    section = "## Memory Context\n\n" + "\n".join(bullets)
    return section
```

### Pattern 3: Augmented SOUL via Tempfile Volume Mount

**What:** Call `render_soul(project_id)` to get the base SOUL content, optionally append the memory context section, write to a tempfile, and add the tempfile path as a read-only volume mount before calling `containers.run()`.

**Known container-side path:** Mount at `/orchestration/SOUL.md`. The `/orchestration` directory is already mounted read-only from `project_root / "orchestration"`. However, that is a **directory** bind mount — adding a file bind mount for `SOUL.md` inside the same directory may conflict. The safer path is a new dedicated mount point: `/workspace/.openclaw/soul.md` (writable mount already exists) or a new constant like `/run/openclaw/soul.md`.

**Recommended container-side path:** `/run/openclaw/soul.md` — clean, dedicated, no conflict with existing mounts. The entrypoint already has access to read any path; the L3 CLI runtime would need to be told this path via an environment variable `SOUL_FILE=/run/openclaw/soul.md`.

**Temp file lifecycle:** Write before `containers.run()`, clean up immediately after. Docker bind-mounts by inode — the file can be deleted from the host after the container is running; the container retains read access through the bind mount until it exits.

```python
# Source: Python docs — tempfile.NamedTemporaryFile
import tempfile
from pathlib import Path
from orchestration.soul_renderer import render_soul

SOUL_CONTAINER_PATH = "/run/openclaw/soul.md"

def _build_augmented_soul(project_id: str, memory_context: str) -> str:
    """Render base SOUL and append memory context section if non-empty."""
    base_soul = render_soul(project_id)
    if not memory_context:
        return base_soul
    # Append memory section after the final trailing newline
    return base_soul.rstrip("\n") + "\n\n" + memory_context + "\n"


def _write_soul_tempfile(content: str) -> Path:
    """Write SOUL content to a named temp file. Caller is responsible for cleanup."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".soul.md",
        prefix="openclaw-",
        delete=False,
    )
    tmp.write(content)
    tmp.flush()
    tmp.close()
    return Path(tmp.name)
```

The caller flow in `spawn_l3_specialist()`:

```python
# 1. Retrieve memories
memu_cfg = get_memu_config()
base_url = memu_cfg.get("memu_api_url", "")
query = f"{task_description} skill:{skill_hint}"
memories = _retrieve_memories_sync(base_url, project_id, query)

# 2. Format memory context
memory_context = _format_memory_context(memories)
memory_count = len([m for m in (memory_context.splitlines()) if m.startswith("-")])
memory_chars = len(memory_context)
if memory_context:
    logger.info(
        f"Injected {memory_count} memories ({memory_chars} chars) into SOUL",
        extra={"task_id": task_id, "project_id": project_id},
    )

# 3. Build augmented SOUL and write to tempfile
soul_content = _build_augmented_soul(project_id, memory_context)
soul_tempfile = _write_soul_tempfile(soul_content)

# 4. Add tempfile to volumes before containers.run()
container_config["volumes"][str(soul_tempfile)] = {
    "bind": SOUL_CONTAINER_PATH,
    "mode": "ro",
}
container_config["environment"]["SOUL_FILE"] = SOUL_CONTAINER_PATH

# 5. Spawn container
try:
    container = client.containers.run(**container_config)
finally:
    # Clean up tempfile after Docker has bind-mounted it (inode persists in container)
    soul_tempfile.unlink(missing_ok=True)
```

### Pattern 4: Query Composition

**What:** The memU `/retrieve` endpoint accepts a `queries` list of `{"role": "user", "content": "..."}` messages. The query should be specific enough to retrieve task-relevant memories.

**Recommended composition:** `f"{task_description} skill:{skill_hint}"` — combines the actual task description (semantic anchor) with the skill type (filters to code vs test context). This gives memU enough signal to find memories from similar past tasks.

**Number of results:** Request 10 from memU. After budget enforcement, typically 3-5 bullets will survive. Requesting more allows the budget trimmer to select the most relevant subset.

### Anti-Patterns to Avoid

- **Calling `asyncio.run()` in spawn.py:** Fails if called from within an already-running event loop (pool.py is async). Use sync `httpx.Client` instead.
- **Mounting the tempfile inside `/orchestration` directory:** `/orchestration` is already a directory bind mount; adding a file bind inside it may silently fail or conflict. Use a dedicated `/run/openclaw/` path.
- **Deleting the tempfile BEFORE `containers.run()`:** Docker needs the file to exist at bind-mount time. Clean up only in a `finally:` block after `containers.run()`.
- **Passing memory context via environment variable:** The 2,000-char budget could fit in an env var, but env vars have a combined 128KB limit and are visible in `docker inspect`. A tempfile is cleaner and more secure.
- **Modifying soul-default.md or soul_renderer.py:** The locked decision explicitly prohibits this. Augmentation happens post-render in spawn.py.
- **Raising exceptions when retrieval fails:** `_retrieve_memories_sync()` must return `[]` on ANY exception, never raise. The container must always spawn — memory context is a best-effort enhancement.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sync HTTP to memU | Custom socket or urllib | `httpx.Client` (already installed) | Handles connection pooling, timeout, JSON parsing |
| SOUL rendering | Custom template engine | `render_soul(project_id)` from soul_renderer.py | Already tested, handles override merging, variable substitution |
| Budget trimming | Character-level truncation inside bullets | Whole-item drop loop | Truncated bullets are misleading; drop whole items for honest degradation |

**Key insight:** The retrieval call is a single sync HTTP POST. The augmented SOUL is a string append. The tempfile is three stdlib calls. This phase is structurally simpler than Phase 28 — the complexity is in getting the sync/async boundary right and the tempfile lifecycle correct.

---

## Common Pitfalls

### Pitfall 1: asyncio.run() Breaks When Called from async Context

**What goes wrong:** `asyncio.run()` raises `RuntimeError: This event loop is already running` if called from within an async function (e.g., if `pool.py`'s `_attempt_task()` were refactored to call `spawn_l3_specialist()` directly).

**Why it happens:** `asyncio.run()` creates a new event loop and blocks the thread. If the thread already has a running event loop (asyncio), this is illegal.

**How to avoid:** Use `httpx.Client` (sync) directly in `_retrieve_memories_sync()`. The sync client has no asyncio dependency.

**Warning signs:** `RuntimeError: This event loop is already running` on spawn.

### Pitfall 2: Tempfile Deleted Before Docker Bind-Mounts It

**What goes wrong:** Docker raises `docker.errors.APIError: invalid mount config` or mounts an empty file if the tempfile is deleted before `containers.run()` completes.

**Why it happens:** Docker daemon opens the file by path at container start time. If the host deletes the file after `containers.run()` returns (the handle is passed to the daemon), the container retains access via inode. But if deleted BEFORE `run()`, the bind fails.

**How to avoid:** Wrap `containers.run()` in `try/finally`, delete tempfile in the `finally` block. This guarantees cleanup even on Docker API errors, and guarantees the file exists during `run()`.

**Warning signs:** Container fails to start, or SOUL file is empty inside container.

### Pitfall 3: Empty Memory Context Produces Blank Header

**What goes wrong:** If `_format_memory_context()` returns `"## Memory Context\n\n"` (header with no bullets) when no memories are found, the SOUL.md contains a blank section that the L3 agent might misinterpret.

**Why it happens:** Off-by-one in the formatting logic — returning the header even when the bullets list is empty.

**How to avoid:** `_format_memory_context()` must return `""` (empty string) when `memories` is `[]` or when all items exceed the budget individually. The `_build_augmented_soul()` function must only append when `memory_context` is truthy. This satisfies success criterion 4 and the locked decision: "when no memories are retrieved, the section is hidden entirely."

**Warning signs:** SOUL.md contains `## Memory Context` header with nothing below it.

### Pitfall 4: Budget Counting Includes/Excludes Markup Inconsistently

**What goes wrong:** If budget is counted against content-only (not including bullet dashes, newlines, or source tags), the actual mounted SOUL section may slightly exceed 2,000 chars due to markup overhead.

**Why it happens:** Budget accounting varies depending on whether `len(bullet)` includes the `"- "` prefix and source tag.

**How to avoid:** Count the fully rendered bullet string (including `"- "` prefix, content, source tag, and newline separator) against the budget. This is Claude's discretion per CONTEXT.md — the safest choice is total rendered length.

**Warning signs:** SOUL file memory section exceeds 2,000 chars when measured by `wc -c`.

### Pitfall 5: soul_renderer.render_soul() Raises When L3 Has No project.json Agent Mapping

**What goes wrong:** `render_soul()` calls `load_project_config()` → reads `agents.l2_pm` for the agent name. If the L3 specialist is the agent being spawned, there's no L2 agent involved in L3 SOUL rendering.

**Why it happens:** `render_soul()` is designed for L2 SOUL generation, not L3. Calling it with the project_id works for filling `$project_name`, `$workspace`, `$tech_stack_*`, but the `$agent_name` variable will resolve to the L2 PM name (or empty), not the L3 name.

**How to avoid:** The L3 SOUL content used for injection is the existing `agents/l3_specialist/agent/SOUL.md` (hardcoded behavioral constraints), NOT the L2-targeted `render_soul()` output. The implementation should read the L3 SOUL file directly (`root / "agents" / "l3_specialist" / "agent" / "SOUL.md"`) and append the memory context section to it.

**This is a critical design correction:** `render_soul(project_id)` generates L2 agent SOUL. The CONTEXT.md decision says inject into "the SOUL template" — this means the L3 SOUL.md at `agents/l3_specialist/agent/SOUL.md`, not the L2-rendered SOUL. The implementation reads that file directly (no template substitution needed — it has no `$` variables), appends the memory context, and writes to tempfile.

**Warning signs:** The mounted SOUL.md contains L2 PM behavioral directives (tactical translation, quality gate) instead of L3 constraints (workspace scope, branch discipline).

---

## Code Examples

### Complete _retrieve_memories_sync Implementation

```python
# Source: httpx docs (sync client), memory_client.py TIMEOUT_RETRIEVE pattern
import httpx

MEMORY_CONTEXT_BUDGET = 2000  # characters, hard cap
_RETRIEVE_TIMEOUT = httpx.Timeout(3.0, connect=2.0)
_RETRIEVE_LIMIT = 10

def _retrieve_memories_sync(base_url: str, project_id: str, query: str) -> list:
    """Sync retrieval from memU /retrieve. Returns [] on any error."""
    if not base_url or not project_id:
        return []
    payload = {
        "queries": [{"role": "user", "content": query}],
        "where": {"user_id": project_id},
    }
    try:
        with httpx.Client(base_url=base_url, timeout=_RETRIEVE_TIMEOUT) as client:
            response = client.post("/retrieve", json=payload)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                return data[:_RETRIEVE_LIMIT]
            if isinstance(data, dict) and "items" in data:
                return data["items"][:_RETRIEVE_LIMIT]
            return []
    except Exception as exc:
        logger.warning(
            "Pre-spawn memory retrieval failed (non-blocking)",
            extra={"project_id": project_id, "error": str(exc)},
        )
        return []
```

### Complete _format_memory_context Implementation

```python
def _format_memory_context(memories: list) -> str:
    """
    Format memories as a markdown ## Memory Context section.

    Returns "" when memories is empty or all items exceed budget.
    Returns section string with header + bullets, total <= MEMORY_CONTEXT_BUDGET chars.
    """
    if not memories:
        return ""

    bullets = []
    total_chars = 0

    for item in memories:
        # Extract content — memU stores text in resource_url field
        text = item.get("resource_url", "") or item.get("content", "") or ""
        if not text:
            continue

        # Build source tag
        category = item.get("category", "")
        if category == "l2_review":
            tag = "(from L2 review)"
        else:
            tag = "(from memory)"

        bullet = f"- {text} {tag}"
        candidate = total_chars + len(bullet) + 1  # +1 for \n separator
        if candidate > MEMORY_CONTEXT_BUDGET:
            break  # drop remaining items rather than truncating

        bullets.append(bullet)
        total_chars += len(bullet) + 1

    if not bullets:
        return ""

    return "## Memory Context\n\n" + "\n".join(bullets)
```

### Spawn.py Integration: Augmentation + Tempfile Mount

```python
# Source: Python docs — tempfile.NamedTemporaryFile; Docker SDK volumes dict
import tempfile
from pathlib import Path

SOUL_CONTAINER_PATH = "/run/openclaw/soul.md"

def _get_l3_soul_base(project_root: Path) -> str:
    """Read the L3 specialist base SOUL.md content."""
    soul_path = project_root / "agents" / "l3_specialist" / "agent" / "SOUL.md"
    if soul_path.exists():
        return soul_path.read_text()
    return ""  # graceful: no SOUL if file missing

def _build_augmented_soul(project_root: Path, memory_context: str) -> str:
    """Combine L3 base SOUL with memory context section."""
    base = _get_l3_soul_base(project_root)
    if not memory_context:
        return base
    return base.rstrip("\n") + "\n\n" + memory_context + "\n"

# In spawn_l3_specialist(), before container_config["volumes"] usage:
memu_cfg = get_memu_config()
base_url = memu_cfg.get("memu_api_url", "")
query = f"{task_description} skill:{skill_hint}"
memories = _retrieve_memories_sync(base_url, project_id, query)
memory_context = _format_memory_context(memories)

if memory_context:
    bullet_count = sum(1 for line in memory_context.splitlines() if line.startswith("-"))
    logger.info(
        f"Injected {bullet_count} memories ({len(memory_context)} chars) into SOUL",
        extra={"task_id": task_id, "project_id": project_id},
    )

soul_content = _build_augmented_soul(project_root, memory_context)

# Write tempfile and track for cleanup
soul_tempfile = None
if soul_content:
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".soul.md", prefix="openclaw-", delete=False
    )
    tmp.write(soul_content)
    tmp.flush()
    tmp.close()
    soul_tempfile = Path(tmp.name)
    container_config["volumes"][str(soul_tempfile)] = {
        "bind": SOUL_CONTAINER_PATH,
        "mode": "ro",
    }
    container_config["environment"]["SOUL_FILE"] = SOUL_CONTAINER_PATH

# Spawn (tempfile must exist at this point)
try:
    container = client.containers.run(**container_config)
finally:
    if soul_tempfile:
        soul_tempfile.unlink(missing_ok=True)
```

### Verification: SOUL Byte Count Check

Success criterion 2 requires verifying the rendered SOUL memory section never exceeds 2,000 characters. Manual verification:

```bash
# After a spawn with memories, inspect the SOUL byte count inside the container
docker exec <container> wc -c /run/openclaw/soul.md

# Or check the section in isolation
docker exec <container> python3 -c "
content = open('/run/openclaw/soul.md').read()
idx = content.find('## Memory Context')
if idx >= 0:
    section = content[idx:]
    print(f'Memory section: {len(section)} chars')
else:
    print('No Memory Context section (graceful empty)')
"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| asyncio.run() for sync->async bridging | httpx.Client (sync) | N/A for this project | Avoids event-loop-already-running error when called from pool.py |
| Passing context via environment variables | Tempfile bind mount | N/A | Handles multi-KB content, avoids env var limits, cleaner separation |

**Deprecated/outdated:**
- `requests` library: Not installed in this project; httpx covers both sync and async.

---

## Open Questions

1. **Does the L3 entrypoint need changes to read SOUL_FILE?**
   - What we know: The entrypoint currently runs `${CLI_RUNTIME} --task "${TASK_DESCRIPTION}"`. Claude Code reads `CLAUDE.md` in the working directory automatically.
   - What's unclear: Does claude-code in the container pick up `SOUL_FILE` env var, or does the SOUL content need to be written to a specific path like `/workspace/CLAUDE.md`?
   - Recommendation: Write the augmented SOUL to `/workspace/.openclaw/{project_id}/soul.md` (within the already-writable `.openclaw` mount), and update the entrypoint to prepend the SOUL content to the task description or write it as `/workspace/CLAUDE.md` before invoking the CLI runtime. The planner should decide if entrypoint changes are in scope for this phase (they are not explicitly locked in/out by CONTEXT.md). Alternatively, if the SOUL is only for future use (not consumed in this phase), simply mounting it is sufficient.

2. **Should `render_soul(project_id)` be used for L3 SOUL content, or read `agents/l3_specialist/agent/SOUL.md` directly?**
   - What we know: `render_soul()` generates L2-targeted content (agent_name=L2 PM, tier=L2). The L3 SOUL at `agents/l3_specialist/agent/SOUL.md` contains L3-appropriate constraints (workspace scope, branch discipline, container lifecycle).
   - What's unclear: The CONTEXT.md says "writes a memory-augmented SOUL to a temp file" — which SOUL?
   - Recommendation: Read `agents/l3_specialist/agent/SOUL.md` directly. This is the L3 behavioral baseline that should be augmented with memory context. Do NOT use `render_soul()` which produces L2 agent content.

3. **Is the entrypoint change in scope for this phase?**
   - What we know: Success criterion 1 says "a spawned L3 container's rendered SOUL.md contains a Memory Context section." This implies the SOUL file is readable inside the container — which a bind mount achieves. But it doesn't require the CLI runtime to actually USE the SOUL file.
   - Recommendation: The phase should mount the file and set `SOUL_FILE` env var. Entrypoint integration (having the CLI read it) can be deferred if not explicitly required by the success criteria.

---

## Sources

### Primary (HIGH confidence)

- `~/.openclaw/skills/spawn_specialist/spawn.py` — full spawn_l3_specialist() function, volumes dict, environment dict, container_config structure
- `~/.openclaw/orchestration/memory_client.py` — retrieve() payload format, where clause, TIMEOUT_RETRIEVE constant, response shape handling
- `~/.openclaw/orchestration/soul_renderer.py` — render_soul() return type (str), L2-specific variable substitution, output format
- `~/.openclaw/agents/l3_specialist/agent/SOUL.md` — actual L3 SOUL content (no `$` template variables, can be read directly)
- `~/.openclaw/agents/_templates/soul-default.md` — L2 SOUL template (confirmed: L2-specific, wrong target for L3 injection)
- Python 3 stdlib docs — `tempfile.NamedTemporaryFile(delete=False)` lifecycle
- httpx docs — `httpx.Client` (sync) POST usage, Timeout configuration

### Secondary (MEDIUM confidence)

- Docker SDK Python docs — volumes dict format `{host_path: {"bind": container_path, "mode": "ro"}}` — confirmed by existing spawn.py usage pattern
- Docker bind-mount inode persistence — file deletion after container start does not affect container access (verified by Docker documentation)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use; no new dependencies
- Architecture: HIGH — call sites verified by direct codebase inspection; tempfile + volume pattern is stdlib + Docker SDK basics
- Pitfalls: HIGH — L2 vs L3 SOUL confusion verified by reading both template files; async/sync boundary verified by reading spawn.py and pool.py

**Research date:** 2026-02-24
**Valid until:** Stable — depends on soul_renderer.py and memory_client.py which are internal; no external API churn expected
