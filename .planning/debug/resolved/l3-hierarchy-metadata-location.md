---
status: resolved
trigger: "L3 hierarchy metadata removed from openclaw.json due to schema validation errors - find correct storage location"
created: 2026-02-23T00:00:00Z
updated: 2026-02-23T00:02:00Z
---

## Current Focus

hypothesis: RESOLVED
test: verified openclaw.json has no hierarchy fields; agents/l3_specialist/config.json has all four fields
expecting: n/a
next_action: archive

## Symptoms

expected: L3 hierarchy metadata (level=3, reports_to=pumplai_pm, spawned_by=pumplai_pm, lifecycle=ephemeral) should be stored somewhere accessible to the orchestration system
actual: These properties were removed from openclaw.json because the schema doesn't support them
errors: "agents.list.5: Unrecognized keys: level, reports_to, spawned_by, lifecycle"
reproduction: Add those keys to agents.list[5] in openclaw.json → config validation fails
timeline: Properties were added during Phase 3 (Specialist Execution), removed just now to fix config validation

## Eliminated

- hypothesis: Store in openclaw.json agents.list entry
  evidence: openclaw.json schema validates against known keys only; adding level/reports_to/spawned_by/lifecycle causes "Unrecognized keys" validation error
  timestamp: 2026-02-23

## Evidence

- timestamp: 2026-02-23
  checked: agents/clawdia_prime/agent/config.json
  found: L1 agent config has level=1, reports_to=null, subordinates=["pumplai_pm"] - hierarchy metadata lives in the agent's OWN config.json
  implication: The pattern is established - each agent stores its own hierarchy position in its config.json, not in openclaw.json

- timestamp: 2026-02-23
  checked: agents/l3_specialist/config.json
  found: Already had level=3 and reports_to="pumplai_pm". lifecycle lives inside container block as container.lifecycle="ephemeral". Only spawned_by was missing.
  implication: Most hierarchy metadata was already correctly placed; only spawned_by needed adding.

- timestamp: 2026-02-23
  checked: skills/spawn_specialist/spawn.py Docker labels
  found: "openclaw.spawned_by" was hardcoded to "pumplai_pm" string literal instead of reading from config
  implication: spawn.py should derive hierarchy labels from agent config to keep single source of truth.

- timestamp: 2026-02-23
  checked: scripts/verify_l1_delegation.py
  found: Validation script reads level from agents/clawdia_prime/agent/config.json and checks it equals 1, confirming agent config.json is the authoritative source.
  implication: The pattern is intentional and validated by tooling.

- timestamp: 2026-02-23
  checked: openclaw.json agents.list[5] after fix
  found: Only id, name, workspace, sandbox - no hierarchy fields. Schema-clean.
  implication: Verification PASSED.

## Resolution

root_cause: openclaw.json is a platform registry (id, name, sandbox, workspace only). Hierarchy metadata (level, reports_to, spawned_by, lifecycle) belongs in the agent's own config.json, following the same pattern established by agents/clawdia_prime/agent/config.json. The L3 config already had level, reports_to, and container.lifecycle; spawned_by was the only missing field. Additionally, spawn.py was hardcoding the spawned_by value instead of reading from config.

fix: |
  1. Added "spawned_by": "pumplai_pm" to agents/l3_specialist/config.json (alongside existing level=3 and reports_to)
  2. Updated skills/spawn_specialist/spawn.py to load l3_config at spawn time and derive:
     - openclaw.spawned_by from config.spawned_by (was hardcoded "pumplai_pm")
     - openclaw.tier from config.level (was hardcoded "l3")
     - mem_limit and cpu_quota from config.container (removes duplication)

verification: |
  - openclaw.json l3_specialist entry: only id, name, workspace, sandbox (no schema violations)
  - agents/l3_specialist/config.json: level=3, reports_to=pumplai_pm, spawned_by=pumplai_pm, container.lifecycle=ephemeral
  - spawn.py: reads spawned_by from config, no hardcoded strings
  - Pattern consistent with clawdia_prime L1 agent config structure

files_changed:
  - agents/l3_specialist/config.json
  - skills/spawn_specialist/spawn.py
