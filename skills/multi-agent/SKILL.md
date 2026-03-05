---
name: multi-agent
description: Use when running multiple coding agents in parallel or orchestrating complex multi-agent workflows. Covers individual agent execution (Codex, Claude, Gemini, OpenCode, Pi) with PTY mode, dependency-based orchestration with worktrees/tmux, and self-healing monitoring.
metadata:
  openclaw:
    emoji: "👥"
    category: "multi-agent"
---

# Multi-Agent Orchestration & Execution

Comprehensive guide for running multiple coding agents - from quick one-shot tasks to complex orchestrated workflows with dependencies and self-healing monitoring.

## Overview

This skill covers two main patterns:
1. **Individual Agent Execution** - Run Codex, Claude Code, or other agents for single tasks
2. **Multi-Agent Orchestration** - Coordinate multiple agents with dependencies, worktrees, and monitoring

**Load the senior-engineering skill alongside this one for engineering principles.**

---

## Part 1: Individual Agent Execution (bash-first)

Use **bash** (with optional background mode) for all coding agent work. Simple and effective.

### ⚠️ PTY Mode Required!

Coding agents (Codex, Claude Code, Pi) are **interactive terminal applications** that need a pseudo-terminal (PTY) to work correctly. Without PTY, you'll get broken output, missing colors, or the agent may hang.

**Always use `pty:true`** when running coding agents:

```bash
# ✅ Correct - with PTY
bash pty:true command:"codex exec 'Your prompt'"

# ❌ Wrong - no PTY, agent may break
bash command:"codex exec 'Your prompt'"
```

#### Bash Tool Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `command` | string | The shell command to run |
| `pty` | boolean | **Use for coding agents!** Allocates a pseudo-terminal for interactive CLIs |
| `workdir` | string | Working directory (agent sees only this folder's context) |
| `background` | boolean | Run in background, returns sessionId for monitoring |
| `timeout` | number | Timeout in seconds (kills process on expiry) |
| `elevated` | boolean | Run on host instead of sandbox (if allowed) |

#### Process Tool Actions (for background sessions)

| Action | Description |
|--------|-------------|
| `list` | List all running/recent sessions |
| `poll` | Check if session is still running |
| `log` | Get session output (with optional offset/limit) |
| `write` | Send raw data to stdin |
| `submit` | Send data + newline (like typing and pressing Enter) |
| `send-keys` | Send key tokens or hex bytes |
| `paste` | Paste text (with optional bracketed mode) |
| `kill` | Terminate the session |

---

### Quick Start: One-Shot Tasks

For quick prompts/chats, create a temp git repo and run:

```bash
# Quick chat (Codex needs a git repo!)
SCRATCH=$(mktemp -d) && cd $SCRATCH && git init && codex exec "Your prompt here"

# Or in a real project - with PTY!
bash pty:true workdir:~/Projects/myproject command:"codex exec 'Add error handling to the API calls'"
```

**Why git init?** Codex refuses to run outside a trusted git directory. Creating a temp repo solves this for scratch work.

---

### The Pattern: workdir + background + pty

For longer tasks, use background mode with PTY:

```bash
# Start agent in target directory (with PTY!)
bash pty:true workdir:~/project background:true command:"codex exec --full-auto 'Build a snake game'"
# Returns sessionId for tracking

# Monitor progress
process action:log sessionId:XXX

# Check if done
process action:poll sessionId:XXX

# Send input (if agent asks a question)
process action:write sessionId:XXX data:"y"

# Submit with Enter (like typing "yes" and pressing Enter)
process action:submit sessionId:XXX data:"yes"

# Kill if needed
process action:kill sessionId:XXX
```

**Why workdir matters:** Agent wakes up in a focused directory, doesn't wander off reading unrelated files.

---

### Fallback Strategy

When primary agent hits limits, fall back in order:

| Priority | Agent | When to Use |
|----------|-------|-------------|
| 1 | **Codex** | Default for coding tasks |
| 2 | **Claude Code** | Codex usage limits or errors |
| 3 | **Gemini** | Claude unavailable or for Gemini-specific tasks |
| 4 | **Pi/OpenCode** | All above unavailable |

**Signs you need to fall back:**
- "You've hit your usage limit"
- Rate limit / 429 errors
- Model overloaded messages

---

### Codex CLI

**Model:** `gpt-5.2-codex` is the default (set in ~/.codex/config.toml)

#### Flags

| Flag | Effect |
|------|--------|
| `exec "prompt"` | One-shot execution, exits when done |
| `--full-auto` | Sandboxed but auto-approves in workspace |
| `--yolo` | NO sandbox, NO approvals (fastest, most dangerous) |

#### Building/Creating

```bash
# Quick one-shot (auto-approves) - remember PTY!
bash pty:true workdir:~/project command:"codex exec --full-auto 'Build a dark mode toggle'"

# Background for longer work
bash pty:true workdir:~/project background:true command:"codex --yolo 'Refactor the auth module'"
```

#### Reviewing PRs

**⚠️ CRITICAL: Never review PRs in the main project folder!**
Clone to temp folder or use git worktree.

```bash
# Clone to temp for safe review
REVIEW_DIR=$(mktemp -d)
git clone https://github.com/user/repo.git $REVIEW_DIR
cd $REVIEW_DIR && gh pr checkout 130
bash pty:true workdir:$REVIEW_DIR command:"codex review --base origin/main"
# Clean up after: trash $REVIEW_DIR

# Or use git worktree (keeps main intact)
git worktree add /tmp/pr-130-review pr-130-branch
bash pty:true workdir:/tmp/pr-130-review command:"codex review --base main"
```

#### Batch PR Reviews (parallel army!)

```bash
# Fetch all PR refs first
git fetch origin '+refs/pull/*/head:refs/remotes/origin/pr/*'

# Deploy the army - one Codex per PR (all with PTY!)
bash pty:true workdir:~/project background:true command:"codex exec 'Review PR #86. git diff origin/main...origin/pr/86'"
bash pty:true workdir:~/project background:true command:"codex exec 'Review PR #87. git diff origin/main...origin/pr/87'"

# Monitor all
process action:list

# Post results to GitHub
gh pr comment <PR#> --body "<review content>"
```

---

### Claude Code

**Fallback when Codex unavailable.**

| Codex | Claude Equivalent |
|-------|-------------------|
| `codex exec "prompt"` | `claude -p "prompt"` |
| `codex --full-auto` | `claude -p --permission-mode acceptEdits` |
| `codex --yolo` | `claude -p --dangerously-skip-permissions` |

```bash
# Non-interactive
claude -p "Add error handling to src/api.ts"
claude -p --permission-mode acceptEdits "Fix the bug"

# Interactive (with PTY)
bash pty:true workdir:~/project command:"claude 'Your task'"
```

---

### Gemini CLI

**Alternative fallback with different model family.**

| Codex | Gemini Equivalent |
|-------|-------------------|
| `codex exec "prompt"` | `gemini "prompt"` |
| `codex --full-auto` | `gemini --approval-mode auto_edit "prompt"` |
| `codex --yolo` | `gemini -y "prompt"` |

```bash
# Non-interactive (one-shot)
gemini "Add error handling to src/api.ts"
gemini -y "Build a REST API"  # yolo mode

# Interactive (with PTY)
bash pty:true workdir:~/project command:"gemini -i 'Your task'"
```

---

### OpenCode

```bash
bash pty:true workdir:~/project command:"opencode run 'Your task'"
```

---

### Pi Coding Agent

```bash
# Install: npm install -g @mariozechner/pi-coding-agent
bash pty:true workdir:~/project command:"pi 'Your task'"

# Non-interactive mode (PTY still recommended)
bash pty:true command:"pi -p 'Summarize src/'"

# Different provider/model
bash pty:true command:"pi --provider openai --model gpt-4o-mini -p 'Your task'"
```

---

## Part 2: Multi-Agent Orchestration

For complex projects with multiple interdependent tasks, use full orchestration with manifest-based coordination.

### Core Concepts

#### 1. Task Manifest

A JSON file defining all tasks, their dependencies, files touched, and status.

```json
{
  "project": "project-name",
  "repo": "owner/repo",
  "workdir": "/path/to/worktrees",
  "created": "2026-01-17T00:00:00Z",
  "model": "gpt-5.2-codex",
  "modelTier": "high",
  "phases": [
    {
      "name": "Phase 1: Critical",
      "tasks": [
        {
          "id": "t1",
          "issue": 1,
          "title": "Fix X",
          "files": ["src/foo.js"],
          "dependsOn": [],
          "status": "pending",
          "worktree": null,
          "tmuxSession": null,
          "startedAt": null,
          "lastProgress": null,
          "completedAt": null,
          "prNumber": null
        }
      ]
    }
  ]
}
```

#### 2. Dependency Rules

- **Same file = sequential** — Tasks touching the same file must run in order or merge
- **Different files = parallel** — Independent tasks can run simultaneously
- **Explicit depends = wait** — `dependsOn` array enforces ordering
- **Phase gates** — Next phase waits for current phase completion

#### 3. Execution Model

- Each task gets its own **git worktree** (isolated branch)
- Each task runs in its own **tmux session**
- Use **Codex with --yolo** for autonomous execution
- Model: **GPT-5.2-codex high** (configurable)

---

### Setup Commands

#### Initialize Orchestration

```bash
# 1. Create working directory
WORKDIR="${TMPDIR:-/tmp}/orchestrator-$(date +%s)"
mkdir -p "$WORKDIR"

# 2. Clone repo for worktrees
git clone https://github.com/OWNER/REPO.git "$WORKDIR/repo"
cd "$WORKDIR/repo"

# 3. Create tmux socket
SOCKET="$WORKDIR/orchestrator.sock"

# 4. Initialize manifest
cat > "$WORKDIR/manifest.json" << 'EOF'
{
  "project": "PROJECT_NAME",
  "repo": "OWNER/REPO",
  "workdir": "WORKDIR_PATH",
  "socket": "SOCKET_PATH",
  "created": "TIMESTAMP",
  "model": "gpt-5.2-codex",
  "modelTier": "high",
  "phases": []
}
EOF
```

#### Analyze GitHub Issues for Dependencies

```bash
# Fetch all open issues
gh issue list --repo OWNER/REPO --state open --json number,title,body,labels > issues.json

# Group by files mentioned in issue body
# Tasks touching same files should serialize
```

#### Create Worktrees

```bash
# For each task, create isolated worktree
cd "$WORKDIR/repo"
git worktree add -b fix/issue-N "$WORKDIR/task-tN" main
```

#### Launch Tmux Sessions

```bash
SOCKET="$WORKDIR/orchestrator.sock"

# Create session for task
tmux -S "$SOCKET" new-session -d -s "task-tN"

# Launch Codex (uses gpt-5.2-codex with reasoning_effort=high from ~/.codex/config.toml)
# Note: Model config is in ~/.codex/config.toml, not CLI flag
tmux -S "$SOCKET" send-keys -t "task-tN" \
  "cd $WORKDIR/task-tN && codex --yolo 'Fix issue #N: DESCRIPTION. Run tests, commit with good message, push to origin.'" Enter
```

---

### Monitoring & Self-Healing

#### Progress Check Script

```bash
#!/bin/bash
# check_progress.sh - Run via heartbeat

WORKDIR="$1"
SOCKET="$WORKDIR/orchestrator.sock"
MANIFEST="$WORKDIR/manifest.json"
STALL_THRESHOLD_MINS=20

check_session() {
  local session="$1"
  local task_id="$2"
  
  # Capture recent output
  local output=$(tmux -S "$SOCKET" capture-pane -p -t "$session" -S -50 2>/dev/null)
  
  # Check for completion indicators
  if echo "$output" | grep -qE "(All tests passed|Successfully pushed|❯ $)"; then
    echo "DONE:$task_id"
    return 0
  fi
  
  # Check for errors
  if echo "$output" | grep -qiE "(error:|failed:|FATAL|panic)"; then
    echo "ERROR:$task_id"
    return 1
  fi
  
  # Check for stall (prompt waiting for input)
  if echo "$output" | grep -qE "(\? |Continue\?|y/n|Press any key)"; then
    echo "STUCK:$task_id:waiting_for_input"
    return 2
  fi
  
  echo "RUNNING:$task_id"
  return 0
}

# Check all active sessions
for session in $(tmux -S "$SOCKET" list-sessions -F "#{session_name}" 2>/dev/null); do
  check_session "$session" "$session"
done
```

#### Self-Healing Actions

When a task is stuck, the orchestrator should:

1. **Waiting for input** → Send appropriate response
   ```bash
   tmux -S "$SOCKET" send-keys -t "$session" "y" Enter
   ```

2. **Error/failure** → Capture logs, analyze, retry with fixes
   ```bash
   # Capture error context
   tmux -S "$SOCKET" capture-pane -p -t "$session" -S -100 > "$WORKDIR/logs/$task_id-error.log"

   # Kill and restart with error context
   tmux -S "$SOCKET" kill-session -t "$session"
   tmux -S "$SOCKET" new-session -d -s "$session"
   tmux -S "$SOCKET" send-keys -t "$session" \
     "cd $WORKDIR/$task_id && codex --model gpt-5.2-codex-high --yolo 'Previous attempt failed with: $(cat error.log | tail -20). Fix the issue and retry.'" Enter
   ```

3. **No progress for 20+ mins** → Nudge or restart
   ```bash
   # Check git log for recent commits
   cd "$WORKDIR/$task_id"
   LAST_COMMIT=$(git log -1 --format="%ar" 2>/dev/null)

   # If no commits in threshold, restart
   ```

#### Heartbeat Cron Setup

```bash
# Add to cron (every 15 minutes)
cron action:add job:{
  "label": "orchestrator-heartbeat",
  "schedule": "*/15 * * * *",
  "prompt": "Check orchestration progress at WORKDIR. Read manifest, check all tmux sessions, self-heal any stuck tasks, advance to next phase if current is complete. Do NOT ping human - fix issues yourself."
}
```

---

### Workflow: Full Orchestration Run

#### Step 1: Analyze & Plan

```bash
# 1. Fetch issues
gh issue list --repo OWNER/REPO --state open --json number,title,body > /tmp/issues.json

# 2. Analyze for dependencies (files mentioned, explicit deps)
# Group into phases:
# - Phase 1: Critical/blocking issues (no deps)
# - Phase 2: High priority (may depend on Phase 1)
# - Phase 3: Medium/low (depends on earlier phases)

# 3. Within each phase, identify:
# - Parallel batch: Different files, no deps → run simultaneously
# - Serial batch: Same files or explicit deps → run in order
```

#### Step 2: Create Manifest

Write manifest.json with all tasks, dependencies, file mappings.

#### Step 3: Launch Phase 1

```bash
# Create worktrees for Phase 1 tasks
for task in phase1_tasks; do
  git worktree add -b "fix/issue-$issue" "$WORKDIR/task-$id" main
done

# Launch tmux sessions
for task in phase1_parallel_batch; do
  tmux -S "$SOCKET" new-session -d -s "task-$id"
  tmux -S "$SOCKET" send-keys -t "task-$id" \
    "cd $WORKDIR/task-$id && codex --model gpt-5.2-codex-high --yolo '$PROMPT'" Enter
done
```

#### Step 4: Monitor & Self-Heal

Heartbeat checks every 15 mins:
1. Poll all sessions
2. Update manifest with progress
3. Self-heal stuck tasks
4. When all Phase N tasks complete → launch Phase N+1

#### Step 5: Create PRs

```bash
# When task completes successfully
cd "$WORKDIR/task-$id"
git push -u origin "fix/issue-$issue"
gh pr create --repo OWNER/REPO \
  --head "fix/issue-$issue" \
  --title "fix: Issue #$issue - $TITLE" \
  --body "Closes #$issue

## Changes
[Auto-generated by Codex orchestrator]

## Testing
- [ ] Unit tests pass
- [ ] Manual verification"
```

#### Step 6: Cleanup

```bash
# After all PRs merged or work complete
tmux -S "$SOCKET" kill-server
cd "$WORKDIR/repo"
for task in all_tasks; do
  git worktree remove "$WORKDIR/task-$id" --force
done
rm -rf "$WORKDIR"
```

---

## Reference Tables

### Manifest Status Values

| Status | Meaning |
|--------|---------|
| `pending` | Not started yet |
| `blocked` | Waiting on dependency |
| `running` | Codex session active |
| `stuck` | Needs intervention (auto-heal) |
| `error` | Failed, needs retry |
| `complete` | Done, ready for PR |
| `pr_open` | PR created |
| `merged` | PR merged |

### When to Use Different Approaches

| Use Case | Recommended Approach |
|----------|---------------------|
| Quick one-shot tasks | `bash pty:true` |
| Long-running with monitoring | `bash background:true` |
| Multiple parallel agents | **tmux** |
| Agent forking (context transfer) | **tmux** |
| Session persistence | **tmux** |
| Complex dependency orchestration | **Full orchestration** |
| Self-healing monitoring | **Full orchestration** |

---

## Examples

### Security Framework Orchestration

```json
{
  "project": "nuri-security-framework",
  "repo": "jdrhyne/nuri-security-framework",
  "phases": [
    {
      "name": "Phase 1: Critical",
      "tasks": [
        {"id": "t1", "issue": 1, "files": ["ceo_root_manager.js"], "dependsOn": []},
        {"id": "t2", "issue": 2, "files": ["ceo_root_manager.js"], "dependsOn": ["t1"]},
        {"id": "t3", "issue": 3, "files": ["workspace_validator.js"], "dependsOn": []}
      ]
    },
    {
      "name": "Phase 2: High",
      "tasks": [
        {"id": "t4", "issue": 4, "files": ["kill_switch.js", "container_executor.js"], "dependsOn": []},
        {"id": "t5", "issue": 5, "files": ["kill_switch.js"], "dependsOn": ["t4"]},
        {"id": "t6", "issue": 6, "files": ["ceo_root_manager.js"], "dependsOn": ["t2"]},
        {"id": "t7", "issue": 7, "files": ["container_executor.js"], "dependsOn": []},
        {"id": "t8", "issue": 8, "files": ["container_executor.js", "egress_proxy.js"], "dependsOn": ["t7"]}
      ]
    }
  ]
}
```

**Parallel execution in Phase 1:**
- t1 and t3 run in parallel (different files)
- t2 waits for t1 (same file)

**Parallel execution in Phase 2:**
- t4, t6, t7 can start together
- t5 waits for t4, t8 waits for t7

### Parallel Issue Fixing with git worktrees

```bash
# 1. Create worktrees for each issue
git worktree add -b fix/issue-78 /tmp/issue-78 main
git worktree add -b fix/issue-99 /tmp/issue-99 main

# 2. Launch Codex in each (background + PTY!)
bash pty:true workdir:/tmp/issue-78 background:true command:"pnpm install && codex --yolo 'Fix issue #78: <description>. Commit and push.'"
bash pty:true workdir:/tmp/issue-99 background:true command:"pnpm install && codex --yolo 'Fix issue #99: <description>. Commit and push.'"

# 3. Monitor progress
process action:list
process action:log sessionId:XXX

# 4. Create PRs after fixes
cd /tmp/issue-78 && git push -u origin fix/issue-78
gh pr create --repo user/repo --head fix/issue-78 --title "fix: ..." --body "..."

# 5. Cleanup
git worktree remove /tmp/issue-78
git worktree remove /tmp/issue-99
```

### Agent Forking with tmux

Transfer context between agents (e.g., plan with Codex, execute with Claude):

```bash
SOCKET="${TMPDIR:-/tmp}/agents.sock"

# Capture context from current agent
CONTEXT=$(tmux -S "$SOCKET" capture-pane -p -t planner -S -500)

# Fork to new agent with context
tmux -S "$SOCKET" new-session -d -s executor
tmux -S "$SOCKET" send-keys -t executor "claude -p 'Based on this plan: $CONTEXT

Execute step 1.'" Enter
```

---

## ⚠️ Rules

1. **Always use pty:true** - coding agents need a terminal!
2. **Respect tool choice** - if user asks for Codex, use Codex.
   - Orchestrator mode: do NOT hand-code patches yourself.
   - If an agent fails/hangs, respawn it or ask the user for direction, but don't silently take over.
3. **Be patient** - don't kill sessions because they're "slow"
4. **Monitor with process:log** - check progress without interfering
5. **--full-auto for building** - auto-approves changes
6. **vanilla for reviewing** - no special flags needed
7. **Parallel is OK** - run many agents at once for batch work
8. **NEVER start agents in sensitive directories** - they'll read docs and get confused
9. **NEVER checkout branches in live project directories** - that's the LIVE instance!

---

## Progress Updates (Critical)

When you spawn coding agents in the background, keep the user in the loop.

- Send 1 short message when you start (what's running + where).
- Then only update again when something changes:
  - a milestone completes (build finished, tests passed)
  - the agent asks a question / needs input
  - you hit an error or need user action
  - the agent finishes (include what changed + where)
- If you kill a session, immediately say you killed it and why.

This prevents the user from seeing only "Agent failed before reply" and having no idea what happened.

---

## Tips

1. **Always use GPT-5.2-codex high** for complex work: `--model gpt-5.2-codex-high`
2. **Clear prompts** — Include issue number, description, expected outcome, test instructions
3. **Atomic commits** — Tell Codex to commit after each logical change
4. **Push early** — Push to remote branch so progress isn't lost if session dies
5. **Checkpoint logs** — Capture tmux output periodically to files
6. **Phase gates** — Don't start Phase N+1 until Phase N is 100% complete
7. **Self-heal aggressively** — If stuck >10 mins, intervene automatically
8. **Browser relay limits** — If CDP automation is blocked, use iframe batch scraping or manual browser steps
9. **PTY is essential** — Without `pty:true`, output breaks or agent hangs
10. **Git repo required** — Codex won't run outside a git directory
11. **exec is your friend** — `codex exec "prompt"` runs and exits cleanly
12. **submit vs write** — Use `submit` to send input + Enter, `write` for raw data

---

## Integration with Other Skills

- **senior-engineering**: Load for build principles and quality gates
- **github**: Use for PR creation, issue management
- **tmux**: For advanced session management (referenced throughout)

---

## Lessons Learned (2026-01-17)

### Codex Sandbox Limitations

When using `codex exec --full-auto`, the sandbox:
- **No network access** — `git push` fails with "Could not resolve host"
- **Limited filesystem** — Can't write to restricted paths

**Workaround:** The orchestrator (not the worker) should push commits from outside the sandbox.

### Heartbeat Detection Improvements

The heartbeat should check for:
1. **Shell prompt idle** — If tmux pane shows `username@hostname path %`, worker is done
2. **Unpushed commits** — `git log @{u}.. --oneline` shows commits not on remote
3. **Push failures** — Look for "Could not resolve host" in output

When detected, the orchestrator should:
1. Push the commit from outside the sandbox
2. Create the PR via `gh pr create`
3. Update manifest and notify

### Recommended Pattern

```bash
# In heartbeat, for each task:
cd /tmp/orchestrator-*/task-tN
if tmux capture-pane shows shell prompt; then
  # Worker finished, check for unpushed work
  if git log @{u}.. --oneline | grep -q .; then
    git push -u origin HEAD
    gh pr create --title "$(git log --format=%s -1)" --body "Closes #N" --base main
  fi
fi
```
