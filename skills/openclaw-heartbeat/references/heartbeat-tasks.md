# Heartbeat Task Templates

## Email Monitoring

```markdown
## Email Check

1. Search unread emails from the last {N} hours
2. Categorize: urgent (reply needed today), informational, spam/ignore
3. For each urgent: extract subject, sender, one-line summary
4. Write to heartbeat-state.json: { "email": { "lastChecked": now, "urgentCount": N } }
5. If urgent count > 0: message user with list
6. Otherwise: stay silent
```

## Calendar Check

```markdown
## Calendar Check

1. Fetch events for next 4 hours
2. Alert if: meeting in <15 min, new invite added since last check, cancellation
3. Write to heartbeat-state.json: { "calendar": { "nextEvent": event, "lastChecked": now } }
4. Alert only on changes; stay silent if nothing new
```

## System Health

```markdown
## System Health Check

1. Ping monitored services: {list services and expected responses}
2. Check disk usage on {mount points}
3. Check for failed systemd services: `systemctl --failed`
4. Write findings to heartbeat-state.json
5. Alert immediately if: service down, disk > 90%, systemd failure
```

## Slack/Discord Mentions

```markdown
## Mentions Check

1. Check unread mentions in Slack/Discord (since last heartbeat)
2. Surface only direct mentions (@name) and DMs
3. Ignore channel messages unless directly relevant
4. Write to heartbeat-state.json: { "mentions": { "count": N, "lastChecked": now } }
```

## Development Pipeline

```markdown
## Dev Pipeline Check

1. Check CI status for recent commits on main
2. Check for open PRs awaiting your review
3. Check for failing test runs
4. Check dependency vulnerability alerts
5. Alert on: CI failure, security vulnerability, PR review request
```

## Weather / Location

```markdown
## Weather Check

1. Fetch weather for tomorrow: {location}
2. Alert if: precipitation > 50%, extreme temperature, severe weather warning
3. Include brief summary in morning message (not a dedicated alert)
```

## Multi-Project Health Aggregation

```markdown
## Project Health (runs once/hour)

For each active project in openclaw.json:
1. Check how many L3 tasks are stuck in `in_progress` > 2 hours
2. Check how many tasks are in `failed` state since last check
3. Check if memU service is reachable
4. Summarize: { project: { stuck: N, failed: N, memu: up|down } }
5. Alert L1 if any project has stuck > 3 or memu down
```
