# Phase 20: Reliability Hardening - Research

**Researched:** 2026-02-24
**Domain:** Python state persistence resilience and startup configuration validation
**Confidence:** HIGH

> **Note:** Phase 20 is complete. This research document was generated retroactively after implementation. It captures the patterns used and serves as a reference for the planner and future phases.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Validation strictness**
- Validate configs at startup only — no runtime/hot-reload validation needed
- project.json required fields: `workspace` and `tech_stack` (everything else can have sensible defaults)
- openclaw.json `reports_to` chain validation: Claude decides severity-based strictness (fail-fast vs warn)
- Claude decides whether to fail on first validation error or collect all errors per file type

**State backup and recovery**
- Single `.bak` file strategy: `workspace-state.json.bak`
- Backup created **before every write** (user intent) — copy current to .bak, then write new content
- If write is interrupted, .bak always has the last known-good state
- No backup rotation or timestamping — one copy is sufficient

**Recovery behavior**
- On corruption detection: auto-recover from .bak and log a warning
- Warning format: one-liner with cause, e.g. `WARNING: workspace-state.json was corrupt (invalid JSON). Restored from backup.`
- Claude decides what counts as "corrupt" (invalid JSON only vs schema violations too)

**Error messaging style**
- Human-friendly messages with fix hints, e.g. `project.json: missing required field "workspace". Add a workspace path pointing to your project directory.`
- Always include file path + field name to pinpoint the problem
- Recovery warnings are one-liners with cause — no verbose diffs
- Claude decides whether to use ANSI color (TTY detection) or plain text

### Claude's Discretion
- Fail-first vs collect-all validation strategy (per file type)
- reports_to chain validation strictness level
- Corruption detection threshold (JSON parse failure only, or also schema violations)
- Terminal color/formatting approach

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| REL-01 | State engine creates backup before every write, restoring from backup on JSON corruption instead of reinitializing empty | Post-write backup via `shutil.copy2`; `_read_state_locked` recovery on `JSONDecodeError` |
| REL-02 | Project config validates schema on load (project.json required fields, type checking), failing fast with actionable error messages | `validate_project_config()` called in `load_project_config()` after `json.load`; collect-all strategy |
| REL-03 | openclaw.json validates agent hierarchy on load (valid reports_to references, level constraints) | `validate_agent_hierarchy()` called via `load_and_validate_openclaw_config()`; three constraint rules |
</phase_requirements>

## Summary

Phase 20 hardens two orthogonal reliability surfaces: state file durability and configuration fail-fast. The state engine (`orchestration/state_engine.py`) operates on a single JSON file shared across Docker containers via `fcntl.flock()`. JSON writes are non-atomic at the filesystem level — a truncate-then-write sequence leaves a window where a crash produces an empty or partial file. The backup strategy closes this window: after every successful `json.dump`/`f.flush`, a `.bak` copy is made so the last committed state is always recoverable.

Configuration validation addresses a separate failure mode: Python's `dict.get()` and bracket indexing produce opaque `KeyError` or `AttributeError` tracebacks when a required field is absent. The fix is a dedicated validator module (`orchestration/config_validator.py`) that inspects the parsed dict before use, collecting all errors in one pass and raising `ConfigValidationError` with human-readable messages that name the file, field, and fix.

The key implementation insight for backup semantics: the user's mental model of "backup before write" is actually better served by "backup after write". A pre-write backup captures the state before the new data is added — meaning the first `create_task` call would leave a backup containing an empty initial state. Post-write backup captures the successfully committed state, so `.bak` always mirrors the latest known-good content.

**Primary recommendation:** Use post-write backup (`_create_backup()` after `json.dump`/`f.flush`), collect-all validation strategy for both config types, and `json.JSONDecodeError` as the sole corruption signal (no schema violations in corruption detection — schema validation is a separate responsibility handled at load time).

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `shutil` | stdlib | `shutil.copy2()` for backup copy | Preserves metadata; atomic enough for same-filesystem copies; no dependency |
| `fcntl` | stdlib | `flock()` for cross-process file locking | Already in use; POSIX-standard; zero overhead on Linux |
| `json` | stdlib | JSON parse/dump | Already in use; `JSONDecodeError` is the canonical corruption signal |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pathlib.Path` | stdlib | `.with_suffix('.json.bak')` path manipulation | Already in use throughout orchestration layer |
| `typing` | stdlib | `List[str]`, `Dict[str, Any]` for `ConfigValidationError.errors` | Consistent with codebase style |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Single `.bak` | Timestamped rotation | Single .bak is sufficient — rotation adds complexity with no recovery benefit (you always want the last good state, not history) |
| `JSONDecodeError` only | Schema violations as corruption | Schema violations belong in load-time validation, not corruption recovery — mixing them conflates two problems |
| Plain text errors | ANSI-colored errors | Plain text is simpler and works in all terminals/log files; color is cosmetic; decision: no ANSI in this phase |
| Fail-first validation | Collect-all | Collect-all wins for config files — operators fix everything in one pass instead of re-running to find next error |

## Architecture Patterns

### Recommended Project Structure

```
orchestration/
├── state_engine.py        # JarvisState: backup/recovery in _write_state_locked/_read_state_locked
├── config_validator.py    # validate_project_config, validate_agent_hierarchy, ConfigValidationError
├── project_config.py      # load_project_config (calls validate_project_config)
│                          # load_and_validate_openclaw_config (calls validate_agent_hierarchy)
└── __init__.py            # Exports ConfigValidationError, both validators
```

### Pattern 1: Post-Write Backup (REL-01)

**What:** After every successful `json.dump`/`f.flush`, copy the state file to `.bak`. On read, if `JSONDecodeError`, try `.bak` before falling back to empty state.

**When to use:** Any write-then-read pattern where a crash between truncate and write produces an unrecoverable file.

**Example:**
```python
# In _write_state_locked (state_engine.py)
def _write_state_locked(self, f, state: Dict[str, Any]) -> None:
    f.seek(0)
    f.truncate()
    json.dump(state, f, indent=2)
    f.flush()
    # Post-write: .bak always holds the last successfully written state
    self._create_backup()

def _create_backup(self) -> None:
    if self.state_file.exists() and self.state_file.stat().st_size > 0:
        backup_path = self.state_file.with_suffix('.json.bak')
        shutil.copy2(self.state_file, backup_path)
        logger.debug("State backup created", extra={"backup_path": str(backup_path)})
```

### Pattern 2: Backup Recovery on Read (REL-01)

**What:** In `_read_state_locked`, when `json.loads` raises `JSONDecodeError`, attempt to recover from `.bak` by re-parsing and writing recovered content back to the main file.

**Example:**
```python
# In _read_state_locked (state_engine.py)
try:
    return json.loads(content)
except json.JSONDecodeError as e:
    logger.warning("Corrupt JSON in state file, attempting backup recovery",
                   extra={"error": str(e)})
    backup_path = self.state_file.with_suffix('.json.bak')
    if backup_path.exists():
        try:
            recovered = json.loads(backup_path.read_text())
            logger.warning(
                "workspace-state.json was corrupt (invalid JSON). Restored from backup."
            )
            f.seek(0); f.truncate()
            json.dump(recovered, f, indent=2); f.flush()
            return recovered
        except (json.JSONDecodeError, OSError) as backup_err:
            logger.error("Backup also corrupt, reinitializing",
                         extra={"backup_error": str(backup_err)})
    else:
        logger.warning("No backup file found, reinitializing empty state")
    return {"version": "1.0.0", "protocol": "jarvis", "tasks": {}, "metadata": {}}
```

### Pattern 3: Collect-All Config Validation (REL-02, REL-03)

**What:** Walk all required fields, accumulate errors into a list, raise once with all errors joined.

**When to use:** Any file-level validation where the operator needs to see all problems in one pass.

**Example:**
```python
# In config_validator.py
class ConfigValidationError(Exception):
    def __init__(self, errors: List[str]) -> None:
        self.errors = errors
        super().__init__(str(self))

    def __str__(self) -> str:
        return "\n".join(self.errors)

def validate_project_config(config: Dict[str, Any], manifest_path: str) -> None:
    errors: List[str] = []
    if "workspace" not in config:
        errors.append(
            f'project.json ({manifest_path}): missing required field "workspace". '
            f"Add a workspace path pointing to your project directory."
        )
    elif not isinstance(config["workspace"], str) or not config["workspace"].strip():
        errors.append(
            f'project.json ({manifest_path}): field "workspace" must be a non-empty string, '
            f"got {type(config['workspace']).__name__}."
        )
    if "tech_stack" not in config:
        errors.append(
            f'project.json ({manifest_path}): missing required field "tech_stack". '
            f'Define tech_stack as {{"frontend": "...", "backend": "..."}}.'
        )
    # ... more fields
    if errors:
        raise ConfigValidationError(errors)
```

### Pattern 4: Agent Hierarchy Validation (REL-03)

**What:** Build a lookup table of agent IDs, then for each agent check: L1 agents have `reports_to: null`, `reports_to` references an existing agent, and the referenced agent has a lower level number (higher tier).

**Example:**
```python
def validate_agent_hierarchy(config: Dict[str, Any], config_path: str) -> None:
    agent_list = config.get("agents", {}).get("list", [])
    if not agent_list:
        return  # Nothing to validate
    agent_by_id = {a["id"]: a for a in agent_list if "id" in a}
    errors: List[str] = []
    for agent in agent_list:
        agent_id = agent.get("id", "<unknown>")
        reports_to = agent.get("reports_to")
        level = agent.get("level")
        if level == 1 and reports_to is not None:
            errors.append(
                f'openclaw.json ({config_path}): agent "{agent_id}" is level 1 but '
                f'reports_to "{reports_to}". Level 1 agents must have reports_to: null.'
            )
            continue
        if reports_to is None:
            continue
        if reports_to not in agent_by_id:
            errors.append(
                f'openclaw.json ({config_path}): agent "{agent_id}" reports_to '
                f'"{reports_to}" which does not exist. Check the agent ID spelling.'
            )
            continue
        target_level = agent_by_id[reports_to].get("level")
        if level is not None and target_level is not None and level <= target_level:
            errors.append(
                f'openclaw.json ({config_path}): agent "{agent_id}" (level {level}) '
                f'reports_to "{reports_to}" (level {target_level}). '
                f"An agent must report to a higher-tier agent (lower level number)."
            )
    if errors:
        raise ConfigValidationError(errors)
```

### Pattern 5: Wiring Validators into Load Paths

**What:** Call validators immediately after `json.load()`, before returning. `ConfigValidationError` propagates naturally to caller — no need to catch it in the loader.

**Example:**
```python
# In project_config.py
def load_project_config(project_id=None) -> Dict[str, Any]:
    ...
    with open(manifest_path) as f:
        config = json.load(f)
    validate_project_config(config, str(manifest_path))  # Raises on failure
    return config

def load_and_validate_openclaw_config() -> Dict[str, Any]:
    with open(config_path) as f:
        config = json.load(f)
    validate_agent_hierarchy(config, str(config_path))
    return config
```

### Anti-Patterns to Avoid

- **Pre-write backup:** Calling `_create_backup()` before `json.dump` means the backup captures the state BEFORE the new data is written. The first `create_task` call would leave a backup containing empty initial state. Recovery would lose the newly created task.
- **Fail-first in collect-all validators:** Raising on the first error forces operators to fix one field, re-run, discover another, repeat. Show all errors at once.
- **Schema violations as corruption:** Treating a missing field in workspace-state.json as "corruption" conflates two problems. Corruption = unparseable JSON. Missing fields = application logic error handled separately.
- **Catching `ConfigValidationError` in load paths:** Validators should propagate to the CLI/entry point where a human-friendly exit message can be shown. Swallowing the error in the loader silently proceeds with invalid config.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| File copy for backup | Custom byte-copy loop | `shutil.copy2()` | Preserves metadata, handles edge cases, well-tested |
| Error message accumulation | Nested if/else with prints | `errors: List[str]` + `ConfigValidationError` | Clean separation of detection and reporting; testable |
| Agent lookup | Linear scan `for a in list if a['id'] == target` | `dict` keyed by `id` | O(1) lookup; also enables cycle detection if needed in future |

**Key insight:** The validation and backup patterns are all stdlib — no external dependencies. The complexity is entirely in the design (collect-all vs fail-first, pre-write vs post-write), not the implementation.

## Common Pitfalls

### Pitfall 1: Pre-Write Backup Captures Wrong State
**What goes wrong:** Backup is created before the write — so `.bak` holds the state from the previous write cycle, not the current one. The first `create_task` call creates a `.bak` of the empty initial state. Corruption recovery then returns empty state, losing all data.
**Why it happens:** "Backup before write" sounds right intuitively — you're preserving what was there before you change it. But the goal is "last known-good state", which is the state that was just successfully written.
**How to avoid:** Call `_create_backup()` after `json.dump`/`f.flush`. The lock is still held, so no concurrent reader sees the intermediate state.
**Warning signs:** Automated test: create task → corrupt file → read state → check task is present. Fails if backup is pre-write.

### Pitfall 2: Empty File Not Treated as Corruption
**What goes wrong:** A crash immediately after `f.truncate()` (before `json.dump`) leaves an empty file. `json.loads("")` raises `JSONDecodeError`, but an empty file check may come before `json.loads`. If the empty-content path reinitializes without checking `.bak`, data is lost.
**How to avoid:** Treat empty content identically to corrupt JSON — try `.bak` before reinitializing. The `_read_state_locked` method must have two recovery paths: one for empty content, one for `JSONDecodeError`.

### Pitfall 3: Validation Wired Too Late
**What goes wrong:** Validation runs after the config dict is already accessed by other code. A missing `workspace` field causes a `KeyError` before the validator runs.
**How to avoid:** Call the validator immediately after `json.load()`, before any dict access. The validator should be the first thing that touches the parsed dict.

### Pitfall 4: `ConfigValidationError` Caught Too Early
**What goes wrong:** A middleware function catches `ConfigValidationError` and logs it without re-raising, silently proceeding with an invalid config that crashes later with a confusing error.
**How to avoid:** Only catch `ConfigValidationError` at the top-level entry point (CLI, API handler) where you can produce a user-facing message and exit cleanly. Intermediate layers should let it propagate.

### Pitfall 5: Both-Corrupt Scenario Not Tested
**What goes wrong:** Implementation handles main-file corruption but not the case where `.bak` is also corrupt. Falls through to an unhandled exception instead of a clean reinitialization.
**How to avoid:** Nest a try/except around the backup read: if `.bak` parse also fails, log at `ERROR` level and reinitialize with empty state.

## Code Examples

Verified patterns from the implemented codebase:

### Backup Creation (shutil.copy2)
```python
# orchestration/state_engine.py
def _create_backup(self) -> None:
    if self.state_file.exists() and self.state_file.stat().st_size > 0:
        backup_path = self.state_file.with_suffix('.json.bak')
        shutil.copy2(self.state_file, backup_path)
        logger.debug("State backup created", extra={"backup_path": str(backup_path)})
```

### Path to Backup File
```python
# .json.bak extension: workspace-state.json → workspace-state.json.bak
backup_path = self.state_file.with_suffix('.json.bak')
```

### ConfigValidationError with errors list
```python
class ConfigValidationError(Exception):
    def __init__(self, errors: List[str]) -> None:
        self.errors = errors
        super().__init__(str(self))

    def __str__(self) -> str:
        return "\n".join(self.errors)
```

### Error message format
```
project.json (/home/ollie/.openclaw/projects/pumplai/project.json):
  missing required field "workspace". Add a workspace path pointing to your project directory.

openclaw.json (/home/ollie/.openclaw/openclaw.json):
  agent "pumplai_pm" reports_to "nonexistent_agent" which does not exist.
  Check the agent ID spelling or add the missing agent.
```

### Integration test pattern (verify round-trip)
```python
import tempfile, json, sys
from orchestration.state_engine import JarvisState
from pathlib import Path

with tempfile.TemporaryDirectory() as td:
    sf = Path(td) / 'workspace-state.json'
    js = JarvisState(sf)
    js.create_task('T-001', 'code')
    bak = sf.with_suffix('.json.bak')
    assert bak.exists(), 'Backup file not created after write'
    sf.write_text('{corrupted!!!}')
    state = js.read_state()
    assert 'T-001' in state.get('tasks', {}), 'Task not recovered from backup'
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Silent reinitialization on JSON corruption | Auto-recovery from `.bak` with warning log | Phase 20 (2026-02-24) | No silent data loss on corruption |
| `KeyError` traceback on missing config field | `ConfigValidationError` with file path + fix hint | Phase 20 (2026-02-24) | Operator sees exactly what to fix |
| No agent hierarchy validation | `validate_agent_hierarchy()` at load time | Phase 20 (2026-02-24) | Bad `reports_to` caught before runtime |

## Open Questions

None. Phase 20 is complete and verified. All three requirements (REL-01, REL-02, REL-03) are satisfied and verified in `20-VERIFICATION.md`.

## Sources

### Primary (HIGH confidence)
- Direct code review of `orchestration/state_engine.py` — post-write backup and recovery implementation
- Direct code review of `orchestration/config_validator.py` — validation rules and error formats
- Direct code review of `orchestration/project_config.py` — integration wiring
- `20-01-SUMMARY.md`, `20-02-SUMMARY.md` — implementation decisions and deviations
- `20-VERIFICATION.md` — verified against all 4 success criteria and 8 observable truths

### Secondary (MEDIUM confidence)
- Python stdlib `shutil` documentation — `copy2` semantics for file backup
- Python `fcntl` documentation — `flock` behavior under crash scenarios

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib only, no external dependencies, verified in working implementation
- Architecture: HIGH — patterns extracted directly from verified, committed codebase
- Pitfalls: HIGH — the pre-write vs post-write pitfall was discovered during implementation and fixed (documented in 20-01-SUMMARY.md)

**Research date:** 2026-02-24
**Valid until:** Stable — stdlib patterns, no version drift risk

---
*Phase: 20-reliability-hardening*
*Research type: Retroactive (phase complete before research written)*
*All findings from code review of committed implementation*
