# Orchestration Debug Checklist

## Directive Not Reaching L2

1. `openclaw models status` — is the primary model auth valid?
2. `openclaw agent --local --agent {id} --message "ping"` — does local run work?
3. Check `~/.openclaw/agents/{agentId}/sessions/` — is a session file created?
4. Check gateway is running: `openclaw status` or `curl http://localhost:18789/health`

## L3 Never Starts

1. `docker ps -a | grep openclaw` — is Docker daemon reachable?
2. Check pool: `data/{project_id}/pool-state.json` — are 3 containers already running?
3. Check `projects/{project_id}/project.json` — valid `workspace` path?
4. Check `skills/spawn/spawn.py` logs for memU connection failures (non-blocking, but noisy)

## L3 Exits Without Progress

1. Check container logs: `docker logs openclaw-{project}-l3-{task_id}`
2. Verify SOUL file was written: `data/{project_id}/soul-{task_id}.md`
3. Verify workspace branch exists: `git -C {workspace} branch -a | grep l3/task-{task_id}`
4. Check exit code — non-zero triggers `failed` state

## State File Corruption

Recovery via `.bak`:
```python
# state_engine.py handles this automatically
# To manually recover:
cp data/{project_id}/workspace-state.json.bak data/{project_id}/workspace-state.json
```

## Memory Injection Not Firing

1. Verify memU service is up: `curl http://localhost:{memu_port}/health`
2. Check `memu_api_url` in `projects/{project_id}/project.json`
3. Memory failures are non-blocking — task still runs, memories just aren't injected

## Stale Lock

```bash
# Check for stale flock (process dead but lock held)
lsof data/{project_id}/workspace-state.json
# If no process holds it, lock will release automatically on next open
```
