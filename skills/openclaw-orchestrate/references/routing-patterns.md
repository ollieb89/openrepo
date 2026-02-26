# L1→L2 Routing Patterns

## Agent ID Resolution

Agent IDs come from `openclaw.json` → `agents.list[].id`. Example agents:
```json
{ "id": "main", "name": "Central Core" }
{ "id": "clawdia_prime", "name": "Head of Development" }
{ "id": "pumplai_pm", "name": "PumpLAI Project Manager" }
```

## Directive Templates

**Feature implementation directive:**
```
openclaw agent --agent pumplai_pm --message "DIRECTIVE: Implement {feature}.
Context: {context}
Acceptance criteria: {criteria}
Priority: {high|medium|low}"
```

**Investigation directive:**
```
openclaw agent --agent pumplai_pm --message "DIRECTIVE: Investigate {issue}.
Symptoms: {symptoms}
Expected: {expected_behavior}
Return: root cause + fix recommendation"
```

**Review directive:**
```
openclaw agent --agent pumplai_pm --message "DIRECTIVE: Review PR #{number}.
Branch: {branch}
Focus areas: {areas}
Decision required: approve|request-changes"
```

## Router Skill (`skills/router/index.js`)

Key safety rule: always use `execFileSync` with array args:
```javascript
// CORRECT — no shell injection
execFileSync('openclaw', ['agent', '--agent', targetId, '--message', directive]);

// WRONG — never do this
exec(`openclaw agent --agent ${targetId} --message ${directive}`);
```

## Routing Decision Tree

```
Incoming L1 directive
  ├─ Is project-specific? → target project PM agent
  ├─ Is global/infra? → target main agent
  ├─ Is parallel-safe? → fan-out to multiple agents
  └─ Is sequential? → chain via session ID
```

## Session Continuity

Reuse a session for multi-turn coordination:
```bash
openclaw agent --agent pumplai_pm --session-id {session_id} --message "Follow-up: {context}"
```

Sessions persist at `~/.openclaw/agents/{agentId}/sessions/{sessionId}.jsonl`.
