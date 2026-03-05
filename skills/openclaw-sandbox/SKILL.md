---
name: openclaw-sandbox
description: "Docker sandboxing configuration in OpenClaw. Use when enabling or configuring tool execution sandboxing, choosing sandbox scope (session/agent/shared), setting workspace access modes (none/ro/rw), adding custom volume mounts, configuring sandboxed browsers, or troubleshooting sandbox permission issues. Triggers for: \"sandbox\", \"Docker isolation\", \"tool sandbox\", \"workspace access\", \"sandboxed run\", \"cap_drop\", \"custom mounts\", \"sandbox mode\", \"non-main sandbox\", \"sandboxed browser\"."
metadata:
  openclaw:
    emoji: "🔒"
    category: "orchestration-core"
---

# OpenClaw Sandboxing

The Gateway process stays on the host. Tool execution (read/write/exec/edit) runs inside an isolated Docker container when sandboxing is enabled.

## Execution Modes

```json5
{
  agents: {
    defaults: {
      sandbox: {
        mode: "non-main"  // off | non-main | all
      }
    }
  }
}
```

| Mode | Behavior |
|------|----------|
| `"off"` | No sandboxing — all tools run on host |
| `"non-main"` | Sandbox non-main sessions only (default) |
| `"all"` | Every session sandboxed |

## Container Scope

```json5
sandbox: {
  scope: "session"   // session | agent | shared
}
```

| Scope | Container lifetime |
|-------|-------------------|
| `"session"` | One container per session (default, best isolation) |
| `"agent"` | One container per agent (reused across sessions) |
| `"shared"` | Single container for all sandboxed sessions |

## Workspace Access

```json5
sandbox: {
  workspaceAccess: "rw"   // none | ro | rw
}
```

| Mode | Agent workspace in container |
|------|------------------------------|
| `"none"` | Sandbox workspace under `~/.openclaw/sandboxes` (fully isolated) |
| `"ro"` | Read-only agent workspace at `/agent` |
| `"rw"` | Read-write workspace at `/workspace` |

## Custom Volume Mounts

```json5
sandbox: {
  docker: {
    binds: [
      "/host/data:/container/data:ro",
      "/host/output:/container/output:rw"
    ]
  }
}
```

**Blocked sources** (security): Docker socket, `/etc`, `/proc`, `/sys`, `/dev`, parent mounts. Use `ro` mode unless write access is absolutely required.

## Network Access

```json5
sandbox: {
  docker: {
    network: "bridge"   // default: no network
  }
}
```

Containers run without network by default. Override only when tools genuinely need outbound access.

## Per-Agent Override

```json5
{
  agents: {
    list: [
      {
        id: "clawdia_prime",
        sandbox: { mode: "off" }   // L1 runs unsandboxed
      },
      {
        id: "pumplai_pm",
        sandbox: { mode: "all", workspaceAccess: "rw" }
      }
    ]
  }
}
```

## Build the Sandbox Image

```bash
make docker-l3
# or:
scripts/sandbox-setup.sh            # base sandbox
scripts/sandbox-browser-setup.sh    # + browser support
```

Default image: `openclaw-sandbox:bookworm-slim`

## Key Limitations

- **Tool policies apply before sandbox rules** — allow/deny lists still checked first
- **Elevated execution** bypasses sandbox (runs on host)
- **Skills with `requires.bins`** are checked on host at load time; binary must also exist inside container
- **Memory flush** is skipped when `workspaceAccess: "none"` or `"ro"` (workspace not writable)
- **`skills.entries.*.env`** injects into host process, not sandbox — use `sandbox.docker.env` for sandbox env vars

See [references/sandbox-recipes.md](references/sandbox-recipes.md) for common sandbox configurations.
