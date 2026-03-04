# Grand Architect Protocol: PumplAI Pilot Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Establish the core orchestration layer of the Grand Architect Protocol through a staged pilot for the PumplAI project, ensuring robust delegation and volume mapping.

**Architecture:** A three-tiered hierarchy where ClawdiaPrime (Level 1) delegates tasks to a dedicated PumplAI_PM (Level 2). The PM manages project-specific state and mediates access to Level 3 specialists via a hub-and-spoke model using the OpenClaw Gateway.

**Tech Stack:** Node.js 22.x, Bun, Docker, OpenClaw CLI, Ubuntu 24.04.

---

### Task 1: Environment & Gateway Configuration

**Files:**
- Modify: `openclaw.json` (Root config)

**Step 1: Define Gateway and PumplAI_PM Node**
Ensure the root configuration establishes the network modes and the initial L2 node mapping.

```json
{
  "gateway": {
    "port": 18789,
    "nodes": [
      {
        "id": "PumplAI_PM",
        "role": "orchestrator",
        "volumes": ["$HOME/Development/Projects/pai:/app/project"],
        "env": {
          "NODE_VERSION": "22",
          "RUNTIME": "bun",
          "PROJECT_DIR": "/app/project"
        }
      }
    ]
  },
  "lane_queue": {
    "concurrency": "serial",
    "priority_weighting": true
  }
}
```

**Step 2: Verify Volume Permissions**
Run: `ls -ld $HOME/Development/Projects/pumplai`
Expected: Directory exists and is writable by UID 1000.

**Step 3: Test Gateway Connectivity**
Run: `openclaw gateway --test-ping --port 18789`
Expected: `Gateway active on port 18789. Ping successful.`

**Step 4: Commit**
```bash
git add openclaw.json
git commit -m "chore: configure gateway and PumplAI_PM node mapping"
```

---

### Task 2: PumplAI_PM Identity & SOUL

**Files:**
- Create: `agents/PumplAI_PM/SOUL.md`
- Create: `agents/PumplAI_PM/identity.json`

**Step 1: Define PumplAI_PM SOUL**
```markdown
# SOUL: PumplAI Project Manager (Level 2)
- **Role**: Intermediate Orchestrator for the PumplAI ecosystem.
- **Hierarchy**: Reports to ClawdiaPrime; supervises `nuxt_pm` and `security_auditor`.
- **Memory**: Maintains persistent state of `/app/project` file tree using semantic snapshots.
- **Governance**: Enforces Node 22+ ESM standards and Pixi environment isolation.
- **Behavior**: Refuses tasks outside `/app/project` scope.
```

**Step 2: Create Identity Config**
```json
{
  "id": "PumplAI_PM",
  "tier": 2,
  "parent": "ClawdiaPrime",
  "permissions": ["fs", "agentToAgent", "exec"],
  "allowed_paths": ["/app/project"]
}
```

**Step 3: Initialize Node**
Run: `openclaw pairing --id PumplAI_PM --role orchestrator`
Expected: `Node PumplAI_PM successfully paired and registered to ClawdiaPrime.`

**Step 4: Commit**
```bash
git add agents/PumplAI_PM/
git commit -m "feat: define PumplAI_PM SOUL and identity"
```

---

### Task 3: Delegation Skill Implementation

**Files:**
- Create: `skills/pumplai_delegation.yaml`

**Step 1: Write Delegation Logic**
```yaml
---
name: delegate_pumplai_task
description: Primary delegation logic for ClawdiaPrime to route tasks to PumplAI_PM.
scope: internal_hierarchy
---
# Logic
1. Validate task context (ensures it pertains to PumplAI).
2. Serialize context into `task_packet.json`.
3. Invoke:
   ```bash
   openclaw call PumplAI_PM --task "$(cat task_packet.json)" --lane serial
```
4. Await response and verify semantic snapshot integrity.
```

**Step 2: Test Delegation Handshake**
Run: `openclaw call PumplAI_PM --task "Verify workspace mount"`
Expected: `[PumplAI_PM] Workspace /app/project detected. Status: OK.`

**Step 3: Commit**
```bash
git add skills/pumplai_delegation.yaml
git commit -m "feat: implement PumplAI delegation skill"
```

---

### Task 4: Integration & Semantic Snapshot Test

**Files:**
- Create: `tests/integration/test_pumplai_handshake.sh`

**Step 1: Create Test Script**
```bash
#!/bin/bash
# Test the L1 -> L2 handshake and volume mapping
TASK="Generate semantic snapshot of /app/project"
RESULT=$(openclaw call PumplAI_PM --task "$TASK")

if [[ $RESULT == *"Snapshot created"* ]]; then
  echo "PASS: Handshake and Volume Mapping Verified"
  exit 0
else
  echo "FAIL: Unexpected result: $RESULT"
  exit 1
fi
```

**Step 2: Run Integration Test**
Run: `bash tests/integration/test_pumplai_handshake.sh`
Expected: `PASS: Handshake and Volume Mapping Verified`

**Step 3: Commit**
```bash
git add tests/integration/test_pumplai_handshake.sh
git commit -m "test: add integration test for PumplAI pilot handshake"
```
