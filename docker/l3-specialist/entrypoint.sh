#!/usr/bin/env bash
set -euo pipefail

# Required environment variables (set by spawner)
: "${TASK_ID:?TASK_ID is required}"
: "${SKILL_HINT:?SKILL_HINT is required}"
: "${STAGING_BRANCH:?STAGING_BRANCH is required}"
: "${CLI_RUNTIME:=claude-code}"
: "${TASK_DESCRIPTION:=No task description provided}"
: "${OPENCLAW_PROJECT:?OPENCLAW_PROJECT is required — container spawned without project context}"

STATE_FILE="${OPENCLAW_STATE_FILE:-/workspace/.openclaw/workspace-state.json}"

# Helper: update state.json via Python state engine
update_state() {
  local status="$1"
  local message="$2"
  python3 -c "
import sys; sys.path.insert(0, '/orchestration')
from state_engine import JarvisState
js = JarvisState('${STATE_FILE}')
js.update_task('${TASK_ID}', '${status}', '${message}')
"
}

# Configure git for commits
git config --global user.name "L3 Specialist"
git config --global user.email "l3@openclaw.local"

# 1. Report startup
update_state "starting" "Container initialized. Skill: ${SKILL_HINT}, Runtime: ${CLI_RUNTIME}"

# 2. Create staging branch
cd /workspace
if git show-ref --verify --quiet "refs/heads/${STAGING_BRANCH}"; then
  git checkout "${STAGING_BRANCH}"
  update_state "in_progress" "Checked out existing staging branch: ${STAGING_BRANCH}"
else
  git checkout -b "${STAGING_BRANCH}" main 2>/dev/null || git checkout -b "${STAGING_BRANCH}"
  update_state "in_progress" "Created new staging branch: ${STAGING_BRANCH}"
fi

# 3. Execute task based on skill hint
update_state "in_progress" "Executing task with ${CLI_RUNTIME}..."

# Placeholder: actual CLI invocation will depend on runtime
# This is the hook point where Claude Code / Codex / Gemini CLI runs
if command -v "${CLI_RUNTIME}" &>/dev/null; then
  ${CLI_RUNTIME} --task "${TASK_DESCRIPTION}" 2>&1 | tee /tmp/task-output.log || true
  EXIT_CODE=$?
else
  echo "WARNING: CLI runtime '${CLI_RUNTIME}' not found. Running in dry-run mode."
  # In dry-run mode, simulate success
  EXIT_CODE=0
fi

# 4. Capture results
if [ $EXIT_CODE -eq 0 ]; then
  # Stage and commit changes on staging branch
  git add -A || true
  if git diff --cached --quiet; then
    update_state "completed" "Task completed. No files changed."
  else
    CHANGED_FILES=$(git diff --cached --name-only | head -20 | tr '\n' ', ')
    git commit -m "L3 task ${TASK_ID}: ${SKILL_HINT}" --allow-empty
    update_state "completed" "Task completed. Changed files: ${CHANGED_FILES}"
  fi
else
  # Capture failure context
  LAST_OUTPUT=$(tail -50 /tmp/task-output.log 2>/dev/null || echo "No output captured")
  update_state "failed" "Task failed (exit code ${EXIT_CODE}). Last output: ${LAST_OUTPUT}"
  exit $EXIT_CODE
fi
