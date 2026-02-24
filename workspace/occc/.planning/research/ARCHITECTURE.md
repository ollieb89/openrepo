# Nexus-Sync MVP Architecture Recommendation

## Architecture Goals
- Local-first execution with strict privacy boundaries.
- Reliable cross-tool context retrieval for Slack + GitHub/Linear.
- Incremental pipelines that support near-real-time catch-up queries.
- Low idle CPU and predictable memory profile for desktop background operation.

## Top-Level Component Boundaries
- Desktop Shell (Tauri UI + command surface): user auth entry, status, query input, result rendering.
- Orchestrator Core (Rust service layer): starts/stops connectors, schedules jobs, manages retries/backoff.
- Connector Layer: isolated adapters for Slack, GitHub, and Linear with provider-specific auth/token refresh.
- Event Log Store: append-only normalized event journal persisted locally (SQLite).
- Canonical Graph Store: entities and relationships (message, thread, issue, PR, project, user, decision).
- Embedding/Index Worker: asynchronous pipeline that transforms canonical records into vector + lexical indexes.
- Linking Engine: computes suggested and confirmed links between chat artifacts and work items.
- Query Engine: retrieval + ranking + synthesis for natural-language catch-up.
- Permission Guard: enforces source-scoped visibility and redaction before indexing/query response.
- Sync State Manager: cursors/checkpoints, job watermarks, conflict detection, replay orchestration.

## Data Contracts and Ownership
- Connector output contract: provider event + provider object id + source timestamps + access scope metadata.
- Normalized event contract: `event_id`, `source`, `tenant`, `actor`, `artifact_type`, `payload_ref`, `occurred_at`, `visibility`.
- Canonical entity contract: stable internal UUID with source-id aliases and version metadata.
- Link contract: `link_id`, `from_entity`, `to_entity`, `link_type`, `score`, `evidence`, `state` (suggested/accepted/rejected).
- Query result contract: answer summary + supporting snippets + provenance references + permission filter proof.

## End-to-End Data Flow
- Connectors poll/subscribe using incremental cursors from Sync State Manager.
- Raw provider payloads are written to immutable local blob/object files keyed by checksum.
- Orchestrator emits normalized events into Event Log Store in arrival order.
- Canonicalizer consumes event log, materializes/upserts entities in Canonical Graph Store.
- Embedding/Index Worker subscribes to entity-change queue and indexes only changed chunks.
- Linking Engine consumes candidate pairs from recent entities and historical neighbors.
- Accepted links are written to graph edges and become query-time ranking features.
- Query Engine retrieves from graph + lexical + vector indexes, ranks, then synthesizes response.

## Event Ingestion Design
- Slack ingestion: channels, thread replies, reactions, edits, and message deletions with edit lineage.
- GitHub ingestion: issues, PRs, comments, reviews, commits, and cross-reference events.
- Linear ingestion: issues, comments, status transitions, assignee changes, project metadata.
- Ingestion mode: start with periodic pull + cursor checkpoints; optionally add webhook bridge later.
- Idempotency: dedupe by provider event id or deterministic content hash when event ids are absent.
- Ordering: maintain per-source ordering key; allow eventual reorder reconciliation by occurred timestamp.
- Failure handling: exponential backoff + dead-letter table for poison payloads.

## Embedding and Indexing Pipeline
- Chunking policy: source-aware chunking (thread windows for chat, section-based for PR/issue bodies).
- Preprocessing: redact secrets/PII markers, normalize mentions/URLs, preserve provenance anchors.
- Embedding model runtime: local model preferred; optional encrypted-transport remote inference fallback.
- Vector index: HNSW/IVF local index persisted per tenant and source scope.
- Lexical index: SQLite FTS5 for exact term and code/token lookups.
- Incremental updates: tombstone handling on deletes, partial reindex on edits, full rebuild command for recovery.
- Freshness SLO target: newly ingested item searchable within 60-120 seconds on commodity laptop.

## Linking Engine
- Candidate generation: temporal proximity + shared entities (repo, issue key, participants, branch names).
- Scoring features: semantic similarity, explicit references, action verbs, recency decay, participant overlap.
- Rules layer: hard boosts for explicit URLs/IDs; hard blocks across permission boundaries.
- Human feedback loop: user accepts/rejects suggested links; feedback updates thresholds.
- Persistence: store link evidence spans to support explainable query results.

## Query Engine
- Query parse: intent classification (catch-up, decision trace, status delta, dependency lookup).
- Retrieval fusion: hybrid retrieval from vector index, FTS, and graph traversal.
- Ranking: weighted blend of relevance, recency, authority (decision-maker signals), and link confidence.
- Synthesis: compact answer with timeline bullets and explicit source citations.
- Safety: if evidence is weak, return uncertainty and top supporting artifacts rather than fabricated summary.

## Sync, Permissions, and Privacy
- Credential handling: OS keychain-backed token storage; never persist plaintext secrets in logs.
- Permission model: attach visibility labels from each source to every entity and chunk.
- Query-time enforcement: post-retrieval filter and pre-render redaction using visibility labels.
- Cross-source joins: only materialize links where user has access to both sides.
- Audit trail: local audit log of connector access, sync runs, and query executions.
- Data governance: configurable retention windows and per-source hard-delete propagation.

## Build Order Implications
- Phase 1: foundational stores and contracts (event log, canonical graph schema, sync checkpoints).
- Phase 2: Slack connector + ingestion normalization + minimal FTS query path.
- Phase 3: GitHub and Linear connectors + canonical entity unification + cursor reliability hardening.
- Phase 4: embedding pipeline + hybrid retrieval + baseline catch-up response synthesis.
- Phase 5: linking engine suggestions + feedback capture + explainability surfaces.
- Phase 6: permissions hardening, audit logging, and failure-recovery tooling.
- Phase 7: performance tuning (batching, cache strategy, index compaction, low-power scheduling).

## MVP Non-Functional Targets
- Idle overhead target: <3% CPU average and bounded memory profile during background sync.
- Reliability target: at-least-once ingestion with deterministic dedupe and replay support.
- Accuracy target: prioritize precision of links and cited evidence over aggressive recall.
- Operability: ship diagnostics bundle with redacted logs and sync/index health metrics.

## Recommended Initial Tech Choices
- Storage: SQLite (WAL mode) for metadata + FTS; local files for raw payload snapshots.
- Runtime: Rust async (Tokio) workers with bounded queues and cooperative cancellation.
- Messaging: in-process durable job tables first; defer external broker for MVP.
- Models: pluggable embedding provider interface to swap local/remote backends without schema changes.
