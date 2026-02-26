# Phase 2: Source Connectivity & Incremental Sync - Research

**Researched:** 2026-02-24
**Domain:** Slack + tracker connectivity, incremental sync cursors, resumable jobs, and connector health telemetry
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
### Incremental Sync Behavior
- First sync must be user-scoped by time window, not forced full backfill. Provide a selectable window at setup (for example, last 30/90/all days) with a safe default favoring controlled initial load.
- Changed-record detection must include updates to existing records, not only newly created items (edits, state changes, reopen/close transitions, and newly added comments/messages).
- Sync operation must support both automatic periodic runs and a manual `Sync now` trigger.
- Interrupted sync must resume from the last confirmed checkpoint/cursor and avoid duplicate ingestion.
- Cursor/watermark semantics should be source-aware (Slack timestamp/thread cursor style; tracker `updated_at` style).

### Sync Progress Visibility
- Show sync status in two places: a dedicated sync dashboard and a compact always-visible status indicator in primary UI.
- Progress reporting should include per-connector and per-source counters; do not rely solely on percent-complete bars when total work is unknown.
- For long-running syncs, show persistent active-state progress with current step and throughput; ETA is best-effort only and must tolerate rate-limit variance.
- Completion/failure feedback must include transient notification plus persistent status card with actionable recovery controls.

### Health Status Semantics
- Connector state model is explicitly: `connected`, `syncing`, `rate_limited`, `auth_expired`, `error`, `disconnected`.
- Any provider 429 response should immediately transition connector state to `rate_limited` with pause/backoff behavior.
- Backoff policy should consume provider `Retry-After` when present; otherwise use exponential fallback windows.
- `auth_expired` is a hard block: stop sync, show explicit re-auth call-to-action, and retain last-successful-sync metadata for user reassurance.
- Status priority order is fixed for UI and action routing: `auth_expired` > `error` > `rate_limited` > `syncing` > `connected`.
- Compact status may use traffic-light semantics for glanceability (green healthy, blue syncing, yellow rate-limited, red action required).

### Claude's Discretion
- Exact visual treatment (icons, spacing, typography, card composition) for dashboard and compact indicators.
- Precise polling interval for periodic syncs, provided behavior remains consistent with the decisions above.
- Detailed wording of helper text/tooltips for progress and health states.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INTG-01 | Connect one Slack workspace and sync selected channels. | Slack OAuth + `conversations.list`/`conversations.history` with channel-scoped tokens and cursor pagination. |
| INTG-02 | Connect one project tracker (GitHub Issues or Linear) and sync issue metadata. | Provider abstraction with GitHub `issues` since cursor + Linear GraphQL pagination by `updatedAt`. |
| INTG-03 | Incremental sync only processes net-new/changed records after first import. | Persist per-source cursors/checkpoints + idempotent upsert keyed by source ID and updated timestamp. |
| INTG-04 | Connector health shows connected/rate-limited/auth-expired. | Health state machine driven by HTTP status classes (`401/403`, `429`, `5xx`) and backoff scheduling. |
| PERF-02 | Initial sync progress visible and resumable after interruption. | Job progress snapshots + resumable cursor checkpoints + UI progress cards and compact indicator. |
</phase_requirements>

## Summary
Phase 2 should be planned around a connector runtime contract, not connector-specific one-off flows. The contract needs three first-class concerns: per-provider auth/config, resumable incremental cursors, and normalized health/progress signals consumable by UI.

Slack and tracker providers should share a single sync engine shape (`connect`, `discover scope`, `sync since cursor`, `classify health`) while keeping source-specific cursor semantics (Slack timestamp/cursor pagination vs tracker `updated_at`). This avoids duplicating failure handling and makes phase 3/4 features consume one unified change feed.

The highest risk in this phase is hidden state drift: sync appearing "healthy" while cursors are stale or repeatedly restarting from scratch. Plans should enforce persistent checkpoints at each completed page/chunk and idempotent ingestion to keep resume safe.

**Primary recommendation:** Build a unified connector + sync state machine first, then implement Slack and tracker adapters on top, and wire health/progress to both dashboard and compact indicator.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `@slack/web-api` | current | Slack API client with cursor pagination and Web API error handling | Official SDK with typed methods and rate-limit metadata handling. |
| `octokit` (`@octokit/rest`) | current | GitHub Issues metadata sync via REST | Official GitHub client with pagination and retry ecosystem support. |
| Native `fetch` (Node 18+/Next 14 runtime) | current | Linear GraphQL calls and connector health probes | Already in stack, no extra runtime dependency needed. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `p-retry` | current | Exponential retry/backoff wrapper | Apply for transient `5xx` and network failures (not auth expiry). |
| `p-queue` | current | Controlled concurrency per connector/source | Prevent API bursts and simplify throughput accounting. |
| `zod` | current | Connector payload validation before persistence | Validate external API records before upsert and checkpoint advance. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Native `fetch` for Linear | `graphql-request` | Cleaner query client but adds dependency; not required for one provider. |
| `p-retry` + custom rate-limit parser | SDK-native retries only | Less code, but weaker cross-provider consistency for state transitions. |
| Single generic cursor type | Provider-specific cursor payloads | Generic type simpler short-term, but loses source-aware resume semantics. |

**Installation:**
```bash
npm install @slack/web-api @octokit/rest p-retry p-queue zod
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── lib/connectors/                 # Provider adapters and contracts
│   ├── types.ts                    # Connector + health + cursor contracts
│   ├── slack.ts                    # Slack adapter
│   ├── tracker-github.ts           # GitHub tracker adapter
│   └── tracker-linear.ts           # Linear tracker adapter
├── lib/sync/
│   ├── engine.ts                   # Incremental/resumable sync orchestration
│   ├── checkpoints.ts              # Cursor persistence + resume loading
│   └── health.ts                   # Error/status classification and priority
├── app/api/connectors/             # Connect/disconnect/sync now endpoints
└── components/connectors/          # Dashboard + compact status indicator
```

### Pattern 1: Connector Contract + Adapter Implementations
**What:** Define one adapter interface each provider must implement (`connect`, `syncIncremental`, `classifyError`).
**When to use:** All Slack and tracker ingestion paths.
**Example:**
```typescript
export type ConnectorHealth = 'connected' | 'syncing' | 'rate_limited' | 'auth_expired' | 'error' | 'disconnected';

export interface SyncCursor {
  source: 'slack' | 'github' | 'linear';
  value: string;
  updatedAt: string;
}

export interface ConnectorAdapter {
  syncIncremental(input: { cursor?: SyncCursor; window: '30d' | '90d' | 'all' }): Promise<{
    records: unknown[];
    nextCursor?: SyncCursor;
    counters: { scanned: number; changed: number; upserted: number };
  }>;
}
```

### Pattern 2: Checkpoint-After-Commit Resume
**What:** Advance cursor only after a page/chunk has been persisted successfully.
**When to use:** Every provider page loop.
**Example:**
```typescript
for (const page of pages) {
  await upsertRecords(page.records);        // idempotent write
  await saveCheckpoint(page.nextCursor);    // checkpoint only after write success
}
```

### Pattern 3: Health State Machine with Priority
**What:** Normalize provider errors into required UI states with fixed priority.
**When to use:** API call failures and background sync scheduler decisions.
**Example:**
```typescript
function classifyHealth(status?: number): ConnectorHealth {
  if (status === 401 || status === 403) return 'auth_expired';
  if (status === 429) return 'rate_limited';
  if (!status || status >= 500) return 'error';
  return 'connected';
}
```

### Anti-Patterns to Avoid
- **Advancing cursor before persistence:** causes data loss on crash/restart.
- **Using one global cursor across multiple channels/repos:** breaks incremental guarantees.
- **Treating all errors as generic `error`:** hides required re-auth/rate-limit actions.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Slack API pagination and auth headers | Manual HTTP wrappers everywhere | `@slack/web-api` methods | Official SDK handles method contracts and response shape drift better. |
| Backoff timing math in every adapter | Per-file retry loops | `p-retry` + shared policy utility | Keeps 429/5xx handling consistent and testable. |
| Ad-hoc JSON shape assumptions | Blindly trust provider payloads | `zod` validation at adapter edge | Prevents bad payloads from corrupting checkpoints/store. |

**Key insight:** Resumable incremental sync succeeds or fails on checkpoint correctness and idempotency discipline, not on connector API call volume.

## Common Pitfalls

### Pitfall 1: Slack history replay duplicates after restart
**What goes wrong:** Restart reprocesses previously ingested messages due to cursor mismatch.
**Why it happens:** Cursor persisted per run instead of per channel + timestamp boundary.
**How to avoid:** Store checkpoint at connector+source scope and upsert by stable source IDs.
**Warning signs:** Changed counter spikes after restarts without new source activity.

### Pitfall 2: Tracker updates missed when using creation time instead of update time
**What goes wrong:** Edited/reopened issues are skipped.
**Why it happens:** Cursor keyed to `created_at` instead of `updated_at` semantics.
**How to avoid:** Use provider update-time filters/cursors and include comments/activity when required.
**Warning signs:** Issues show recent UI activity but no ingestion delta.

### Pitfall 3: 429 handling does not transition health state
**What goes wrong:** UI still shows `connected` while sync silently backs off or fails.
**Why it happens:** Retry logic disconnected from health state model.
**How to avoid:** On first 429, set `rate_limited`, persist `retryAfter`, and expose to dashboard/indicator.
**Warning signs:** Frequent retries with no visible status change.

### Pitfall 4: Auth expiry treated as transient error
**What goes wrong:** System repeatedly retries invalid token without user action.
**Why it happens:** 401/403 routed through generic retry policy.
**How to avoid:** Hard-stop on auth errors, mark `auth_expired`, expose re-auth CTA.
**Warning signs:** Repeating 401 loops and no reconnect prompt.

## Code Examples

### Slack cursor pagination and channel history retrieval
```typescript
import { WebClient } from '@slack/web-api';

const client = new WebClient(process.env.SLACK_BOT_TOKEN);
const history = await client.conversations.history({
  channel,
  oldest,
  cursor,
  limit: 200,
});
```
Source: https://api.slack.com/web

### GitHub incremental issue listing via `since`
```typescript
await octokit.rest.issues.listForRepo({
  owner,
  repo,
  since: lastSyncIso,
  per_page: 100,
});
```
Source: https://octokit.github.io/rest.js/v22/

### Linear issue pagination by `updatedAt`
```graphql
query Issues($after: String, $updatedAt: DateTimeOrDuration) {
  issues(after: $after, filter: { updatedAt: { gte: $updatedAt } }) {
    nodes { id identifier title updatedAt state { name } }
    pageInfo { hasNextPage endCursor }
  }
}
```
Source: https://linear.app/developers/graphql

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Full replay sync on interval | Incremental cursor-based sync + resume checkpoints | Lower API cost and faster steady-state sync. |
| Hidden background status | Always-visible compact + detailed dashboard status | Better operator confidence and faster issue recovery. |
| Single generic error status | Explicit auth/rate-limit/error health model | Clear user actions and better supportability. |

## Open Questions

1. Should project tracker choice be fixed per project (GitHub or Linear) or swappable with migration?
2. Should first-sync default window be `30d` or `90d` for this product's expected history depth?
3. Do we need connector-level dead-letter logging for malformed provider records in v1, or can we fail fast with surfaced error cards?

## Sources

### Primary (HIGH confidence)
- Slack API docs and Web API references: https://api.slack.com/web
- Slack rate limits: https://api.slack.com/apis/rate-limits
- GitHub REST best practices and pagination: https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api
- GitHub REST pagination guide: https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api
- Linear GraphQL reference and auth: https://linear.app/developers/graphql
- Linear API intro: https://linear.app/developers
- In-repo planning context:
  - `.planning/ROADMAP.md`
  - `.planning/REQUIREMENTS.md`
  - `.planning/STATE.md`
  - `.planning/phases/02-source-connectivity-incremental-sync/02-CONTEXT.md`

### Secondary (MEDIUM confidence)
- Octokit REST client usage docs: https://octokit.github.io/rest.js/v22/

## Metadata

**Confidence breakdown:**
- Connector contracts and sync patterns: HIGH
- Provider API semantics (Slack/GitHub/Linear): HIGH
- Implementation package selection in this codebase: MEDIUM

**Research date:** 2026-02-24
**Valid until:** 2026-03-24
