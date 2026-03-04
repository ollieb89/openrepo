# Phase 47: Env Var Precedence + Migration CLI - Research

**Researched:** 2026-02-25
**Domain:** Python CLI (argparse), env var resolution, config migration
**Confidence:** HIGH — all findings from direct codebase inspection

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Migration CLI output format**
- Claude decides format and verbosity for dry-run and applied-changes output (probably human-readable list of changes)
- When no changes needed: print "Already up-to-date" and exit 0
- After writing changes: Claude decides summary verbosity (probably "Migrated X: N changes applied. Backup saved to X.bak")

**Migration backup behaviour**
- Auto-create `openclaw.json.bak` before any write (always, no flags required)
- Also backup each `project.json` before writing (e.g., `project.json.bak`)

**Migration trigger and detection**
- Claude decides detection strategy (structural diff is likely cleanest given no prior schema version field)
- Minimum viable input: config must have at least the top-level structure (gateway object, agents array) — freeform JSON gets a clear rejection
- Unknown fields: removed during migration (config comes out valid per Phase 46 schema)
- Scope: migrates `openclaw.json` AND all `project.json` files found under `projects/`

**Env var resolution**
- All callers route through `config.py` — one authoritative resolver, no direct `os.environ` reads scattered across components
- `OPENCLAW_STATE_FILE` gap fixed: Python `get_state_path()` must honour this env var (currently only entrypoint.sh reads it)
- `OPENCLAW_ROOT` pointing to a non-existent directory → auto-create with `mkdir -p`
- Override logging: Claude decides signal level (likely DEBUG — silent in normal operation, visible with verbose flag)

**Precedence documentation**
- `openclaw.json.example` updated with inline comments on each overridable field (e.g., `// Override with OPENCLAW_LOG_LEVEL env var`)
- `config.py` gets a comment block near the resolver functions documenting the full precedence chain
- `openclaw config --help` includes a concise list of env vars with brief one-line descriptions (no full examples)

### Claude's Discretion
- Exact dry-run and post-migration output format and verbosity
- Whether env var override logging is DEBUG or a different level
- Migration detection strategy (structural diff vs version field vs combined)
- How the precedence comment block in config.py is structured

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CONF-03 | Operator can run `openclaw config migrate` to upgrade an existing `openclaw.json` to the current schema with a dry-run preview | `migrate` subcommand added to `openclaw.cli.config:main`; structural diff detection; backup before write; scope covers `openclaw.json` + all `projects/*/project.json` |
| CONF-04 | Env var precedence is explicitly documented in `openclaw.json` comments and enforced uniformly — `OPENCLAW_ROOT` → `OPENCLAW_PROJECT` → `OPENCLAW_LOG_LEVEL` → `OPENCLAW_ACTIVITY_LOG_MAX` resolution order is consistent across all callers | Single remaining gap: `OPENCLAW_PROJECT` is read via `os.environ.get()` in `project_config.py` — must move to `config.py`; `OPENCLAW_ROOT`, `OPENCLAW_STATE_FILE`, `LOG_LEVEL`, `ACTIVITY_LOG_MAX_ENTRIES` already route through `config.py` |
</phase_requirements>

---

## Summary

Phase 47 has two independent deliverables: (1) close the env var uniformity gap left by Phase 45, and (2) add a `migrate` subcommand to the existing `openclaw-config` CLI that upgrades stale config files to the current Phase 46 schema.

The env var work is minimal. `OPENCLAW_ROOT`, `OPENCLAW_STATE_FILE`, `OPENCLAW_LOG_LEVEL`, and `OPENCLAW_ACTIVITY_LOG_MAX` already route through `config.py`. The single remaining scatter is `OPENCLAW_PROJECT`, read directly via `os.environ.get("OPENCLAW_PROJECT")` in `project_config.py:get_active_project_id()`. Moving that one line into a `get_active_project_id()` helper in `config.py` closes CONF-04. The `OPENCLAW_ROOT` auto-create behaviour is also missing — `_find_project_root()` returns the path but never creates it when the env var points to a non-existent directory.

The migration CLI builds on Phase 46's existing `validate_openclaw_config()` / `validate_project_config_schema()` validators. Migration detection is structural: run the validator, collect `additionalProperties` warnings (unknown fields to remove), and check for fatal required-field errors (which cannot be auto-fixed — report and exit with guidance). The `migrate` subcommand is added to `openclaw.cli.config:main`, the only file that needs editing for the CLI surface. No new entry point in `pyproject.toml` is needed; the existing `openclaw-config` entrypoint already delegates to subcommands.

**Primary recommendation:** Add `get_active_project_id()` to `config.py`, fix `_find_project_root()` auto-create, add `migrate` to `cli/config.py`. Three file changes; no new dependencies.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `argparse` | stdlib | CLI argument parsing | Already used for `show`, `project`, `monitor`, `suggest` |
| `json` | stdlib | Config parsing/serialisation | Used throughout the codebase |
| `pathlib.Path` | stdlib | Filesystem operations | Project standard — all existing CLI code uses Path |
| `jsonschema.Draft202012Validator` | >=4.26.0 (already in deps) | Schema validation for migration detection | Added in Phase 46; already in `pyproject.toml` |
| `shutil.copy2` | stdlib | Backup before write | Same pattern as `migrate_state.py` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `difflib.unified_diff` | stdlib | Dry-run diff output | Used when `--dry-run` flag is set to show what would change |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `difflib.unified_diff` | Custom field-by-field printer | Unified diff is standard and familiar; custom printer is more human-friendly but adds implementation work |
| Structural diff via validator | Adding `_schema_version` to config | No version field exists today; adding one creates its own migration chicken-and-egg problem |

**Installation:**
No new pip dependencies — all required libraries are already present.

---

## Architecture Patterns

### Recommended Project Structure

No new files needed beyond what Phase 46 already created:

```
packages/orchestration/src/openclaw/
├── config.py              # Add get_active_project_id(), fix _find_project_root() auto-create
├── project_config.py      # Remove direct os.environ.get("OPENCLAW_PROJECT"); import from config
├── cli/
│   └── config.py          # Add cmd_migrate(), add 'migrate' subparser to main()
packages/orchestration/tests/
└── test_config_validator.py  # Extend: add migration tests
```

### Pattern 1: Env Var Resolver in config.py

**What:** All env var reads live in `config.py` as module-level constants or resolver functions. Callers import from `config`, never call `os.environ` directly.

**When to use:** Every new env var override must follow this pattern.

**Current state (before Phase 47):**
```python
# config.py — already correct:
LOG_LEVEL = os.environ.get("OPENCLAW_LOG_LEVEL", "INFO").upper()
ACTIVITY_LOG_MAX_ENTRIES = int(os.environ.get("OPENCLAW_ACTIVITY_LOG_MAX", "100"))

def _find_project_root() -> Path:
    env_root = os.environ.get("OPENCLAW_ROOT")
    if env_root:
        return Path(env_root)
    return Path.home() / ".openclaw"

def get_state_path(project_id: str) -> Path:
    env_state = os.environ.get("OPENCLAW_STATE_FILE")
    if env_state:
        return Path(env_state)
    ...

# project_config.py — BROKEN (direct read, must move):
def get_active_project_id() -> str:
    env_project = os.environ.get("OPENCLAW_PROJECT")  # <-- move to config.py
    ...
```

**After Phase 47 — config.py addition:**
```python
def get_active_project_env() -> str | None:
    """Return OPENCLAW_PROJECT env var value, or None if not set.

    Resolution order: OPENCLAW_PROJECT env var -> openclaw.json active_project
    This function handles the env var half; project_config.py handles the file half.
    """
    return os.environ.get("OPENCLAW_PROJECT") or None
```

**project_config.py updated:**
```python
from .config import get_active_project_env

def get_active_project_id() -> str:
    env_project = get_active_project_env()  # routes through config.py
    if env_project:
        return env_project
    ...
```

**Simpler alternative** (also valid): Just add `ACTIVE_PROJECT_ENV_VAR = os.environ.get("OPENCLAW_PROJECT")` as a module-level constant in `config.py` and import that constant in `project_config.py`. Either approach satisfies "routes through config.py".

### Pattern 2: OPENCLAW_ROOT Auto-Create

**What:** When `OPENCLAW_ROOT` points to a non-existent directory, create it rather than failing downstream with confusing `FileNotFoundError`.

**Location:** `_find_project_root()` in `config.py`.

```python
def _find_project_root() -> Path:
    env_root = os.environ.get("OPENCLAW_ROOT")
    if env_root:
        root = Path(env_root)
        root.mkdir(parents=True, exist_ok=True)  # auto-create
        return root
    return Path.home() / ".openclaw"
```

**Note:** The `~/.openclaw` fallback does NOT auto-create — only the explicitly-set env var path. This avoids silently creating `~/.openclaw` when it doesn't exist (a pre-existing behaviour).

### Pattern 3: migrate Subcommand in cli/config.py

**What:** Add `migrate` to the existing `openclaw-config` CLI. No new entrypoint — `pyproject.toml` already has `openclaw-config = "openclaw.cli.config:main"`.

**CLI surface:**
```
openclaw-config migrate [--dry-run] [--config PATH]
```

- `--dry-run`: print what would change, do not modify files
- `--config PATH`: override config file path (defaults to `<project_root>/openclaw.json`)

**Migration algorithm for a single file:**
1. Parse JSON — if unparseable, print clear error and exit 1
2. Run schema validator — collect fatal (missing required fields) and warnings (unknown fields)
3. If fatal errors: print actionable message, exit 1 (cannot auto-fix missing required fields)
4. If no warnings and no structural gaps: print "Already up-to-date." exit 0
5. In dry-run: print a human-readable list of what would change, exit 0
6. In apply mode:
   a. `shutil.copy2(config_path, config_path + ".bak")` — unconditional backup
   b. Remove unknown fields from the dict
   c. Write back as pretty JSON (indent=2)
   d. Print "Migrated {path}: {N} field(s) removed. Backup saved to {path}.bak"

**Scope — both config types:**
```python
def cmd_migrate(args) -> int:
    root = get_project_root()

    # 1. Migrate openclaw.json
    rc = _migrate_one_file(root / "openclaw.json", "openclaw", dry_run=args.dry_run)

    # 2. Migrate all project.json files
    projects_dir = root / "projects"
    if projects_dir.exists():
        for project_dir in sorted(projects_dir.iterdir()):
            if project_dir.is_dir() and not project_dir.name.startswith("_"):
                manifest = project_dir / "project.json"
                if manifest.exists():
                    rc2 = _migrate_one_project_file(manifest, dry_run=args.dry_run)
                    if rc2 != 0:
                        rc = rc2
    return rc
```

### Pattern 4: Precedence Documentation

**What:** Three locations get updated:

1. **`config.py` comment block** near the resolver functions:
```python
# ── Env Var Precedence ────────────────────────────────────────────────────────
# The following environment variables override their config-file counterparts.
# Resolution order (first set wins):
#
#   OPENCLAW_ROOT            → project root directory (default: ~/.openclaw)
#   OPENCLAW_PROJECT         → active project ID (default: openclaw.json active_project)
#   OPENCLAW_LOG_LEVEL       → log verbosity: DEBUG|INFO|WARNING|ERROR (default: INFO)
#   OPENCLAW_ACTIVITY_LOG_MAX → max activity log entries per task (default: 100)
#   OPENCLAW_STATE_FILE      → workspace state file path (L3 containers only)
#
# All env var reads are centralised in this module. No component should call
# os.environ directly for OpenClaw configuration values.
# ─────────────────────────────────────────────────────────────────────────────
```

2. **`config/openclaw.json.example`** — add `// Override with OPENCLAW_LOG_LEVEL env var` inline comments on the relevant fields. The example already uses `_comment_*` JSON keys; add comments for the env var overridable fields on `active_project` and `gateway.port` (non-overridable) vs `LOG_LEVEL` / `ACTIVITY_LOG_MAX` (which are not config-file fields).

3. **`openclaw-config --help`** epilog — add a brief env var table.

### Anti-Patterns to Avoid

- **Direct `os.environ.get()` in non-config modules:** Any caller that reads an env var directly bypasses the single-source pattern. Always import from `config.py`.
- **Auto-fixing missing required fields in migration:** If `gateway.port` is missing, migration cannot guess a port number. Print a clear error with the field name and example value; don't fabricate a default.
- **Overwriting backup:** `shutil.copy2` silently overwrites an existing `.bak`. This is acceptable (`.bak` is always the state just before the most recent migrate run).
- **Mutating the example file's `_comment_*` keys:** The example file is not parsed by the validator in normal operation; `_comment_*` keys are documentation only. Don't add them to live configs.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Config diff detection | Custom field comparison | `validate_openclaw_config()` + `validate_project_config_schema()` from Phase 46 | Already collect unknown fields as warnings; reuse directly |
| Backup | Custom copy logic | `shutil.copy2()` | Preserves metadata, idiomatic Python |
| Pretty-print output | Custom JSON serialiser | `json.dumps(config, indent=2, default=str)` | Already used in `cmd_show` |

**Key insight:** The Phase 46 schema validator already identifies all unknown fields as warnings. Migration is just: collect those warnings, strip the flagged fields from the dict, write back. Zero new detection logic needed.

---

## Common Pitfalls

### Pitfall 1: Module-Level Constants Are Import-Time Evaluated

**What goes wrong:** `LOG_LEVEL = os.environ.get("OPENCLAW_LOG_LEVEL", "INFO").upper()` is evaluated once at import. If tests set `os.environ["OPENCLAW_LOG_LEVEL"]` after importing `config`, the constant is stale.

**Why it happens:** Python module-level assignments run once at first import; subsequent env var changes don't re-evaluate.

**How to avoid:** In tests that exercise env var behaviour, use `monkeypatch.setenv()` BEFORE importing the module, or reload the module after setting the env var (`importlib.reload`). For Phase 48 integration tests (CONF-07), this is the standard approach.

**Warning signs:** Test sets env var, asserts value, gets the default instead.

### Pitfall 2: Migration Writes Non-Roundtrippable JSON

**What goes wrong:** Loading JSON with `json.load()` and dumping with `json.dumps(indent=2)` changes whitespace, key ordering, and unicode escaping. The file is semantically identical but looks different in `git diff`.

**Why it happens:** `json.dumps` sorts keys by default when `sort_keys=True`, or preserves insertion order otherwise. Either way, the formatting change is inevitable.

**How to avoid:** Accept this: migration is a one-time operation. Document it ("migrate rewrites the file with standard formatting"). Do NOT use `sort_keys=True` — preserve the original key order (dict insertion order in Python 3.7+).

### Pitfall 3: Unknown Field in `_comment_*` Pattern

**What goes wrong:** `openclaw.json.example` uses `_comment_*` keys as documentation. If someone copies the example file as their live config, migration will remove all `_comment_*` keys (they are unknown per the schema).

**Why it happens:** The schema has `additionalProperties: false`; `_comment_*` are not defined properties.

**How to avoid:** This is correct behaviour — migration strips documentation keys from live configs. The dry-run output will show them being removed. Document this in the migration output ("Note: _comment_* documentation keys are removed in migration; see config/openclaw.json.example for reference").

### Pitfall 4: project.json Missing Required Fields

**What goes wrong:** A project.json that is missing `workspace` or `tech_stack` will produce fatal errors from the schema validator. Migration cannot auto-fix these.

**Why it happens:** There's no reasonable default for `workspace` (it's a local filesystem path).

**How to avoid:** When migration encounters a project.json with fatal schema errors, print a clear message: "ERROR: projects/{id}/project.json has required fields missing — manual fix needed: {field_list}". Skip that file (don't write it), continue with remaining projects, exit non-zero.

### Pitfall 5: OPENCLAW_ROOT Auto-Create Side Effect

**What goes wrong:** `_find_project_root()` with auto-create will silently create a directory if `OPENCLAW_ROOT` is set to a typo path (e.g., `~/.openclaaw`). The directory is created; subsequent operations still fail because it's empty.

**Why it happens:** Auto-create is unconditional when env var is set.

**How to avoid:** This is acceptable per the locked decision. The operator set the env var explicitly; creating the directory is the correct first-run behaviour. The subsequent failure (no `openclaw.json`) produces a clear error.

---

## Code Examples

### Migration: Detecting and Removing Unknown Fields

```python
# Source: inferred from existing validate_openclaw_config() in config_validator.py

def _collect_unknown_fields(config: dict, validator_result_warnings: list) -> list[str]:
    """Extract field names from additionalProperties warning messages."""
    # Warnings from validate_openclaw_config() have format:
    # "openclaw.json contains unknown field 'fieldname'"
    unknown = []
    for w in validator_result_warnings:
        # Extract field name after last single quote
        if "unknown field" in w:
            parts = w.rsplit("'", 2)
            if len(parts) >= 2:
                unknown.append(parts[-2])
    return unknown

def _migrate_openclaw_config(config: dict) -> tuple[dict, list[str]]:
    """Remove unknown fields from an openclaw.json dict.

    Returns (migrated_config, list_of_changes).
    """
    from openclaw.config_validator import validate_openclaw_config
    fatal, warnings = validate_openclaw_config(config, "<migration>")

    if fatal:
        raise MigrationError(fatal)  # cannot auto-fix

    changes = []
    migrated = dict(config)
    for field in _collect_unknown_fields(config, warnings):
        del migrated[field]
        changes.append(f"  - removed unknown field: '{field}'")

    return migrated, changes
```

### Backup Before Write

```python
import shutil
from pathlib import Path

def _backup_and_write(config_path: Path, migrated: dict) -> None:
    """Write migrated config, always backing up the original first."""
    bak_path = config_path.with_suffix(config_path.suffix + ".bak")
    shutil.copy2(config_path, bak_path)
    with open(config_path, "w") as f:
        json.dump(migrated, f, indent=2, ensure_ascii=False)
        f.write("\n")  # trailing newline convention
```

### Dry-Run Output Format

```
Dry run — no files modified.

openclaw.json:
  - removed unknown field: '_schema_version'
  - removed unknown field: 'old_gateway_config'
  Run without --dry-run to apply.

projects/pumplai/project.json:
  Already up-to-date.

projects/smartai/project.json:
  - removed unknown field: 'legacy_ci'
  Run without --dry-run to apply.
```

### Applied Output Format

```
Migrated config/openclaw.json: 2 field(s) removed. Backup saved to config/openclaw.json.bak

projects/pumplai/project.json: Already up-to-date.

Migrated projects/smartai/project.json: 1 field(s) removed. Backup saved to projects/smartai/project.json.bak
```

### Adding `migrate` Subparser to cli/config.py

```python
# In main():
migrate_parser = subparsers.add_parser(
    "migrate",
    help="Upgrade openclaw.json and all project.json files to the current schema",
)
migrate_parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Print what would change without modifying any files",
)

# In the dispatch block:
if args.command == "migrate":
    sys.exit(cmd_migrate(args))
```

### config.py: get_active_project_env()

```python
def get_active_project_env() -> str | None:
    """Return the OPENCLAW_PROJECT env var value, or None if not set.

    Part of the env var precedence chain:
    OPENCLAW_ROOT → OPENCLAW_PROJECT → OPENCLAW_LOG_LEVEL → OPENCLAW_ACTIVITY_LOG_MAX

    The file-based fallback (openclaw.json active_project) is handled by
    project_config.get_active_project_id().
    """
    return os.environ.get("OPENCLAW_PROJECT") or None
```

### openclaw-config --help env var epilog

```python
parser = argparse.ArgumentParser(
    description="OpenClaw Config Tools",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
Environment variables (override config file values):
  OPENCLAW_ROOT             Project root directory (default: ~/.openclaw)
  OPENCLAW_PROJECT          Active project ID (default: openclaw.json active_project)
  OPENCLAW_LOG_LEVEL        Log verbosity: DEBUG|INFO|WARNING|ERROR (default: INFO)
  OPENCLAW_ACTIVITY_LOG_MAX Max activity log entries per task (default: 100)
  OPENCLAW_STATE_FILE       Workspace state file path (L3 containers only)
""",
)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `os.environ` reads scattered across modules | All reads centralised in `config.py` | Phase 45 (partial) | Uniform override behaviour |
| `OPENCLAW_PROJECT` read directly in `project_config.py` | Will move to `config.py` in Phase 47 | Phase 47 | Closes the last scatter |
| No migration tooling | `openclaw config migrate` | Phase 47 | Operators can upgrade without hand-editing |
| `OPENCLAW_ROOT` missing dir → runtime failure | `OPENCLAW_ROOT` missing dir → auto-create | Phase 47 | Cleaner first-run experience |

---

## Open Questions

1. **`_comment_*` key extraction in warnings**
   - What we know: `validate_openclaw_config()` produces a single warning string for ALL unknown fields combined (`"Additional properties are not allowed ('_comment', '_schema_version' were unexpected)"`)
   - What's unclear: The current warning message is a single concatenated string from jsonschema, not one warning per field. The migration code needs to parse this string or call `iter_errors()` directly to get individual field names.
   - Recommendation: Call `Draft202012Validator.iter_errors()` directly in `_migrate_openclaw_config()` (not via `validate_openclaw_config()`) to get one error per unknown field. This gives clean field names without string parsing.

2. **`openclaw.json.example` `_comment_*` vs `//` comments**
   - What we know: The example currently uses `_comment_*` JSON keys (not real comments). JSON does not support `//` comments.
   - What's unclear: The CONTEXT.md says "inline comments on each overridable field" — but JSON can't have `//` comments.
   - Recommendation: The existing `_comment_*` pattern is correct. Add env var override info to those `_comment_*` strings. No actual `//` comment syntax.

---

## Sources

### Primary (HIGH confidence)

- Direct codebase inspection — `packages/orchestration/src/openclaw/config.py` — current env var reads, resolver functions
- Direct codebase inspection — `packages/orchestration/src/openclaw/project_config.py` — confirmed `OPENCLAW_PROJECT` scatter at line 95
- Direct codebase inspection — `packages/orchestration/src/openclaw/config_validator.py` — schema validator behaviour, warning message format
- Direct codebase inspection — `packages/orchestration/src/openclaw/cli/config.py` — existing `show` subcommand pattern, `main()` structure
- Direct codebase inspection — `packages/orchestration/pyproject.toml` — confirmed `openclaw-config` entrypoint, no new entry needed
- Runtime verification — `validate_openclaw_config()` on live config → 0 fatals, 0 warnings (config currently valid)
- Runtime verification — `OPENCLAW_LOG_LEVEL=DEBUG` set before import → `LOG_LEVEL` reflects env var (module-level constant works correctly)
- Runtime verification — `validate_openclaw_config()` on `openclaw.json.example` → all `_comment_*` keys produce single combined warning, not individual warnings per field
- Direct inspection — 9 real `project.json` files → all pass schema validation; no known-bad fields to migrate in the real dataset
- Direct inspection — `docker/l3-specialist/entrypoint.sh` → confirmed `OPENCLAW_STATE_FILE` is set by spawner; Python side already reads it in `get_state_path()`

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all stdlib, no new dependencies, existing patterns confirmed
- Architecture: HIGH — exact file locations and line numbers identified from live codebase inspection
- Pitfalls: HIGH — pitfalls from runtime verification (warning message format, module-level evaluation)

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (stable — no external dependencies change)
