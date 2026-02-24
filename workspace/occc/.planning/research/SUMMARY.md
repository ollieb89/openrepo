# Nexus-Sync Roadmap Synthesis

## Recommended Stack Snapshot
- Desktop runtime: Tauri v2 with Rust supervisor and thin React/TypeScript UI.
- Core async model: Tokio workers with bounded queues and cooperative cancellation.
- Primary local store: SQLite in WAL mode for metadata, sync state, and durability.
- Lexical retrieval: SQLite FTS5 as deterministic fallback and debugging path.
- Vector retrieval: Qdrant local/embedded by default; sqlite-vec as lean fallback option.
- Network and API clients: reqwest + provider-specific rate-limit and retry middleware.
- Observability: tracing + local metrics for ingest lag, queue depth, and retrieval quality.
- Secrets: OS keychain-backed token storage; never persist plaintext secrets.
- AI boundary: local retrieval/embedding first; remote inference only explicit opt-in.
- Security posture: strict TLS validation, minimized scopes, local-first data retention.

## Table-Stakes MVP Set
- Slack ingestion with channel/thread sync, cursor checkpoints, and edit/delete handling.
- GitHub ingestion focused on issues, PRs, comments, and cross-reference context.
- Linear ingestion focused on issue metadata, comments, and status transitions.
- Unified entity model spanning messages, threads, issues, PRs, users, and decisions.
- Natural-language catch-up for "what changed" and "what do I need to know".
- Time-scoped catch-up for relative and absolute windows with timezone normalization.
- Source-grounded summaries with deep-link attribution for every material claim.
- Decision extraction from threads with confidence scoring and abstain behavior.
- Auto-link suggestions between chat and work items (suggest-only, not auto-write).
- Clear sync health and staleness visibility, including retry/error state surfaces.
- Local-first processing defaults with explicit remote-assist toggle.
- Background sync constrained by strict CPU/memory budgets.

## Major Architecture Decisions
- Use append-only normalized event log as ingestion source of truth.
- Materialize canonical entities/relations from events for query-time graph traversal.
- Keep raw provider payload snapshots immutable and checksum-addressed locally.
- Enforce connector contract: pull_since(cursor), normalize, idempotent upsert.
- Use deterministic IDs/hashes to guarantee replay-safe dedupe and merge semantics.
- Split retrieval into hybrid path: graph + lexical + vector with ranking fusion.
- Gate all indexing and query output through visibility labels and permission filters.
- Isolate connectors so one provider outage cannot block all query workflows.
- Persist link suggestions with evidence spans, confidence, and explicit user state.
- Ship with in-process durable job tables; defer external broker until post-MVP.

## Top Risks and Mitigations
- Privacy boundary erosion from telemetry.
- Mitigation: default-redacted events, data classification gates, mandatory privacy review.
- Secret leakage in logs/crash artifacts.
- Mitigation: keychain storage, log scrubbers, and secure crash-bundle export.
- Over-broad OAuth/app scopes hurting trust and security.
- Mitigation: minimal scopes, progressive consent, periodic scope audits.
- API drift causing broken parsing and silent data loss.
- Mitigation: provider contract tests, schema alerts, tolerant parsers, fallback handling.
- Rate-limit cascades during backfills.
- Mitigation: request budgeting, jittered backoff, prioritized queues, checkpointed deltas.
- Event ordering ambiguity degrading summary correctness.
- Mitigation: source ordering keys, clock-offset handling, uncertainty markers.
- Low precision in auto-links and decision summaries.
- Mitigation: multi-signal scoring, calibrated thresholds, evidence-only synthesis, feedback loop.
- Performance regressions on large workspaces.
- Mitigation: incremental indexing, worker backpressure, compaction/TTL, resource kill-switches.
- Cross-workspace data bleed in multi-account clients.
- Mitigation: hard tenant partition keys in storage, caches, and query filters.

## Phase-Order Hints
- Phase 1: Foundation.
- Deliver event log schema, sync checkpoints, canonical model, secure token handling.
- Phase 2: First connector vertical slice.
- Deliver Slack ingest + normalization + FTS retrieval + staleness diagnostics.
- Phase 3: Multi-source expansion.
- Deliver GitHub + Linear connectors, entity unification, replay/idempotency hardening.
- Phase 4: Catch-up quality baseline.
- Deliver hybrid retrieval, evidence-grounded summaries, time-scoped query intents.
- Phase 5: Decision and link intelligence.
- Deliver decision timeline, link suggestions, rationale, and user feedback capture.
- Phase 6: Security and resilience hardening.
- Deliver permission enforcement audit, outage isolation, failure recovery tooling.
- Phase 7: Performance and launch readiness.
- Deliver tuning for low idle overhead, retention controls, diagnostics, and policy docs.

## Roadmap Guardrails
- Keep connector scope fixed to Slack + GitHub + Linear through MVP.
- Prioritize precision, provenance, and trust over aggressive automation.
- Require user confirmation for external writes and high-impact actions.
- Surface degraded states explicitly instead of implying complete context.
- Treat local-first promise as a product invariant, not a preference.
