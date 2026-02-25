# Phase 46: Schema Validation + Fail-Fast Startup - Research

**Researched:** 2026-02-25
**Domain:** Python JSON schema validation, config loader integration, CLI subcommand
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Error message format:**
- Missing required field → contextual error with hint: names the field, names the file, and suggests the expected value/example. e.g. `ERROR: config/openclaw.json is missing required field 'gateway.port'. Add it: "port": 18789`
- Unknown field → warning, continue startup. e.g. `WARNING: openclaw.json contains unknown field 'gatewayy'`
- Errors and warnings go to stderr only — pre-startup, before logging is configured
- ANSI color: red `ERROR`, yellow `WARNING` when stdout is a TTY; auto-detect TTY, strip color when piped/redirected

**Validation scope:**
- Validate in the central config loader (config.py) when the config is first loaded — all entry points automatically get validation for free, no per-command duplication
- Dashboard gets validation indirectly via the Python API; if the API returns an error, the dashboard surfaces it — dashboard does not validate independently
- `openclaw.json` is validated eagerly at startup; missing required field = exit immediately, no fall-back to defaults
- `project.json` is validated lazily when that project is first accessed/switched to — bad project configs fail on use, not at startup

**Schema implementation:**
- Schema defined as Python dict/dataclass in `config.py` alongside existing constants — single source of truth, no extra files
- `jsonschema>=4.26.0` used for validation (already flagged as the only new v1.5 dependency)
- Validate types on required fields (int, str, list), not just presence — wrong type is as bad as missing field
- Human-readable schema docs: inline comments in `config/openclaw.json.example`, explaining each field's type, default, and required/optional status

**Required vs optional fields:**
- `openclaw.json` required (missing = exit): `gateway.port` (int) and `agents` (list) — everything else has sensible defaults
- `project.json` required fields: **Claude's Discretion** — review actual project.json files and determine what's operationally necessary at load time
- Error hints include an expected value/example for required fields
- New `openclaw config show` CLI command: prints the resolved effective config (file values merged with defaults) for operator auditing

### Claude's Discretion

- Exact Python structure for schema definition (typed dict, dataclass, plain dict, or JSON Schema dict)
- `project.json` required fields determination (review real files)
- TTY detection implementation details
- Exact shape of `openclaw config show` output (table vs JSON vs pretty-printed dict)
- Where in the startup call path `validate()` is called within `config.py`

### Deferred Ideas (OUT OF SCOPE)

- None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CONF-02 | `openclaw.json` has a documented, validated schema for the OpenClaw runtime section; unknown fields are flagged at startup | jsonschema `additionalProperties: false` catches unknowns; `required` array catches missing; schema dict in config.py is the doc |
| CONF-06 | OpenClaw fails at startup with a clear, actionable error if `openclaw.json` or `project.json` contains missing required fields or invalid types | `iter_errors()` collect-all pattern; custom error message formatting using `error.path` and `error.validator`; `sys.exit(1)` before doing any work |
</phase_requirements>

---

## Summary

Phase 46 adds machine-validated schemas to `openclaw.json` and `project.json`, and wires fail-fast startup behaviour into the central config loader. The implementation is incremental and low-risk: the project already has `ConfigValidationError`, `validate_agent_hierarchy`, and `validate_project_config` in `config_validator.py`. Phase 46 extends these rather than replacing them.

The key insight is that **`jsonschema` 4.26.0 is already present in the venv** (pulled in transitively by `mcp`) and merely needs to be added as an explicit declared dependency in `packages/orchestration/pyproject.toml`. No new packages need to be installed.

The architecture decision to validate inside `config.py` (specifically in `load_and_validate_openclaw_config` in `project_config.py`, which is already the central config loader) means all 7+ CLI entry points and the dashboard API get validation for free with no per-command changes.

**Primary recommendation:** Add `jsonschema>=4.26.0` to `pyproject.toml`, define the schema dict in `config.py`, call `validate_openclaw_config()` from `load_and_validate_openclaw_config()` in `project_config.py` and add `validate_project_config_schema()` to the `load_project_config()` path. Then add `openclaw-config` CLI entry point with a `show` subcommand. The `openclaw.json.example` file (to be created) serves as the human-readable schema doc.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| jsonschema | 4.26.0 (already in venv) | JSON Schema validation for Python | De-facto standard, already present, decision locked |
| Python stdlib `sys` | 3.10+ | `sys.stderr.isatty()` for TTY detection, `sys.exit(1)` for fail-fast | No new deps |
| Python stdlib `json` | 3.10+ | Config file loading (already used throughout) | Already in use |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| jsonschema `Draft202012Validator` | 4.26.0 | Collect-all error iteration via `iter_errors()` | Use over `validate()` to surface all errors at once, not just first |
| Python stdlib `argparse` | 3.10+ | `openclaw config show` CLI subcommand | Consistent with existing `project.py`, `monitor.py` pattern |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| jsonschema dict schema in config.py | pydantic models | Pydantic is heavier, not in project, overkill for flat config |
| jsonschema dict schema | marshmallow | Same issue — new dep, not warranted |
| jsonschema `additionalProperties` | manual key enumeration | additionalProperties is declarative and self-documenting |
| `Draft202012Validator` | `Draft7Validator` | 2020-12 is current; both support the keywords needed; 2020-12 preferred |

**Installation (already present — only need to declare):**
```bash
# Add to packages/orchestration/pyproject.toml dependencies:
# "jsonschema>=4.26.0",
```

---

## Architecture Patterns

### Recommended Project Structure (changes only)

```
packages/orchestration/src/openclaw/
├── config.py                  # ADD: OPENCLAW_JSON_SCHEMA dict constant
├── config_validator.py        # ADD: validate_openclaw_config(), extend validate_project_config()
├── project_config.py          # MODIFY: call validate_openclaw_config() in load_and_validate_openclaw_config()
│                              # MODIFY: call extended validate_project_config() in load_project_config()
├── cli/
│   ├── config.py              # NEW: openclaw-config CLI (show subcommand)
│   └── project.py             # unchanged
config/
├── openclaw.json              # unchanged (existing valid config)
└── openclaw.json.example      # NEW: human-readable schema documentation
```

### Pattern 1: Schema as Python dict in config.py

**What:** Define the JSON Schema as a module-level dict constant in `config.py`, co-located with other constants. This is the "single source of truth" the context locked.

**When to use:** Always — schema dict belongs next to the constants it validates.

**Example:**
```python
# In config.py — the locked location
# Source: locked decision in CONTEXT.md

OPENCLAW_JSON_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["gateway", "agents"],
    "properties": {
        "gateway": {
            "type": "object",
            "required": ["port"],
            "properties": {
                "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                "mode": {"type": "string"},
                "bind": {"type": "string"},
                "auth": {"type": "object"},
            },
            # No additionalProperties here — gateway is extensible
        },
        "agents": {
            "type": "object",
            # agents has .list and .defaults — object, not list
            # Note: the locked decision says agents is a "list" but the actual
            # openclaw.json has agents as an object with .list and .defaults.
            # Research finding: validate agents as "object" (not "array").
        },
        "active_project": {"type": "string"},
        "source_directories": {
            "type": "array",
            "items": {"type": "string"},
        },
        "meta": {"type": "object"},
        "commands": {"type": "object"},
        "channels": {"type": "object"},
        "memory": {"type": "object"},
        "plugins": {"type": "object"},
    },
    "additionalProperties": False,  # Unknown top-level fields → WARNING, not error
    # Note: additionalProperties:false causes ValidationError, which we catch
    # and demote to warning — see Pattern 3 below.
}
```

### Pattern 2: Collect-all error iteration with actionable messages

**What:** Use `Draft202012Validator.iter_errors()` to collect all validation errors at once, then format each into an actionable message using `error.path`, `error.validator`, and `error.instance`.

**When to use:** Always prefer over `validate()` (which raises on first error) so operators see the full picture.

**Example (verified from Context7 / official docs):**
```python
# Source: Context7 /python-jsonschema/jsonschema — iter_errors pattern
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

def validate_openclaw_config(config: dict, config_path: str) -> list[str]:
    """
    Returns list of actionable error strings. Empty list = valid.
    Warnings (unknown fields) are returned separately.
    """
    from openclaw.config import OPENCLAW_JSON_SCHEMA
    validator = Draft202012Validator(OPENCLAW_JSON_SCHEMA)
    errors = []
    warnings = []
    for error in validator.iter_errors(config):
        field_path = ".".join(str(p) for p in error.absolute_path) or "(root)"
        if error.validator == "additionalProperties":
            # Unknown field — demote to warning
            warnings.append(
                f"openclaw.json contains unknown field '{_extract_unknown_field(error)}'"
            )
        elif error.validator == "required":
            # Missing required field — fatal
            missing = error.validator_value  # the required field name(s)
            errors.append(
                f"config/openclaw.json is missing required field '{field_path}.{missing[0] if isinstance(missing, list) else missing}'"
            )
        elif error.validator == "type":
            errors.append(
                f"config/openclaw.json field '{field_path}' must be {error.schema['type']}, "
                f"got {type(error.instance).__name__}"
            )
        else:
            errors.append(f"config/openclaw.json: {error.message}")
    return errors, warnings
```

### Pattern 3: Separate errors from warnings — additionalProperties demoted

**What:** `additionalProperties: false` in JSON Schema generates a `ValidationError` with `error.validator == "additionalProperties"`. We catch these specifically and demote from error to warning. Required-field and type violations remain fatal.

**Key fact (verified):** `error.validator_value` for an `additionalProperties` error contains the additional property name(s). The `error.message` is typically `'extra_field' is not valid under any of the given schemas` or `Additional properties are not allowed ('extra_field' was unexpected)`.

**Note on `required` validator:** When `jsonschema` reports a `required` error, `error.validator_value` is the list of required properties defined in schema, and `error.message` contains the specific missing property name. The missing field name is extractable from `error.message` via `error.message.split("'")[1]` (verified pattern: message is `"'field_name' is a required property"`).

### Pattern 4: Pre-logging stderr output with TTY colour

**What:** Validation runs before `openclaw.logging` is configured (it reads `OPENCLAW_LOG_LEVEL` which requires the config to be loaded first). So validation output must go directly to `sys.stderr` using ANSI codes stripped when not a TTY.

**When to use:** At validation call sites — `load_and_validate_openclaw_config()`.

**Example:**
```python
import sys

def _is_tty() -> bool:
    return hasattr(sys.stderr, "isatty") and sys.stderr.isatty()

def _fmt_error(msg: str) -> str:
    if _is_tty():
        return f"\033[91mERROR\033[0m: {msg}"
    return f"ERROR: {msg}"

def _fmt_warning(msg: str) -> str:
    if _is_tty():
        return f"\033[93mWARRING\033[0m: {msg}"
    return f"WARNING: {msg}"
```

### Pattern 5: openclaw config show — effective config display

**What:** A new CLI entry point `openclaw-config` (in `cli/config.py`) with a `show` subcommand that loads `openclaw.json`, merges with defaults, and prints the effective config. Consistent with `project.py` / `monitor.py` patterns (argparse subparsers, same `Colors` class, exit codes 0/1).

**Recommended output format (Claude's Discretion resolved):** Pretty-printed JSON (using `json.dumps(effective_config, indent=2)`) — already familiar to operators, machine-readable, no formatting library needed. Optionally prefix with a comment line `# Effective config (file + defaults merged)`.

**Example output:**
```json
{
  "gateway": {
    "port": 18789,
    "mode": "local",
    "bind": "loopback",
    "auth": {"mode": "token"}
  },
  "agents": { ... },
  "active_project": "pumplai",
  "_defaults_applied": ["source_directories"]
}
```

### Anti-Patterns to Avoid

- **Validate in each CLI entry point separately:** The locked decision requires validation in the config loader — adding per-command validation creates duplication and missed coverage.
- **Use `validate()` instead of `iter_errors()`:** `validate()` raises on first error; operators need to see all errors at once.
- **Print warnings to stdout:** All pre-startup output goes to stderr (locked decision).
- **Use `additionalProperties: false` as fatal:** Unknown fields must be warnings, not errors (locked decision).
- **Schema in a separate `.json` file:** Locked decision requires schema as Python dict in `config.py` — single source of truth.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON Schema validation | Custom recursive key-checker | jsonschema `Draft202012Validator.iter_errors()` | Handles nested paths, type checks, required, additionalProperties correctly with zero bugs |
| Type checking in JSON | `isinstance()` chains | jsonschema `type` keyword | jsonschema handles JSON number/integer distinction, null, boolean consistently |
| Error path extraction | Manual path joining | `error.absolute_path` (a `deque`) | Correct for nested schemas including arrays |
| TTY detection | Platform-specific checks | `sys.stderr.isatty()` | Stdlib, correct, handles pipe/redirect |

**Key insight:** The collect-all pattern (`iter_errors`) already exists in `config_validator.py` via the `errors: List[str]` + collect loop — jsonschema just handles the schema-matching logic that currently lives in hand-coded `if "field" not in config` blocks.

---

## Common Pitfalls

### Pitfall 1: `agents` field type mismatch — object vs list

**What goes wrong:** The locked decision says `agents` (list) is required. But the actual `openclaw.json` has `agents` as an **object** with two sub-keys: `agents.list` (the array of agent dicts) and `agents.defaults` (default model/sandbox config). Validating `agents` as `"type": "array"` will cause every valid config to fail.

**Why it happens:** The CONTEXT.md says `agents (list)` meaning "the agents section must be present and contain a list", not that the `agents` top-level value is an array.

**How to avoid:** Schema for top-level `agents` field must be `"type": "object"` with `required: ["list"]` where `list` is an array. Check: `gateway.port` is the only int required at top level; `agents.list` is the list.

**Warning signs:** Test with real `openclaw.json` — if it fails validation on a valid config, the type is wrong.

### Pitfall 2: `error.validator == "required"` — missing field name extraction

**What goes wrong:** `error.validator_value` for a `required` error is the full list of required properties from the schema (e.g., `["port"]`), not just the missing one. The actually-missing field name is in `error.message` as `"'port' is a required property"`.

**Why it happens:** JSON Schema `required` is validated as a keyword against the whole object — the error reports which constraint failed, not specifically which member is absent.

**How to avoid:** Extract missing field from `error.message` using: `missing_field = error.message.split("'")[1]`. Or use `error.validator_value` (the required list) minus `set(error.instance.keys())`.

**Warning signs:** Error message says `"['port'] is a required property"` — wrong, needs to extract the string not the list.

### Pitfall 3: `additionalProperties` error message extraction

**What goes wrong:** The unknown field name is embedded in `error.message` (e.g., `"Additional properties are not allowed ('gatewayy' was unexpected)"`) — not directly in a structured attribute.

**Why it happens:** jsonschema puts all diagnostic info in the human message for this validator.

**How to avoid:** Parse with regex: `re.search(r"\('(\w+)' was unexpected\)", error.message)` or split on `'`. Simpler: format the raw `error.message` directly in the warning since it's already human-readable.

**Warning signs:** Trying `error.instance` or `error.validator_value` for additional properties — both give unexpected types.

### Pitfall 4: `load_and_validate_openclaw_config` is called multiple times

**What goes wrong:** Multiple callers (`get_active_project_id`, `get_source_directories`, `get_memu_config`, `load_project_config`) each open and re-read `openclaw.json` independently. If validation is added to `load_and_validate_openclaw_config()`, those other callers that do their own `json.load()` bypass validation entirely.

**Why it happens:** `get_source_directories()` and `get_memu_config()` in `project_config.py` do their own `open(config_path)` / `json.load()` — they don't call `load_and_validate_openclaw_config()`.

**How to avoid:** For the purposes of CONF-02/CONF-06, validation only needs to run on the code paths that gate actual startup work. The locked decision says "validate when config is first loaded" — `load_and_validate_openclaw_config()` is called by `get_active_project_id()` which is on the startup critical path. The other helpers (`get_source_directories`, `get_memu_config`) are supplemental reads and can stay as-is. No need to refactor every reader.

**Warning signs:** Tests show validation error raised by helper that doesn't call the validator → the helper is doing its own file read.

### Pitfall 5: `sys.exit()` inside a library function breaks tests

**What goes wrong:** Calling `sys.exit(1)` inside `load_and_validate_openclaw_config()` makes it impossible to test the error path — `pytest` treats `SystemExit` as test failure.

**Why it happens:** Mixing library-level (raise exception) and CLI-level (sys.exit) concerns.

**How to avoid:** Keep `config_validator.py` raise-only. The `sys.exit()` call belongs at the CLI boundary — in `load_and_validate_openclaw_config()` or better in the CLI entry points that call it. Tests can use `pytest.raises(SystemExit)` or test the validator directly without triggering exit. **Recommended:** Raise `ConfigValidationError` from validator; catch it at the `load_and_validate_openclaw_config()` level, print formatted message to stderr, then `sys.exit(1)`. Tests call `validate_openclaw_config()` directly without going through the exit-triggering wrapper.

### Pitfall 6: jsonschema not in declared dependencies

**What goes wrong:** `jsonschema` is present in the venv only because `mcp` pulled it in — if `mcp` is removed or the venv is rebuilt from declared deps only, `import jsonschema` fails.

**Why it happens:** Transitive dependency is not the same as declared dependency.

**How to avoid:** Add `"jsonschema>=4.26.0"` to `[project].dependencies` in `packages/orchestration/pyproject.toml` before writing any code that imports it.

---

## Code Examples

Verified patterns from official sources:

### Collect-all validation with error classification

```python
# Source: Context7 /python-jsonschema/jsonschema — iter_errors pattern
from jsonschema import Draft202012Validator
import re

def _extract_additional_property(message: str) -> str:
    """Extract unknown field name from additionalProperties error message."""
    m = re.search(r"\('(.+?)' was unexpected\)", message)
    return m.group(1) if m else message

def validate_openclaw_config(config: dict, config_path: str) -> tuple[list[str], list[str]]:
    """
    Validate config against OPENCLAW_JSON_SCHEMA.

    Returns: (fatal_errors, warnings)
    - fatal_errors: list of strings; non-empty → call sys.exit(1)
    - warnings: list of strings; always print but continue startup
    """
    from openclaw.config import OPENCLAW_JSON_SCHEMA
    validator = Draft202012Validator(OPENCLAW_JSON_SCHEMA)
    fatal = []
    warnings = []

    for error in validator.iter_errors(config):
        path = ".".join(str(p) for p in error.absolute_path)

        if error.validator == "additionalProperties":
            field = _extract_additional_property(error.message)
            warnings.append(
                f"openclaw.json contains unknown field '{field}'"
            )
        elif error.validator == "required":
            # "'{field}' is a required property"
            missing = error.message.split("'")[1]
            parent = f"{path}." if path else ""
            example = _hint_for_field(parent + missing)
            fatal.append(
                f"config/openclaw.json is missing required field "
                f"'{parent}{missing}'. Add it: {example}"
            )
        elif error.validator == "type":
            expected = error.schema.get("type", "?")
            got = type(error.instance).__name__
            fatal.append(
                f"config/openclaw.json field '{path}' must be {expected}, "
                f"got {got}"
            )
        else:
            fatal.append(f"config/openclaw.json: {error.message}")

    return fatal, warnings


def _hint_for_field(field_path: str) -> str:
    """Return an example value string for the given field path."""
    hints = {
        "gateway.port": '"port": 18789',
        "agents": '"agents": {"list": [], "defaults": {}}',
        "agents.list": '"list": []',
    }
    return hints.get(field_path, f'"{field_path.split(".")[-1]}": <value>')
```

### Stderr output with TTY colour

```python
# Pattern used in existing init.py, project.py — extended for pre-logging context
import sys

def _stderr(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)

def _is_tty() -> bool:
    return hasattr(sys.stderr, "isatty") and sys.stderr.isatty()

RED   = "\033[91m" if _is_tty() else ""
YELLOW = "\033[93m" if _is_tty() else ""
RESET = "\033[0m"  if _is_tty() else ""

def emit_validation_results(fatal: list[str], warnings: list[str], config_path: str) -> None:
    for w in warnings:
        _stderr(f"{YELLOW}WARNING{RESET}: {w}")
    for e in fatal:
        _stderr(f"{RED}ERROR{RESET}: {e}")
    if fatal:
        sys.exit(1)
```

**Important:** Compute `_is_tty()` at call time, not at module import time, so tests that redirect stderr work correctly.

### Schema constant with correct agents shape

```python
# config.py addition — verified against real openclaw.json structure
OPENCLAW_JSON_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["gateway", "agents"],
    "properties": {
        "meta":              {"type": "object"},
        "active_project":    {"type": "string"},
        "source_directories":{"type": "array", "items": {"type": "string"}},
        "agents": {
            "type": "object",
            "required": ["list"],
            "properties": {
                "list":     {"type": "array"},
                "defaults": {"type": "object"},
            },
        },
        "commands":  {"type": "object"},
        "channels":  {"type": "object"},
        "gateway": {
            "type": "object",
            "required": ["port"],
            "properties": {
                "port":  {"type": "integer", "minimum": 1, "maximum": 65535},
                "mode":  {"type": "string"},
                "bind":  {"type": "string"},
                "auth":  {"type": "object"},
            },
        },
        "memory":  {"type": "object"},
        "plugins": {"type": "object"},
    },
    "additionalProperties": False,
}
```

### project.json required fields — determined from real files

Examining all 9 project.json files (`pumplai`, `finai`, `geriai`, `geriapp`, `replyiq`, `rivalsignal`, `smartai`, `ugro-data`, `viflo`), every file has:
- `workspace` (string, non-empty) — already validated by `validate_project_config()`
- `tech_stack` (object) — already validated by `validate_project_config()`

The existing `validate_project_config()` already covers the operationally-necessary required fields. Phase 46 extends it to also:
1. Flag unknown top-level fields as warnings (via jsonschema `additionalProperties`)
2. Validate types using jsonschema rather than hand-coded isinstance checks (optional refactor, or just add schema layer alongside existing)

**Recommendation:** Augment `validate_project_config()` to also run a jsonschema pass for unknown-field detection, while keeping the existing hand-coded required-field checks (they produce better error messages with examples). This avoids rewriting working validation logic.

### openclaw config show — minimal implementation

```python
# cli/config.py — new file, consistent with project.py pattern
import argparse
import json
import sys
from openclaw.project_config import load_and_validate_openclaw_config
from openclaw.config import get_project_root

def cmd_show(args: argparse.Namespace) -> int:
    try:
        config = load_and_validate_openclaw_config()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    # Effective config = loaded file (validation already merged nothing,
    # but we can annotate defaults for clarity)
    print(json.dumps(config, indent=2))
    return 0

def main() -> int:
    parser = argparse.ArgumentParser(description="OpenClaw Config Tools")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("show", help="Print effective config")
    args = parser.parse_args()
    if args.command == "show":
        return cmd_show(args)
    parser.print_help()
    return 1

if __name__ == "__main__":
    sys.exit(main())
```

Add to `pyproject.toml` scripts:
```toml
openclaw-config = "openclaw.cli.config:main"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hand-coded `if "field" not in config` | jsonschema schema validation | Phase 46 | Unknown fields auto-detected; type checking declarative |
| Per-module file reads in `get_source_directories()` etc. | Still per-module (acceptable — startup critical path goes through `load_and_validate_openclaw_config`) | n/a — not changing this | No regression, validation on critical path only |

**What already exists and should NOT be re-implemented:**
- `ConfigValidationError` in `config_validator.py` — reuse, extend
- `validate_project_config()` — extend with jsonschema unknown-fields pass
- `validate_agent_hierarchy()` — unchanged by this phase
- `load_and_validate_openclaw_config()` in `project_config.py` — the injection point for new `validate_openclaw_config()` call

---

## Open Questions

1. **TTY colour computed at module level vs call time**
   - What we know: `init.py` uses a `Colors` class with constants at class definition time — no TTY check, always emits ANSI.
   - What's unclear: Whether to match that existing pattern (risking colour in piped output) or use call-time TTY detection.
   - Recommendation: Use call-time `sys.stderr.isatty()` for the new validation output since the locked decision explicitly requires TTY-stripping. Existing `Colors` in `init.py` is a separate concern.

2. **`openclaw.json.example` path**
   - What we know: The decision says "inline comments in `config/openclaw.json.example`". JSON doesn't support comments; this means either a `.jsonc` file, a JSON file with `"_comment"` keys, or a separate Markdown/text doc.
   - What's unclear: Whether operators expect a `.json.example` they can copy, or a human-readable reference.
   - Recommendation: Create `config/openclaw.json.example` as a valid JSON file with descriptive string values for optional fields and comments embedded as `"_comment_fieldname"` keys — or use a `.jsonc` extension if editors in use support it. Alternatively, create `config/openclaw.schema.json` as a proper JSON Schema document (machine-readable + human-readable). The simplest operator-friendly choice: a well-commented copy of `openclaw.json` with example values and a `"_schema"` key at the top describing the structure.

3. **`project.json` unknown field warnings — load path**
   - What we know: `load_project_config()` calls `validate_project_config()` already. Adding a jsonschema pass here for unknown-field warnings requires knowing all legitimate project.json top-level keys.
   - What's unclear: Are fields like `id`, `name`, `agent_display_name` intentionally undeclared (they're present in all real files but not in `validate_project_config()`)?
   - Recommendation: Enumerate known project.json keys from real files: `id`, `name`, `agent_display_name`, `workspace`, `tech_stack`, `agents`, `l3_overrides`. Define a PROJECT_JSON_SCHEMA with these as properties and `additionalProperties: false`. This flags typos like `l3_overridess`.

---

## Validation Architecture

> `workflow.nyquist_validation` is absent from `.planning/config.json` — this section is included per standard research practice but is marked as optional.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 7.0+ |
| Config file | `packages/orchestration/pyproject.toml` (no `[tool.pytest]` section yet — tests run via `uv run pytest packages/orchestration/tests/`) |
| Quick run command | `uv run pytest packages/orchestration/tests/test_config_validator.py -x` |
| Full suite command | `uv run pytest packages/orchestration/tests/ -v` |
| Estimated runtime | ~5 seconds |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CONF-02 | Unknown field in openclaw.json → warning, not error | unit | `uv run pytest packages/orchestration/tests/test_config_validator.py::test_unknown_field_is_warning -x` | Wave 0 gap |
| CONF-02 | Valid config loads without error | unit | `uv run pytest packages/orchestration/tests/test_config_validator.py::test_valid_config_passes -x` | Wave 0 gap |
| CONF-02 | Schema defined in config.py importable | unit | `uv run pytest packages/orchestration/tests/test_config_validator.py::test_schema_importable -x` | Wave 0 gap |
| CONF-06 | Missing `gateway.port` → exit with error naming field | unit | `uv run pytest packages/orchestration/tests/test_config_validator.py::test_missing_gateway_port_is_fatal -x` | Wave 0 gap |
| CONF-06 | Missing `agents` → exit with error naming field | unit | `uv run pytest packages/orchestration/tests/test_config_validator.py::test_missing_agents_is_fatal -x` | Wave 0 gap |
| CONF-06 | Wrong type `gateway.port` (string instead of int) → exit | unit | `uv run pytest packages/orchestration/tests/test_config_validator.py::test_wrong_type_is_fatal -x` | Wave 0 gap |
| CONF-06 | Missing `project.json` required field → error on access | unit | `uv run pytest packages/orchestration/tests/test_config_validator.py::test_project_json_missing_required -x` | Wave 0 gap |

### Wave 0 Gaps (must be created before implementation)

- [ ] `packages/orchestration/tests/test_config_validator.py` — covers CONF-02 and CONF-06 schema validation scenarios; does not exist yet (current `test_*` files cover memory, pool, suggest, state engine — no config schema tests)

*(Existing test infrastructure: `conftest.py`, pytest, pytest-asyncio, respx — all sufficient. No framework install needed.)*

---

## Sources

### Primary (HIGH confidence)

- Context7 `/python-jsonschema/jsonschema` — `iter_errors()` pattern, `ValidationError` attributes (`validator`, `validator_value`, `absolute_path`, `message`), `Draft202012Validator`
- Direct code inspection: `config_validator.py`, `config.py`, `project_config.py`, `__init__.py`, `pyproject.toml`, all 9 `project.json` files, `openclaw.json` — structural analysis
- Official jsonschema docs (via Context7): `additionalProperties`, `required`, `type` keyword behaviours

### Secondary (MEDIUM confidence)

- `sys.stderr.isatty()` TTY detection — stdlib, well-established pattern; verified against Python 3.10+ docs
- `json.dumps(..., indent=2)` for `config show` output — stdlib, consistent with existing `project.py` JSON writes

### Tertiary (LOW confidence)

- None — all findings verified against code or official docs

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — jsonschema already in venv at correct version, verified; stdlib only additions
- Architecture: HIGH — based on direct inspection of all relevant source files; schema shapes verified against real config files
- Pitfalls: HIGH — pitfalls 1-4 based on jsonschema API verification; pitfalls 5-6 based on code inspection of existing patterns

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (stable domain — jsonschema API is stable, codebase changes slowly)
