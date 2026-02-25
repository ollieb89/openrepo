# Sandbox Configuration Recipes

## Minimal Sandboxed Setup (Recommended Default)

```json5
{
  agents: {
    defaults: {
      sandbox: {
        mode: "non-main",
        scope: "session",
        workspaceAccess: "rw"
      }
    }
  }
}
```

Main agent runs on host (faster, full access). All other sessions sandboxed.

## Maximum Isolation

```json5
{
  agents: {
    defaults: {
      sandbox: {
        mode: "all",
        scope: "session",
        workspaceAccess: "none",
        docker: {
          network: "none"
        }
      }
    }
  }
}
```

No workspace access, no network, new container per session.

## Shared Workspace + Read-Only Source

```json5
{
  agents: {
    defaults: {
      sandbox: {
        mode: "all",
        workspaceAccess: "rw",
        docker: {
          binds: [
            "/home/user/projects:/projects:ro"
          ]
        }
      }
    }
  }
}
```

Agent can write to workspace but only read project files.

## Sandbox with Outbound Network

```json5
{
  agents: {
    defaults: {
      sandbox: {
        mode: "all",
        docker: {
          network: "bridge",
          env: {
            "HTTP_PROXY": "http://proxy.internal:3128"
          }
        }
      }
    }
  }
}
```

## Installing Skill Binaries in Sandbox

If a skill requires a binary (e.g., `uv`, `ffmpeg`), it must exist inside the container:

```json5
{
  agents: {
    defaults: {
      sandbox: {
        docker: {
          setupCommand: "apt-get install -y ffmpeg && pip install uv"
        }
      }
    }
  }
}
```

Or bake it into a custom Dockerfile extending `openclaw-sandbox:bookworm-slim`.

## L3 Container vs Sandbox

| Aspect | L3 Container | Sandbox |
|--------|-------------|---------|
| Purpose | Task execution (ephemeral) | Tool isolation (per session) |
| Initiated by | L2 via spawn.py | Gateway automatically |
| Security | cap_drop ALL, 4GB/1CPU | Same base profile |
| Workspace | `/workspace` (rw) + `/openclaw` (ro) | Configured via `workspaceAccess` |
| Lifetime | Per task | Per session/agent/shared |

Both use the same Docker security profile. L3 containers have task-specific SOUL injection; sandboxed sessions do not.
