# OpenClaw Integration Plan

> Detailed implementation plan for integrating the `openclaw/` agent runtime into the `openrepo` orchestration workspace as a first-class dependency.

**Date**: 2026-03-02
**Status**: Draft
**Scope**: 5 phases across P0–P4 priority tiers

---

## Context

Two distinct but coupled projects coexist in this workspace:

| | Root repo (openrepo) | `openclaw/` subdirectory |
|---|---|---|
| **Role** | Orchestration brain (L1/L2/L3 hierarchy, state engine, project management) | Agent runtime engine (messaging, tool execution, channels, skills) |
| **Tech** | Python 3.10+ (uv), Node.js (router), Next.js 14 (dashboard), Rust/Python (memU) | TypeScript (pnpm), ~370K LOC, Pi framework, Express 5 gateway |
| **Version** | v1.6 | 2026.2.15 |
| **Relationship** | Calls `openclaw` CLI via `execFileSync('openclaw', [...])` in `skills/router/index.js` | IS the `openclaw` CLI that gets invoked |

The root repo's `openclaw.json` is the configuration file consumed by the openclaw runtime. The `extensions/memory-memu/` plugin bridges the root's memU service into the openclaw agent. They are already coupled — this plan formalizes and strengthens that coupling.

### Current Architecture

```
Root repo (L2 host)                          openclaw/ (runtime)
┌──────────────────────────────┐            ┌────────────────────────────────┐
│ L1: ClawdiaPrime             │            │                                │
│   └─ skills/router/index.js ─┼─ CLI ────►│ openclaw agent --agent X       │
│       L2: Project Manager    │            │   └─ Pi agent loop             │
│         └─ skills/spawn/     │            │       └─ sandbox (Docker)      │
│            L3: Docker        │            │       └─ tools                 │
│                              │            │       └─ channels (Telegram…)  │
├──────────────────────────────┤            │                                │
│ state_engine.py (Jarvis)     │            │ src/agents/skills/workspace.ts │
│ packages/dashboard/ (OCCC)   │            │ ui/ (Lit web components)       │
│ packages/memory/ (memU)  ◄───┼── plugin ─┤ memory-memu extension          │
│ openclaw.json ───────────────┼── config ─► reads openclaw.json             │
│ extensions/memory-memu/ ─────┼── bridge ─► /retrieve, /memorize endpoints  │
└──────────────────────────────┘            └────────────────────────────────┘
```

### Integration Contract (how they connect today)

1. **CLI dispatch**: `skills/router/index.js` → `execFileSync('openclaw', ['agent', '--agent', targetId, '--message', directive, '--json'])` with 5-min timeout
2. **Config sharing**: Root's `openclaw.json` defines agents, gateway (port 18789), channels (Telegram), plugins (memory-memu)
3. **State sync**: `skills/spawn/spawn.py` mounts `workspace/.openclaw/<project_id>/workspace-state.json` into L3 containers, protected by `fcntl.flock()`
4. **Memory bridge**: `extensions/memory-memu/` wraps memU REST API; spawn.py pre-fetches memories and injects into L3 SOUL context (2000 char budget)
5. **Volume mounts**: L3 containers get `/workspace` (rw), `/openclaw_src` (ro, orchestration package), `/workspace/.openclaw` (rw, shared state)

---

## Phase 1: Foundation — Git Submodule + Build Wiring

**Priority**: P0 (do first)
**Effort**: ~2 hours
**Risk**: Low

### Rationale

`openclaw/` is currently an untracked directory (`??` in git status). It has its own git remote:
- `origin`: `git@github.com:ollieb89/openclaw.git` (fork)
- `upstream`: `git@github.com:openclaw/openclaw.git` (upstream)

A git submodule formalizes this relationship, pins to a specific commit, and lets openclaw evolve independently while the root repo tracks a known-good version.

### Steps

#### 1.1 — Prepare the workspace

```bash
cd /home/ob/Development/Tools/openrepo

# Stash any uncommitted changes
git stash

# Move openclaw/ out temporarily (submodule add needs a clean target)
mv openclaw /tmp/openclaw-backup
```

#### 1.2 — Add as git submodule

```bash
git submodule add git@github.com:ollieb89/openclaw.git openclaw

# Pin to current commit
cd openclaw
git checkout $(cd /tmp/openclaw-backup && git rev-parse HEAD)
cd ..

# Commit the submodule addition
git add .gitmodules openclaw
git commit -m "chore: add openclaw runtime as git submodule"
```

#### 1.3 — Restore local state

```bash
# Copy any local-only files (untracked in openclaw's git) from backup
# Example: local config overrides, .env files
diff -rq /tmp/openclaw-backup openclaw --exclude=.git | grep "Only in /tmp"
# Manually copy anything needed, then:
rm -rf /tmp/openclaw-backup
```

#### 1.4 — Update Makefile

Add these targets to the existing Makefile:

```makefile
# --- Submodule Management ---

submodule-init: ## Initialize and update git submodules
	git submodule update --init --recursive

submodule-update: ## Pull latest from openclaw submodule remote
	cd openclaw && git fetch origin && git checkout origin/main
	@echo "Remember to commit the submodule pointer: git add openclaw && git commit"

# --- OpenClaw Runtime ---

openclaw-install: ## Install openclaw runtime dependencies
	cd openclaw && pnpm install --frozen-lockfile

openclaw-build: ## Build the openclaw runtime
	cd openclaw && pnpm build

openclaw-link: ## Make 'openclaw' CLI available on PATH (via pnpm link)
	cd openclaw && pnpm link --global

# --- Unified Setup ---

setup: submodule-init openclaw-install openclaw-build openclaw-link dev ## Full workspace setup from scratch
	@echo "Setup complete. 'openclaw' CLI is on PATH. Orchestration package installed."

# --- Unified Dev ---

dev-all: dev ## Start all dev services (orchestration + dashboard)
	@echo "Orchestration installed. Run 'make dashboard' in another terminal for OCCC."
```

#### 1.5 — Update .PHONY

```makefile
.PHONY: help dev test lint dashboard memory clean \
        submodule-init submodule-update \
        openclaw-install openclaw-build openclaw-link \
        setup dev-all
```

#### 1.6 — Add PATH hint to shell profile (optional)

For development without `pnpm link --global`, add to the project's `.envrc` (if using direnv) or document:

```bash
export PATH="$(pwd)/openclaw/node_modules/.bin:$PATH"
```

### Validation

| Check | Command | Expected |
|---|---|---|
| Submodule registered | `git submodule status` | Shows openclaw/ with pinned commit hash |
| Dependencies installed | `cd openclaw && pnpm ls --depth 0` | No errors, packages listed |
| Build succeeds | `cd openclaw && pnpm build` | Exit 0, `dist/` populated |
| CLI available | `openclaw --version` | Prints version (2026.2.15 or similar) |
| Full setup from clone | `git clone --recursive <repo> && cd openrepo && make setup` | All targets succeed |
| Router can dispatch | `node skills/router/index.js main "echo test"` | No "command not found" error |

### Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| `pnpm link --global` conflicts with system openclaw | PATH resolution picks wrong binary | Use `$(pwd)/openclaw/node_modules/.bin` PATH prepend instead |
| Submodule update breaks root repo | Orchestration calls fail | Pin submodule to tested commits; update deliberately |
| Contributors forget `--recursive` on clone | openclaw/ dir empty | `make setup` runs `submodule-init` first; document in README |

---

## Phase 2: Skills Bridge — Unified Skill Loading

**Priority**: P1 (high)
**Effort**: ~3 hours
**Risk**: Medium (skill name collisions possible)
**Depends on**: Phase 1

### Rationale

Both projects have `skills/` directories with SKILL.md files in compatible formats:

| Aspect | Root skills (36) | openclaw bundled skills (51+) |
|---|---|---|
| **Purpose** | Orchestration methodology (spawn, router, review, TDD, brainstorming) | Agent capabilities (github, slack, weather, coding-agent) |
| **Format** | YAML frontmatter (`name`, `description`) + markdown body | YAML frontmatter (`name`, `description`, `metadata.openclaw`) + markdown body |
| **Location** | `skills/` | `openclaw/skills/` |

The openclaw skill loader (`src/agents/skills/workspace.ts`) supports **`config.skills.load.extraDirs`** — an array of additional directories to scan for skills. This is the clean integration path.

### Skill Loading Order (openclaw runtime)

1. Bundled skills (`openclaw/skills/` or `OPENCLAW_BUNDLED_SKILLS_DIR`)
2. **Extra dirs** (`config.skills.load.extraDirs[]`) ← we add root skills here
3. Managed skills (`~/.config/openclaw/skills/`)
4. Personal agent skills (`~/.agents/skills/`)
5. Project agent skills (`<workspace>/.agents/skills/`)
6. Workspace skills (`<workspace>/skills/`)

### Steps

#### 2.1 — Audit for name collisions

```bash
# Find skills that exist in both directories
comm -12 \
  <(ls skills/ | sort) \
  <(ls openclaw/skills/ | sort)
```

Known collision: `gog` exists in both. Resolve by:
- Renaming root's `gog` to `oc-gog` (orchestration-specific), OR
- Keeping both and letting openclaw's precedence rules handle it (bundled wins)

#### 2.2 — Add extraDirs to openclaw.json

Add the `skills.load` configuration block:

```json
{
  "skills": {
    "load": {
      "extraDirs": [
        "./skills"
      ]
    }
  }
}
```

The path is relative to the workspace root (where `openclaw.json` lives).

#### 2.3 — Add metadata.openclaw to root skills (optional, improves UX)

For each root skill that should appear in the openclaw skill list with proper metadata, add the `metadata.openclaw` block to the YAML frontmatter:

```yaml
---
name: openclaw-orchestrate
description: Multi-tier agent orchestration in OpenClaw's L1→L2→L3 hierarchy.
metadata:
  openclaw:
    emoji: "🏗️"
    category: "orchestration"
---
```

Priority skills to enhance:
- `openclaw-orchestrate` — core orchestration skill
- `openclaw-spawn-l3` — L3 container management
- `openclaw-review` — diff review
- `openclaw-heartbeat` — health monitoring
- `router` — L1→L2 dispatch
- `spawn` — L2→L3 spawning

#### 2.4 — Create skill categories manifest

Create `skills/MANIFEST.json` to document which skills belong to orchestration vs general:

```json
{
  "categories": {
    "orchestration-core": [
      "router",
      "spawn",
      "review",
      "openclaw-orchestrate",
      "openclaw-spawn-l3",
      "openclaw-heartbeat",
      "openclaw-review"
    ],
    "orchestration-methodology": [
      "brainstorming",
      "executing-plans",
      "test-driven-development",
      "verification-before-completion",
      "subagent-driven-development",
      "systematic-debugging",
      "self-improving-agent"
    ],
    "multi-agent": [
      "multi-agent",
      "dispatching-parallel-agents",
      "pumplai_delegation"
    ],
    "integration": [
      "notion-kanban-sync",
      "openclaw-memory-system",
      "openclaw-models",
      "notebooklm"
    ]
  }
}
```

#### 2.5 — Scope orchestration-only skills

Some root skills (like `spawn`, `router`) depend on the Python orchestration package (`from openclaw.X import Y`). These should only be invoked by L2 agents, not general openclaw agents.

Options:
1. Add `metadata.openclaw.requires.packages: ["openclaw"]` so the skill loader can gate them
2. Use agent-specific skill allowlists in `openclaw.json` agent config
3. Add `metadata.openclaw.agentScope: ["clawdia_prime", "pumplai_pm"]` to restrict visibility

Recommended: Option 2 — add a `skills.allowlist` or `skills.blocklist` per agent in `openclaw.json`:

```json
{
  "agents": {
    "list": [
      {
        "id": "main",
        "name": "Central Core",
        "skills": {
          "include": ["*"],
          "exclude": ["spawn", "router", "review"]
        }
      },
      {
        "id": "clawdia_prime",
        "name": "Head of Development",
        "skills": {
          "include": ["*"]
        }
      }
    ]
  }
}
```

### Validation

| Check | Command | Expected |
|---|---|---|
| No name collisions | `comm -12 <(ls skills/ \| sort) <(ls openclaw/skills/ \| sort)` | Collisions resolved or documented |
| Config valid | `python -m json.tool openclaw.json` | Valid JSON with `skills.load.extraDirs` |
| Skills loaded | `openclaw skills list` | Shows both bundled AND orchestration skills |
| Scoping works | Run as `main` agent → spawn skill not offered | Skill exclusions respected |

### Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Skill name collision (`gog`) | Wrong skill loaded | Rename root's conflicting skills with `oc-` prefix |
| Orchestration skills invoked without Python env | Runtime error | Add `requires` metadata; scope skills to L2 agents only |
| `extraDirs` path resolution differs across environments | Skills not found | Use relative path `./skills` (relative to config file location) |

---

## Phase 3: Memory Consolidation — Document & Harden

**Priority**: P2 (medium)
**Effort**: ~1 hour
**Risk**: Low (already working)
**Depends on**: Phase 1

### Rationale

Memory integration is already functional:
- `openclaw.json` configures `memory-memu` plugin → `extensions/memory-memu/`
- memU extension wraps the REST API from `packages/memory/`
- SQLite storage at `memory/*.sqlite` (per-agent)
- `spawn.py` pre-fetches memories and injects into L3 SOUL context

No structural changes needed. This phase is about hardening and documentation.

### Steps

#### 3.1 — Add memory health check to Makefile

```makefile
memory-health: ## Check memU service health (port 18791; override via MEMU_API_URL)
	@url="$${MEMU_API_URL:-http://localhost:18791}"; \
	curl -sf "$$url/health" > /dev/null 2>&1 \
		&& echo "memU service: healthy" \
		|| echo "memU service: not running (start with 'make memory-up')"
```

#### 3.2 — Ensure config paths are portable

Audit `extensions/memory-memu/openclaw.plugin.json` to confirm:
- No hardcoded absolute paths
- SQLite storage paths derive from `OPENCLAW_ROOT` or workspace-relative paths
- memU API URL is configurable via environment variable

#### 3.3 — Document the memory architecture

Add a section to CLAUDE.md (or this plan's appendix) documenting:
- Memory flow: agent action → memU `/memorize` → SQLite + embeddings → retrieval → SOUL injection
- Storage locations: `memory/*.sqlite` per-agent files
- Config: `openclaw.json` → `plugins.entries.memory-memu.config`
- Extension: `extensions/memory-memu/` (TypeScript wrapper → Python memU)

### Validation

| Check | Command | Expected |
|---|---|---|
| memU starts | `make memory-up && make memory-health` | "healthy" |
| Memory persists across restarts | `make memory-down && make memory-up && curl localhost:18791/health` | Service recovers, data intact |
| L3 gets memory context | Spawn a test L3 → check `/run/openclaw/soul.md` | Memory section present in SOUL |

---

## Phase 4: Dashboard Linking — Unified Developer Experience

**Priority**: P3 (medium)
**Effort**: ~4 hours
**Risk**: Low-Medium
**Depends on**: Phase 1

### Rationale

Two dashboards serve different roles:
- **OCCC** (`packages/dashboard/`, port 6987): Orchestration visibility — L3 pool, task boards, escalations, autonomy dashboard
- **openclaw UI** (`openclaw/ui/`, served via gateway on port 18789): Agent runtime — conversations, channels, skill management

For developer experience, both should be easily accessible and cross-linked.

### Steps

#### 4.1 — Add unified dev command

Update Makefile to start both services:

```makefile
dev-dashboard: dashboard ## Start OCCC dashboard (port 6987)

dev-services: ## Start all background services (memU + dashboards)
	@echo "Starting memU..."
	$(MAKE) memory-up
	@echo "Starting OCCC dashboard on :6987..."
	cd packages/dashboard && bun run dev &
	@echo "All services started. OpenClaw gateway available on :18789"
```

#### 4.2 — Add cross-links in OCCC dashboard

Add navigation links in the OCCC sidebar/header pointing to the openclaw gateway UI:

```typescript
// packages/dashboard/src/components/Navigation.tsx
const externalLinks = [
  { label: "Agent Runtime", href: "http://localhost:18789", icon: BotIcon },
];
```

#### 4.3 — Add OCCC link in openclaw gateway (optional)

If openclaw supports custom navigation via config or plugin:
- Add a link to `http://localhost:6987` in the openclaw UI
- Or document it in the openclaw MOTD/welcome message

**Note:** OCCC cross-links to the openclaw gateway from the sidebar. For the reverse direction, developers can manually open OCCC at `http://localhost:6987` or add a link in the openclaw UI if/when config-based external links are supported.

#### 4.4 — Gateway proxy for OCCC (future, optional)

Add a proxy route in the openclaw gateway to forward OCCC requests:

```typescript
// In openclaw gateway config or extension
app.use('/occc', createProxyMiddleware({
  target: 'http://localhost:6987',
  changeOrigin: true,
  pathRewrite: { '^/occc': '' }
}));
```

This unifies access under a single port (18789) but adds complexity. Defer unless needed.

### Validation

| Check | Command | Expected |
|---|---|---|
| Both dashboards start | `make dev-services` | OCCC on :6987, gateway on :18789 |
| Cross-links work | Click "Agent Runtime" in OCCC | Opens openclaw gateway UI |
| Independent operation | Stop one, other continues | No crashes or dependency |

---

## Phase 5: Docker Image Sharing — Unified Base Images

**Priority**: P4 (low)
**Effort**: ~3 hours
**Risk**: Medium (container behavior changes)
**Depends on**: Phase 1

### Rationale

Both projects build Docker images from `debian:bookworm-slim` with overlapping package sets:

| Package | L3 Specialist | openclaw Sandbox | openclaw Sandbox-Common |
|---|---|---|---|
| bash | via slim | yes | yes |
| git | yes | yes | yes |
| python3 | yes | yes | yes |
| curl | yes | yes | yes |
| jq | yes | yes | yes |
| ripgrep | no | yes | yes |
| Node.js | no | no | yes |
| Go | no | no | yes |
| Rust | no | no | yes |
| pip/jsonschema | yes | no | no |
| **User** | l3worker (1000) | sandbox | configurable (FINAL_USER) |
| **CMD** | entrypoint.sh | sleep infinity | sleep infinity |

### Steps

#### 5.1 — Adopt openclaw sandbox as L3 base

Update `docker/l3-specialist/Dockerfile`:

```dockerfile
ARG BASE_IMAGE=openclaw-sandbox:bookworm-slim
FROM ${BASE_IMAGE}

# L3-specific additions
RUN pip3 install --no-cache-dir jsonschema

# Health check sentinel
HEALTHCHECK --interval=30s --timeout=5s \
  CMD test -f /tmp/openclaw-healthy || exit 1

# Copy entrypoint
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Override user to match L3 conventions
ARG L3_USER=l3worker
RUN useradd -m -u 1000 ${L3_USER} 2>/dev/null || true
USER ${L3_USER}
WORKDIR /workspace

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
```

#### 5.2 — Add shared base build to Makefile

```makefile
docker-sandbox-base: ## Build openclaw sandbox base image
	cd openclaw && docker build -f Dockerfile.sandbox -t openclaw-sandbox:bookworm-slim .

docker-sandbox-common: docker-sandbox-base ## Build openclaw sandbox-common image
	cd openclaw && docker build -f Dockerfile.sandbox-common -t openclaw-sandbox-common:bookworm-slim .

docker-l3: docker-sandbox-base ## Build L3 specialist container image (depends on sandbox base)
	docker build -t openclaw-l3-specialist:latest docker/l3-specialist/

docker-all: docker-sandbox-base docker-sandbox-common docker-l3 ## Build all Docker images
```

#### 5.3 — Update spawn.py image reference (if needed)

If the image name changes, update `skills/spawn/spawn.py`:

```python
container_config = {
    "image": l3_config.get("container", {}).get("image", "openclaw-l3-specialist:latest"),
    ...
}
```

Ensure `l3_overrides.container.image` in project configs can override the default.

### Validation

| Check | Command | Expected |
|---|---|---|
| Base image builds | `make docker-sandbox-base` | Image tagged `openclaw-sandbox:bookworm-slim` |
| L3 image builds on top | `make docker-l3` | Image tagged `openclaw-l3-specialist:latest` |
| L3 container starts | `docker run --rm openclaw-l3-specialist:latest whoami` | Prints `l3worker` |
| Spawn works end-to-end | `python3 skills/spawn/spawn.py test-001 code "test" --dry-run` | No image errors |
| Existing tasks unaffected | Run a real L3 task | Task completes successfully |

### Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Different package versions in new base | L3 entrypoint breaks | Run L3 test suite against new image before merging |
| User UID mismatch | Permission errors on mounted volumes | Both use UID 1000; verify with `id` in container |
| Larger image size (ripgrep, extra packages) | Slower pulls | Acceptable trade-off; saves maintaining two base images |

---

## Implementation Timeline

```
Week 1
├── Phase 1: Git submodule + Makefile wiring (2h)
│   ├── Day 1: Submodule add + Makefile update
│   └── Day 1: Validation + CLAUDE.md update
│
├── Phase 2: Skills bridge (3h)
│   ├── Day 2: Audit collisions + add extraDirs config
│   ├── Day 2: Metadata enhancement + manifest
│   └── Day 3: Agent scoping + validation
│
└── Phase 3: Memory hardening (1h)
    └── Day 3: Health check + documentation

Week 2
├── Phase 4: Dashboard linking (4h)
│   ├── Day 4: Unified Makefile targets
│   └── Day 4: Cross-links + validation
│
└── Phase 5: Docker unification (3h)
    ├── Day 5: Update Dockerfiles + Makefile
    └── Day 5: End-to-end L3 testing
```

**Total estimated effort**: ~13 hours across 5 days

---

## Success Criteria

### Phase 1 (Foundation)
- [ ] `git clone --recursive` produces a complete workspace
- [ ] `make setup` installs everything from scratch
- [ ] `openclaw --version` works from the root directory
- [ ] `node skills/router/index.js` can dispatch to agents

### Phase 2 (Skills)
- [ ] `openclaw skills list` shows orchestration skills from root `skills/`
- [ ] No skill name collisions remain
- [ ] Orchestration-only skills are scoped to L2 agents

**Note:** OpenClaw loads config from `~/.openclaw/openclaw.json` by default. To see root skills:

1. **Use repo config** (requires OPENCLAW_TELEGRAM_BOT_TOKEN, OPENCLAW_GATEWAY_TOKEN, etc.):
   ```bash
   OPENCLAW_CONFIG_PATH="$(pwd)/openclaw.json" openclaw skills list
   # or: make openclaw-skills
   ```

2. **Merge into your config** — add to `~/.openclaw/openclaw.json`:
   ```json
   "skills": {
     "load": {
       "extraDirs": ["/path/to/openrepo/skills"]
     }
   }
   ```
   Use an absolute path so it works regardless of cwd.

### Phase 3 (Memory)
- [ ] `make memory-health` reports service status
- [ ] Memory injection works in L3 SOUL context

### Phase 4 (Dashboard)
- [x] `make dev-services` starts memU + OCCC dashboard
- [x] Cross-link in OCCC sidebar: "Agent Runtime" → openclaw gateway (:18789)

### Phase 5 (Docker)
- [ ] L3 image builds from openclaw sandbox base
- [ ] Existing L3 tasks pass with the new image
- [ ] Single `make docker-all` builds the full image chain

---

## Appendix A: File Changes Summary

| File | Change | Phase |
|---|---|---|
| `.gitmodules` | Add openclaw submodule entry | 1 |
| `Makefile` | Add 10+ new targets | 1, 3, 4, 5 |
| `CLAUDE.md` | Document submodule workflow | 1 |
| `openclaw.json` | Add `skills.load.extraDirs` | 2 |
| `skills/MANIFEST.json` | New — skill categories | 2 |
| `skills/gog/SKILL.md` | Rename to `oc-gog` or resolve collision | 2 |
| `skills/*/SKILL.md` (6 files) | Add `metadata.openclaw` frontmatter | 2 |
| `extensions/memory-memu/openclaw.plugin.json` | Audit paths for portability | 3 |
| `packages/dashboard/src/components/` | Add external navigation links | 4 |
| `docker/l3-specialist/Dockerfile` | Rebase on openclaw-sandbox | 5 |

## Appendix B: Environment Variables

| Variable | Used by | Purpose |
|---|---|---|
| `OPENCLAW_ROOT` | config.py, dashboard | Project root path (default: `~/.openclaw`) |
| `OPENCLAW_PROJECT` | config.py, spawn.py | Active project ID |
| `OPENCLAW_STATE_FILE` | state_engine.py (L3) | State file path inside containers |
| `OPENCLAW_BUNDLED_SKILLS_DIR` | workspace.ts | Override bundled skills location |
| `OPENCLAW_GATEWAY_TOKEN` | openclaw.json | Gateway auth token |
| `OPENCLAW_TELEGRAM_BOT_TOKEN` | openclaw.json | Telegram channel token |
| `GEMINI_API_KEY` | openclaw.json | Memory plugin API key |
| `MEMU_API_URL` | spawn.py (L3) | memU service endpoint for containers |

## Appendix C: Port Allocation

| Port | Service | Owner |
|---|---|---|
| 6987 | OCCC Dashboard | packages/dashboard (Next.js) |
| 18791 | memU REST API | packages/memory (FastAPI) |
| 18789 | OpenClaw Gateway | openclaw/ (Express 5) |

## Appendix D: Skill Format Comparison

### Root skill format (minimal)
```yaml
---
name: openclaw-orchestrate
description: Multi-tier agent orchestration in OpenClaw's L1→L2→L3 hierarchy.
---
# OpenClaw Multi-Tier Orchestration
...
```

### openclaw skill format (full)
```yaml
---
name: github
description: "Interact with GitHub using the `gh` CLI."
metadata:
  openclaw:
    emoji: "🐙"
    requires:
      bins: ["gh"]
    install:
      - id: brew
        kind: brew
        formula: gh
        bins: ["gh"]
        label: "Install GitHub CLI (brew)"
---
# GitHub Skill
...
```

The root format is a valid subset — `metadata.openclaw` is optional. Root skills will load without modification; adding metadata improves discoverability.
