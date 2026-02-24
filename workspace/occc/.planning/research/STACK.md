# Nexus-Sync 2026 Stack Recommendations (Local-First Desktop Context Bridge)

## Scope and Assumptions
- Focus: MVP for Slack + GitHub/Linear context sync and natural-language catch-up.
- Runtime target: Desktop agent with Rust/Tauri, privacy-by-default, low overhead.
- Product constraint: No customer-data training; local processing preferred.
- Recommendation style: practical picks that reduce operational complexity in first year.

## Confidence Legend
- `HIGH`: Mature in production, strong ecosystem fit, low migration risk.
- `MED`: Good fit with some integration or maintenance risk.
- `LOW`: Promising but still volatile for this product stage.

## Recommended Core Architecture
- Desktop shell: `Tauri v2` + Rust backend + minimal web UI (`HIGH`).
- Internal process model: single Rust supervisor + async workers (`tokio`) (`HIGH`).
- Data model: append-only local event log + derived materialized views (`HIGH`).
- Sync model: connector-specific pull/webhook hybrid with local idempotent merge (`HIGH`).
- AI boundary: local retrieval first, optional remote LLM behind explicit consent (`HIGH`).

## Desktop and Agent Runtime (Rust/Tauri)
- `tauri` + `tauri-build` + `tauri-plugin-log` for packaging and diagnostics (`HIGH`).
- `tokio` for concurrency; use bounded queues to prevent runaway background work (`HIGH`).
- `tracing` + `tracing-subscriber` for structured logs and span-level perf visibility (`HIGH`).
- `serde`/`serde_json` for normalized event payloads (`HIGH`).
- `reqwest` with connector-specific rate-limit middleware (`HIGH`).
- `sqlx` (SQLite) for typed queries and migration safety (`HIGH`).
- `thiserror` + `anyhow` pattern: typed domain errors, ergonomic app-level propagation (`HIGH`).

## Local Storage and Search
- Primary store: `SQLite` in WAL mode for reliability and low overhead (`HIGH`).
- Full-text fallback: `SQLite FTS5` for keyword search and debugging paths (`HIGH`).
- Vector store (default): `Qdrant` embedded/local mode for ANN + filtering (`MED`).
- Vector store (lean option): `sqlite-vec` if footprint matters more than ANN performance (`MED`).
- Metadata and ACL tags should live alongside embeddings for policy-safe retrieval (`HIGH`).
- Use deterministic chunk IDs (source+thread+message hash) for idempotent upserts (`HIGH`).

## Embeddings and RAG Pipeline
- Local embeddings first: `bge-small-en-v1.5`/successor via `candle` or `onnxruntime` (`MED`).
- Higher-quality local option: `nomic-embed-text` class models if device budget allows (`MED`).
- Chunking strategy: conversation-window aware chunks, not fixed token windows (`HIGH`).
- Reranking: lightweight local reranker only for top-k if latency budget permits (`MED`).
- Keep retrieval policy explicit: per-source ACL filter before similarity search (`HIGH`).

## Integrations: Slack + GitHub + Linear
- Slack: official Web API + Events API + granular OAuth scopes only (`HIGH`).
- GitHub: GraphQL for issue/PR context; REST fallback for edge endpoints (`HIGH`).
- Linear: GraphQL API with incremental sync cursor checkpoints (`HIGH`).
- Connector contract: `pull_since(cursor)`, `normalize()`, `upsert_idempotent()` (`HIGH`).
- Backoff/rate limit: token bucket + jittered retries per provider policy (`HIGH`).
- Use source-native IDs as immutable foreign keys; never rewrite canonical refs (`HIGH`).

## Privacy and Security by Default
- Local-first policy: raw content remains local unless user explicitly enables remote assist (`HIGH`).
- Secret handling: OS keychain (`keyring` crate) for OAuth tokens and encryption keys (`HIGH`).
- At-rest protection: `sqlcipher` or file-level encryption for sensitive local DBs (`MED`).
- In-transit: TLS pinning where feasible; strict cert validation and hostname checks (`HIGH`).
- Data minimization: store only fields required for retrieval and linking (`HIGH`).
- Auditable controls: local policy log for “what was indexed/sent and why” (`HIGH`).

## UI and Product Surface
- UI stack inside Tauri: `React` + `TypeScript` + lightweight component set (`HIGH`).
- Main UX: command palette + “Catch Me Up” view + link suggestions with approve/reject (`HIGH`).
- Keep rendering thin; move heavy transforms to Rust commands (`HIGH`).
- Offline-first UX: stale indicators and explicit “last synced” timestamps (`HIGH`).

## Observability and Quality
- Local metrics: ingest lag, queue depth, embedding latency, retrieval hit rate (`HIGH`).
- Crash/error reporting: local-first crash bundle export, user-controlled share flow (`HIGH`).
- Contract tests per connector with replay fixtures for API drift detection (`HIGH`).
- E2E smoke tests: auth, initial sync, catch-up query, link suggestion workflow (`HIGH`).

## What to Avoid (2026)
- Avoid Electron for this product: larger memory footprint and weaker low-overhead story (`HIGH`).
- Avoid cloud-only vector DB for MVP: violates privacy posture and adds ops burden (`HIGH`).
- Avoid over-scoped ingestion (email/Discord/Notion) before Slack+GitHub/Linear quality (`HIGH`).
- Avoid unbounded background workers and naive polling loops (`HIGH`).
- Avoid storing full raw payload duplicates across tables; normalize once and reference (`HIGH`).
- Avoid opaque ML pipelines without deterministic fallback search path (`HIGH`).

## Minimal “Ship-First” 2026 Stack
- Desktop: `Tauri v2` + Rust (`tokio`, `tracing`, `reqwest`, `serde`).
- Local data: `SQLite (WAL + FTS5)` + optional `Qdrant local` for vectors.
- AI local: ONNX/Candle embedding model + retrieval/rerank in-process.
- Integrations: Slack Events/Web API, GitHub GraphQL+REST, Linear GraphQL.
- Security: OS keychain, local encryption, explicit remote-off by default toggle.
- Result: privacy-forward, low-latency MVP with clear upgrade path to team features.

## Upgrade Path After MVP
- Multi-workspace tenancy in local DB with per-tenant keys (`MED`).
- Optional enterprise relay for policy enforcement and managed updates (`MED`).
- Selective federated analytics with differential privacy for product telemetry (`LOW`).
