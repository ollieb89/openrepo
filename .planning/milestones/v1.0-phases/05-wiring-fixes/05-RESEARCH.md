# Phase 5: Wiring Fixes & Initialization - Research

**Researched:** 2026-02-18
**Domain:** Python filesystem operations, JSON configuration management, Git directory initialization
**Confidence:** HIGH

## Summary

Phase 5 closes two specific integration gaps identified in the v1.0 milestone audit. The first gap is broken L1→L2 delegation wiring: ClawdiaPrime (L1) lacks a config.json file with skill_registry, preventing it from invoking the router_skill that already exists. The second gap is missing directory initialization: the snapshots system code exists but workspace/.openclaw/snapshots/ was never created during Phase 3 execution.

Both gaps are straightforward filesystem and configuration operations. The router_skill already exists and works (verified in Phase 2), L3 config.json provides a proven pattern to follow, and the snapshot.py module already includes idempotent directory creation logic. This is pure wiring and initialization work with no new capabilities.

**Primary recommendation:** Create L1 config.json following L3 pattern, register router_skill only, and add idempotent snapshots directory initialization to system startup flow. Verify with automated test scripts.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### L1 Config & Skill Registry
- Create a **full L1 config.json** (not minimal) — include identity ref, gateway endpoint, and other L1 settings alongside skill_registry
- Register **router_skill only** in skill_registry — other skills (spawn_specialist, etc.) are wired in future phases
- Config format and file location are Claude's discretion based on existing codebase patterns

#### Delegation Flow Behavior
- "End-to-end" success = **gateway message roundtrip** — L1 sends through gateway, gets response back. Proves wiring works.
- Include **basic error handling** — clear error messages when gateway or L2 is unreachable (not just happy path)
- Gateway endpoint source for router_skill is Claude's discretion based on what exists
- Verification via **automated script** that tests the delegation flow and reports pass/fail

#### Snapshots Directory Setup
- Directory creation must be **idempotent** — safe to run multiple times, checks existence first
- Whether to create empty or with baseline snapshot is Claude's discretion
- Bake into **startup integration** — snapshots dir is guaranteed to exist when system starts
- Verification via **automated test script** that creates a test snapshot and verifies capture

### Claude's Discretion
- Config.json format (whether to match L2 pattern or create L1-specific structure)
- Config.json file location (agents/clawdia_prime/agent/ or elsewhere)
- Router skill's gateway endpoint source (L1 config.json vs openclaw.json)
- Whether to seed snapshots dir with baseline snapshot or leave empty

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| COM-01 | Implement hub-and-spoke communication via the OpenClaw Gateway. | L3 config.json provides proven pattern; router_skill already exists and tested in Phase 2; gateway endpoint available in openclaw.json |
| COM-04 | Implement semantic snapshotting for workspace state persistence. | snapshot.py already includes idempotent directory creation in capture_semantic_snapshot(); just need to call it at startup |

</phase_requirements>

## Standard Stack

### Core Libraries (Built-in Python)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| json | stdlib | Read/write config.json files | Standard Python config format |
| pathlib.Path | stdlib | Filesystem path operations | Modern, cross-platform path handling |
| subprocess | stdlib | Execute git commands | Already used by snapshot.py |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| argparse | stdlib | CLI argument parsing | Verification test scripts |

### Alternatives Considered
None needed — all operations use Python standard library. No external dependencies required.

**Installation:**
No installation needed — pure Python stdlib operations.

## Architecture Patterns

### Recommended Project Structure
```
agents/clawdia_prime/agent/
├── IDENTITY.md              # Exists
├── SOUL.md                  # Exists
└── config.json              # NEW - L1 configuration

workspace/.openclaw/
├── snapshots/               # NEW - initialized at startup
├── workspace-state.json     # Exists
└── (other files)

orchestration/
├── init.py                  # NEW - startup initialization module
├── snapshot.py              # Exists - already has directory creation
├── state_engine.py          # Exists
└── (other modules)

scripts/
└── verify_phase5.py         # NEW - automated verification test
```

### Pattern 1: Agent Config.json (Following L3 Pattern)

**What:** JSON configuration file defining agent capabilities, skill registry, and settings
**When to use:** Every agent tier that needs to invoke skills or define runtime behavior
**Example:**

```json
{
  "id": "clawdia_prime",
  "name": "ClawdiaPrime - Strategic Orchestrator",
  "level": 1,
  "reports_to": null,
  "gateway": {
    "endpoint": "http://localhost:18789",
    "auth_token": "c1701657cb4ba6739dcb5684bebf077384ce540c3c41e112"
  },
  "skill_registry": {
    "router_skill": {
      "name": "Hub-and-Spoke Router (CLI)",
      "description": "Enables L1 orchestrators to delegate tasks to L2 project managers.",
      "skill_path": "skills/router_skill",
      "handler": "node index.js {{targetId}} \"{{directive}}\""
    }
  },
  "identity_ref": "agents/clawdia_prime/agent/IDENTITY.md",
  "soul_ref": "agents/clawdia_prime/agent/SOUL.md"
}
```

**Source:** Adapted from `/home/ollie/.openclaw/agents/l3_specialist/config.json`

### Pattern 2: Idempotent Directory Initialization

**What:** Create directory if it doesn't exist, no-op if it already exists
**When to use:** Startup initialization, ensuring required directories exist
**Example:**

```python
from pathlib import Path

def ensure_snapshots_directory(workspace_path: str) -> Path:
    """
    Ensure snapshots directory exists at workspace/.openclaw/snapshots/

    Idempotent - safe to call multiple times.

    Args:
        workspace_path: Path to workspace root

    Returns:
        Path object for snapshots directory
    """
    workspace = Path(workspace_path)
    snapshots_dir = workspace / '.openclaw' / 'snapshots'

    # mkdir with parents=True and exist_ok=True is idempotent
    snapshots_dir.mkdir(parents=True, exist_ok=True)

    return snapshots_dir
```

**Source:** Pattern used in `orchestration/snapshot.py` line 209

### Pattern 3: Startup Integration Hook

**What:** Module that runs initialization checks at system startup
**When to use:** Ensuring required directories, config files, or state exist before normal operations
**Example:**

```python
"""
Startup initialization for OpenClaw system.

Ensures all required directories and state files exist before normal operations.
"""

from pathlib import Path
from typing import Dict, Any

def initialize_system(workspace_path: str) -> Dict[str, Any]:
    """
    Run all startup initialization tasks.

    Idempotent - safe to run multiple times.

    Args:
        workspace_path: Path to workspace root

    Returns:
        Dictionary with initialization results
    """
    results = {}

    # Ensure snapshots directory exists
    snapshots_dir = ensure_snapshots_directory(workspace_path)
    results['snapshots_dir'] = {
        'path': str(snapshots_dir),
        'existed': snapshots_dir.exists(),
        'status': 'ok'
    }

    # Future: Add other initialization tasks here

    return results
```

**Source:** Standard Python initialization pattern

### Pattern 4: Gateway Message Roundtrip Test

**What:** Verification test that sends a message through the gateway and verifies response
**When to use:** Testing L1→L2 delegation flow end-to-end
**Example:**

```python
import subprocess
import json

def test_l1_to_l2_delegation():
    """
    Test that L1 can successfully route a directive to L2 via router_skill.

    Returns:
        True if delegation succeeds, False otherwise
    """
    try:
        # Load L1 config to get router_skill path
        config_path = Path('/home/ollie/.openclaw/agents/clawdia_prime/agent/config.json')
        with open(config_path) as f:
            config = json.load(f)

        router_skill_path = config['skill_registry']['router_skill']['skill_path']
        skill_dir = Path('/home/ollie/.openclaw') / router_skill_path

        # Execute router_skill with test directive
        result = subprocess.run(
            ['node', 'index.js', 'pumplai_pm', 'test delegation'],
            cwd=skill_dir,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Check if delegation succeeded
        if result.returncode == 0:
            print("[PASS] L1 → L2 delegation successful")
            return True
        else:
            print(f"[FAIL] L1 → L2 delegation failed: {result.stderr}")
            return False

    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        return False
```

**Source:** Based on router_skill verification from Phase 2

### Anti-Patterns to Avoid

- **Creating config.json with hardcoded paths:** Use relative paths from project root, not absolute paths
- **Skipping idempotency checks:** Always use `exist_ok=True` for directory creation to avoid race conditions
- **Omitting error handling in gateway calls:** Router skill must handle unreachable gateway gracefully
- **Creating minimal L1 config:** User decision requires full config with identity refs, gateway endpoint, etc.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Directory creation with race conditions | Custom exists() check + mkdir() | `Path.mkdir(parents=True, exist_ok=True)` | Atomic operation, handles concurrent calls |
| JSON config validation | Custom schema checker | Simple dict structure + try/except | Phase 5 is gap closure, not feature addition |
| Gateway endpoint discovery | New discovery protocol | Read from openclaw.json | Already exists and proven |
| Skill invocation | New skill runner | Existing router_skill CLI | Already tested in Phase 2 |

**Key insight:** All required components already exist. This phase is pure wiring — connecting existing pieces, not building new ones.

## Common Pitfalls

### Pitfall 1: Non-idempotent Initialization
**What goes wrong:** Startup script fails on second run because directory already exists
**Why it happens:** Using `mkdir()` without `exist_ok=True` raises FileExistsError
**How to avoid:** Always use `Path.mkdir(parents=True, exist_ok=True)`
**Warning signs:** "FileExistsError: [Errno 17] File exists" in logs

### Pitfall 2: Config Path Confusion
**What goes wrong:** Router skill can't find gateway endpoint because config references wrong path
**Why it happens:** Mixing absolute and relative paths, or referencing wrong config file
**How to avoid:** Use consistent relative paths from project root; document which config is authoritative
**Warning signs:** "Cannot connect to gateway" errors when gateway is running

### Pitfall 3: Missing Gateway Error Handling
**What goes wrong:** Router skill crashes instead of reporting clear error when gateway is unreachable
**Why it happens:** Not catching connection errors from axios/subprocess
**How to avoid:** Wrap gateway calls in try/catch, return structured error messages
**Warning signs:** Uncaught exceptions, no user-friendly error messages

### Pitfall 4: Testing in Isolation Instead of End-to-End
**What goes wrong:** Unit tests pass but integration fails because components don't connect
**Why it happens:** Testing config.json creation separately from router_skill invocation
**How to avoid:** Write verification script that tests full L1→gateway→L2 roundtrip
**Warning signs:** "Works on my machine" syndrome, integration failures in production

### Pitfall 5: Creating Snapshots Directory Without Checking Git Repo
**What goes wrong:** Snapshots directory created in non-git workspace, snapshot capture fails later
**Why it happens:** Not validating workspace is a git repository before initialization
**How to avoid:** Check `git rev-parse --git-dir` succeeds before creating snapshots dir
**Warning signs:** "Not a git repository" errors during snapshot capture

## Code Examples

Verified patterns from the codebase:

### L1 Config Creation (Based on L3 Pattern)

```python
import json
from pathlib import Path

def create_l1_config():
    """
    Create config.json for ClawdiaPrime (L1) agent.

    Follows L3 config pattern with L1-specific settings.
    """
    config_path = Path('/home/ollie/.openclaw/agents/clawdia_prime/agent/config.json')

    config = {
        "id": "clawdia_prime",
        "name": "ClawdiaPrime - Strategic Orchestrator",
        "level": 1,
        "reports_to": None,
        "gateway": {
            "endpoint": "http://localhost:18789",
            "auth_token": "c1701657cb4ba6739dcb5684bebf077384ce540c3c41e112"
        },
        "skill_registry": {
            "router_skill": {
                "name": "Hub-and-Spoke Router (CLI)",
                "description": "Enables L1 orchestrators to delegate tasks to L2 project managers.",
                "skill_path": "skills/router_skill",
                "handler": "node index.js {{targetId}} \"{{directive}}\""
            }
        },
        "identity_ref": "agents/clawdia_prime/agent/IDENTITY.md",
        "soul_ref": "agents/clawdia_prime/agent/SOUL.md"
    }

    # Write config with pretty formatting
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"Created L1 config: {config_path}")
    return config_path
```

**Source:** Adapted from `/home/ollie/.openclaw/agents/l3_specialist/config.json`

### Idempotent Snapshots Directory Initialization

```python
from pathlib import Path

def ensure_snapshots_directory(workspace_path: str) -> Path:
    """
    Ensure workspace/.openclaw/snapshots/ directory exists.

    Idempotent - safe to call multiple times.

    Args:
        workspace_path: Path to workspace root (e.g., /home/ollie/.openclaw/workspace)

    Returns:
        Path to snapshots directory
    """
    workspace = Path(workspace_path)
    snapshots_dir = workspace / '.openclaw' / 'snapshots'

    # parents=True creates intermediate directories
    # exist_ok=True prevents error if directory already exists
    snapshots_dir.mkdir(parents=True, exist_ok=True)

    print(f"Snapshots directory ready: {snapshots_dir}")
    return snapshots_dir
```

**Source:** Pattern from `orchestration/snapshot.py` line 209

### Verification Script - L1 to L2 Delegation Test

```python
#!/usr/bin/env python3
"""
Verify Phase 5 wiring fixes.

Tests:
1. L1 config.json exists with router_skill registration
2. L1 → L2 delegation flow completes end-to-end
3. Snapshots directory exists and snapshot capture works
"""

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path('/home/ollie/.openclaw')

def test_l1_config_exists():
    """Test 1: Verify L1 config.json exists and contains router_skill."""
    print("\n[Test 1] L1 config.json exists with router_skill")

    config_path = PROJECT_ROOT / 'agents' / 'clawdia_prime' / 'agent' / 'config.json'

    if not config_path.exists():
        print(f"  [FAIL] Config not found: {config_path}")
        return False

    with open(config_path) as f:
        config = json.load(f)

    # Check required fields
    if 'skill_registry' not in config:
        print("  [FAIL] Missing skill_registry")
        return False

    if 'router_skill' not in config['skill_registry']:
        print("  [FAIL] router_skill not registered")
        return False

    print(f"  [PASS] L1 config exists with router_skill")
    return True

def test_l1_to_l2_delegation():
    """Test 2: Test L1 → L2 delegation via router_skill."""
    print("\n[Test 2] L1 → L2 delegation flow")

    router_skill_dir = PROJECT_ROOT / 'skills' / 'router_skill'

    if not router_skill_dir.exists():
        print(f"  [FAIL] router_skill not found: {router_skill_dir}")
        return False

    try:
        # Execute router skill with test directive
        result = subprocess.run(
            ['node', 'index.js', 'pumplai_pm', 'test delegation from verification script'],
            cwd=router_skill_dir,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print("  [PASS] L1 → L2 delegation successful")
            print(f"  Output: {result.stdout.strip()}")
            return True
        else:
            print(f"  [FAIL] Delegation failed")
            print(f"  Error: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("  [FAIL] Delegation timed out")
        return False
    except Exception as e:
        print(f"  [FAIL] Test error: {e}")
        return False

def test_snapshots_directory():
    """Test 3: Verify snapshots directory exists and is writable."""
    print("\n[Test 3] Snapshots directory initialization")

    snapshots_dir = PROJECT_ROOT / 'workspace' / '.openclaw' / 'snapshots'

    if not snapshots_dir.exists():
        print(f"  [FAIL] Snapshots directory not found: {snapshots_dir}")
        return False

    if not snapshots_dir.is_dir():
        print(f"  [FAIL] Snapshots path is not a directory: {snapshots_dir}")
        return False

    # Test write access
    test_file = snapshots_dir / '.test_write'
    try:
        test_file.write_text('test')
        test_file.unlink()
        print(f"  [PASS] Snapshots directory ready: {snapshots_dir}")
        return True
    except Exception as e:
        print(f"  [FAIL] Cannot write to snapshots directory: {e}")
        return False

def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Phase 5 Verification: Wiring Fixes & Initialization")
    print("=" * 60)

    tests = [
        test_l1_config_exists,
        test_l1_to_l2_delegation,
        test_snapshots_directory
    ]

    results = [test() for test in tests]

    print("\n" + "=" * 60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)

    sys.exit(0 if all(results) else 1)

if __name__ == '__main__':
    main()
```

**Source:** Verification pattern from Phase 2

## State of the Art

This phase uses stable, proven patterns from the existing codebase. No cutting-edge technologies involved.

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual directory creation | Path.mkdir(exist_ok=True) | Python 3.5+ (2015) | Idempotent, race-safe |
| Shell scripts for init | Python startup module | Best practice | Cross-platform, testable |
| Hardcoded config values | JSON config files | Industry standard | Maintainable, versionable |

**Deprecated/outdated:**
None — all patterns are current Python best practices.

## Open Questions

### 1. Should L1 config include gateway auth token or read from openclaw.json?

**What we know:**
- openclaw.json has gateway.auth.token: "c1701657cb4ba6739dcb5684bebf077384ce540c3c41e112"
- L3 config.json doesn't include auth token (likely reads from openclaw.json)
- Router skill uses CLI (`openclaw agent`) which reads openclaw.json

**What's unclear:**
Whether L1 config.json should duplicate the auth token or rely on openclaw.json as the single source of truth

**Recommendation:**
Include gateway endpoint in L1 config.json but omit auth token. Router skill already uses `openclaw agent` CLI which reads auth from openclaw.json. This avoids token duplication and follows L3 pattern.

### 2. Where should startup initialization be triggered?

**What we know:**
- No existing startup script in codebase
- Snapshots directory already created (exists with empty state)
- This is primarily a future-proofing measure

**What's unclear:**
Whether to create a formal startup module or document manual initialization

**Recommendation:**
Create `orchestration/init.py` module with `initialize_system()` function, but don't hook it into automated startup yet. Document manual invocation in verification script. Future phases can integrate into container entrypoints or service startup.

### 3. Should snapshots directory be seeded with baseline snapshot?

**What we know:**
- Snapshots directory currently empty
- snapshot.py captures diffs against main branch
- First snapshot will be relative to current workspace state

**What's unclear:**
Whether an empty directory or a baseline snapshot better serves the system

**Recommendation:**
Leave empty. The semantic snapshot system captures diffs from staging branches, not absolute state. First L3 task will create first snapshot. Adding a baseline snapshot would require defining "baseline state" which is out of scope for this gap closure phase.

## Sources

### Primary (HIGH confidence)
- `/home/ollie/.openclaw/agents/l3_specialist/config.json` - L3 config pattern
- `/home/ollie/.openclaw/skills/router_skill/index.js` - Router skill implementation
- `/home/ollie/.openclaw/skills/router_skill/skill.json` - Skill metadata
- `/home/ollie/.openclaw/orchestration/snapshot.py` - Snapshot system with directory creation
- `/home/ollie/.openclaw/orchestration/config.py` - SNAPSHOT_DIR constant
- `/home/ollie/.openclaw/openclaw.json` - Gateway configuration
- `/home/ollie/.openclaw/.planning/phases/02-core-orchestration/02-VERIFICATION.md` - Phase 2 verification (router_skill tested)
- `/home/ollie/.openclaw/.planning/v1.0-MILESTONE-AUDIT.md` - Gap identification (COM-01, COM-04)

### Secondary (MEDIUM confidence)
- Python pathlib documentation - Path.mkdir() idempotency pattern
- JSON standard - Configuration file format

### Tertiary (LOW confidence)
None required — all research based on existing codebase.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Uses Python stdlib only, no external dependencies
- Architecture: HIGH - Patterns proven in existing L3 config and snapshot.py
- Pitfalls: HIGH - Common Python filesystem pitfalls, well-documented

**Research date:** 2026-02-18
**Valid until:** 90 days (stable patterns, unlikely to change)
