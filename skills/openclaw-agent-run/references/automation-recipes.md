# Automation Recipes

## Cron: Daily Status Report

```bash
#!/bin/bash
# cron: 0 9 * * 1-5 (weekdays at 9am)
openclaw agent --agent main \
  --message "Generate daily standup: what's pending, what's in progress, any blockers?" \
  --deliver \
  --reply-channel slack \
  --reply-to "#standup"
```

## Script: Fan-Out Parallel Tasks

```bash
#!/bin/bash
declare -a tasks=(
  "Audit security headers in the API"
  "Verify database indexes are optimal"
  "Check for outdated dependencies"
)

pids=()
for task in "${tasks[@]}"; do
  openclaw agent --agent pumplai_pm --message "$task" --json > /tmp/result_$$.json &
  pids+=($!)
done

for pid in "${pids[@]}"; do
  wait $pid
done

# Aggregate results
jq -s '[.[].text]' /tmp/result_*.json
rm /tmp/result_*.json
```

## Script: Check Output Before Delivery

```bash
#!/bin/bash
RESULT=$(openclaw agent --agent main --message "Draft the weekly summary" --json)
TEXT=$(echo "$RESULT" | jq -r '.text')
WORD_COUNT=$(echo "$TEXT" | wc -w)

if [ "$WORD_COUNT" -gt 50 ]; then
  echo "$RESULT" | jq -r '.text' | openclaw agent \
    --agent main \
    --message "Send this to the team channel: $TEXT" \
    --deliver --reply-channel slack --reply-to "#team"
fi
```

## Python: Orchestration Wrapper

```python
import subprocess, json

def run_agent(agent_id: str, message: str, session_id: str = None) -> dict:
    cmd = ["openclaw", "agent", "--agent", agent_id, "--message", message, "--json"]
    if session_id:
        cmd += ["--session-id", session_id]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)

# Multi-turn with session continuity
response = run_agent("pumplai_pm", "Start planning feature X")
session = response["sessionId"]

followup = run_agent("pumplai_pm", "Break it into L3 tasks", session_id=session)
print(followup["text"])
```

## Node.js: Router Pattern (L1)

```javascript
const { execFileSync } = require('child_process');

function dispatchDirective(agentId, directive) {
  // ALWAYS use array args — no shell injection
  const output = execFileSync('openclaw', [
    'agent', '--agent', agentId,
    '--message', directive,
    '--json'
  ], { encoding: 'utf8' });
  return JSON.parse(output);
}

// Fan-out to multiple agents
const agents = ['pumplai_pm', 'smartai_pm', 'finai_pm'];
const results = agents.map(id =>
  dispatchDirective(id, 'Daily health check: report status')
);
```
