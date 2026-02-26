---
name: openclaw-heartbeat
description: Heartbeat operations and periodic agent monitoring in OpenClaw. Use when setting up scheduled/recurring agent checks, configuring HEARTBEAT.md tasks, managing heartbeat state, batching periodic API checks (email, calendar, weather, system health), implementing quiet hours, or debugging missed heartbeats. Triggers for: "heartbeat", "periodic check", "scheduled agent", "batch checks", "HEARTBEAT.md", "quiet hours", "recurring task", "heartbeat state", "cron agent".
---

# OpenClaw Heartbeat Operations

Heartbeats let the agent periodically check external systems (email, calendar, system health) in a single batched turn, rather than polling constantly.

## Enable Heartbeat

In `HEARTBEAT.md` — leave **empty** (or comments only) to disable:

```markdown
# HEARTBEAT.md

# Add task lines to enable periodic checks:
- Check unread email and surface anything urgent
- Check today's calendar for upcoming meetings
- Check weather for tomorrow
- Check if any monitored services are down
```

The agent reads this file and decides which checks to perform each heartbeat cycle.

## Heartbeat State

State tracked in `memory/heartbeat-state.json`:

```json
{
  "lastChecked": {
    "email": "2026-02-25T09:00:00Z",
    "calendar": "2026-02-25T09:00:00Z",
    "weather": "2026-02-25T09:00:00Z"
  },
  "pendingAlerts": [],
  "lastRun": "2026-02-25T09:00:00Z"
}
```

Update this file after each check to avoid redundant API calls on the next heartbeat.

## Quiet Hours

Don't disturb the user during overnight hours:

```markdown
## Quiet Hours Policy

Stay quiet between 23:00-08:00 local time unless:
- A critical alert fires (server down, payment failed, security breach)
- The user explicitly requested a night alert

Defer non-urgent findings to the morning summary.
```

## Batch Check Pattern

Good heartbeat: one turn, batch all checks, one summary message.

```markdown
## Heartbeat Checklist

1. Check unread email (last 2 hours) — surface urgent only
2. Check calendar — next 4 hours
3. Check Slack mentions
4. Ping monitored services
5. Write findings to memory/heartbeat-state.json
6. If anything urgent: message user
7. If nothing: stay silent (reply with NO_REPLY)
```

## Triggering Heartbeats via Cron

```bash
# cron: */30 * * * * (every 30 minutes)
openclaw agent --agent main --message "HEARTBEAT: run your heartbeat checklist"
```

Or use OpenClaw's built-in scheduler if configured.

## Periodic Memory Review

During heartbeats, periodically consolidate daily memory into MEMORY.md:

```markdown
## Weekly Memory Consolidation

Every Sunday:
1. Read all memory/YYYY-MM-DD.md from the past week
2. Extract key decisions, learnings, and recurring patterns
3. Append a "Week of YYYY-MM-DD" summary to MEMORY.md
4. Note: do NOT delete daily logs
```

## Pre-Compaction Memory Flush

OpenClaw automatically triggers a silent memory flush when the session nears compaction (controlled by `agents.defaults.compaction.memoryFlush`). This is separate from heartbeats but follows the same "write to memory before context is lost" principle.

See [references/heartbeat-tasks.md](references/heartbeat-tasks.md) for a library of ready-to-use heartbeat task templates.
