# L3 Container Configuration Reference

## Docker Security Profile

```python
container_config = {
    "image": "openclaw-l3-specialist:latest",
    "name": f"openclaw-{project_id}-l3-{task_id}",
    "security_opt": ["no-new-privileges"],
    "cap_drop": ["ALL"],
    "mem_limit": "4g",
    "cpu_quota": 100000,   # 1 CPU
    "user": "1000",        # non-root
}
```

## Volume Mounts

| Host Path | Container Path | Mode |
|-----------|---------------|------|
| `{workspace}` | `/workspace` | `rw` |
| `~/.openclaw` | `/openclaw` | `ro` |
| `{soul_file}` | `/openclaw/soul.md` | `ro` |

## Environment Variables Injected

| Variable | Value |
|----------|-------|
| `TASK_ID` | task_id |
| `TASK_DESCRIPTION` | task description |
| `PROJECT_ID` | project_id |
| `AGENT_TYPE` | L3_CODE \| L3_TEST \| L3_REVIEW |
| `SOUL_FILE` | `/openclaw/soul.md` |
| `OPENCLAW_STATE_FILE` | path to workspace-state.json |

## Build the Image

```bash
make docker-l3
# or directly:
docker build -f docker/l3-specialist/Dockerfile -t openclaw-l3-specialist .
```

## Entrypoint Flow (`docker/l3-specialist/entrypoint.sh`)

1. Read `SOUL_FILE`
2. Detect `CLI_RUNTIME` (claude-code | codex | gemini-cli)
3. For `claude-code` / `codex`: pass soul as `--system-prompt` arg
4. For `gemini-cli`: write soul to `GEMINI.md`
5. Execute: `"${CLI_RUNTIME}" "${SOUL_ARGS[@]}" --task "${TASK_DESCRIPTION}"`

## Container Labels

All containers tagged with:
- `openclaw.project={project_id}`
- `openclaw.task={task_id}`
- `openclaw.agent_type={agent_type}`
- `openclaw.session={session_id}`

Use labels for monitoring: `docker ps --filter "label=openclaw.project=pumplai"`
