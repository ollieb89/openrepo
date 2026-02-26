# PITFALLS: Local-First Context-Bridge Products

## Format
- Pitfall: Domain-specific failure mode for local-first context bridges.
- Warning Signs: Observable indicators the pitfall is emerging.
- Prevention Strategy: Design or process controls that reduce likelihood/impact.
- Suggested Phase: Earliest product phase where this should be explicitly handled.

## Pitfalls Register

1) Privacy boundary erosion via "helpful" telemetry
- Warning Signs: New analytics events contain message snippets, issue titles, or user identifiers by default.
- Prevention Strategy: Enforce data-classification gates, default-redact payloads, and require privacy review for every new event.
- Suggested Phase: Architecture + instrumentation design (pre-alpha).

2) Local secret leakage from token storage
- Warning Signs: OAuth tokens/API keys are persisted unencrypted or visible in logs/crash dumps.
- Prevention Strategy: Use OS keychain/credential vault, in-memory short-lived tokens, and log scrubbers for secrets.
- Suggested Phase: Integration foundation (alpha).

3) Over-broad connector permissions
- Warning Signs: App requests full workspace scopes when only read metadata is needed.
- Prevention Strategy: Scope minimization, progressive permission prompts, and per-connector permission audits.
- Suggested Phase: Connector design + security review (alpha).

4) API drift breaking extraction pipelines
- Warning Signs: Sudden rise in parse errors, missing fields, null objects after provider-side updates.
- Prevention Strategy: Contract tests against provider schemas, version pinning, fallback parsers, and schema-change alerting.
- Suggested Phase: Integration hardening (alpha to beta).

5) Rate-limit cascades during backlog sync
- Warning Signs: 429 spikes, retry storms, queue growth, and long freshness delays after reconnect.
- Prevention Strategy: Budgeted request scheduler, adaptive backoff with jitter, delta sync checkpoints, and priority queues.
- Suggested Phase: Sync engine implementation (alpha).

6) Event ordering ambiguity creates incorrect timelines
- Warning Signs: "Catch me up" summaries place decisions before the discussion that produced them.
- Prevention Strategy: Monotonic event IDs, source clock-offset handling, causal stitching rules, and uncertainty markers.
- Suggested Phase: Context graph modeling (alpha).

7) Embedding quality collapse on short/noisy chat content
- Warning Signs: Irrelevant nearest neighbors, weak recall for acronyms, and topic drift in recommendations.
- Prevention Strategy: Domain-tuned chunking, metadata-aware embeddings, acronym dictionaries, and periodic retrieval eval sets.
- Suggested Phase: Relevance pipeline design (alpha to beta).

8) False links between chats and tasks reduce trust
- Warning Signs: Users frequently dismiss suggested links or report "not related" matches.
- Prevention Strategy: Calibrated confidence thresholds, multi-signal linking (semantic + participants + time window), and one-click feedback loops.
- Suggested Phase: Recommendation UX + model calibration (beta).

9) Hallucinated causality in auto-summaries
- Warning Signs: Summaries assert decisions/owners that are not explicitly present in source artifacts.
- Prevention Strategy: Evidence-grounded summarization, citation pointers, and abstain behavior when confidence is low.
- Suggested Phase: Summarization feature rollout (beta).

10) Silent data staleness masked as "complete context"
- Warning Signs: Freshness lag exceeds SLA but UI does not surface lag or missing connector health.
- Prevention Strategy: Per-source freshness badges, degraded-state banners, and sync-health diagnostics in-product.
- Suggested Phase: UX reliability layer (beta).

11) Local indexing performance regressions on large workspaces
- Warning Signs: CPU spikes, battery drain, fan noise, and UI lag during background sync/index operations.
- Prevention Strategy: Incremental indexing, bounded worker pools, backpressure, and resource budgets with kill-switches.
- Suggested Phase: Performance engineering (alpha continuous).

12) Memory bloat from long-lived context graphs
- Warning Signs: Resident memory grows over days; process restarts required to recover.
- Prevention Strategy: TTL/compaction policies, mmap-based stores, and leak detection profiling in CI/perf runs.
- Suggested Phase: Storage/runtime architecture (alpha).

13) Offline-first conflicts creating duplicate or divergent entities
- Warning Signs: Same decision or task appears multiple times after reconnect merge.
- Prevention Strategy: Deterministic IDs, idempotent upserts, conflict-resolution policies, and reconciliation audits.
- Suggested Phase: Data model + sync semantics (alpha).

14) Cross-workspace data bleed in multi-tenant local clients
- Warning Signs: Search results include items from a different workspace/account context.
- Prevention Strategy: Hard workspace partition keys at storage and query layers; scoped caches per tenant.
- Suggested Phase: Multi-account support planning (pre-beta).

15) Insecure local cache artifacts (attachments/snippets)
- Warning Signs: Temporary files remain world-readable or persist after logout/uninstall.
- Prevention Strategy: Encrypted-at-rest cache, strict file permissions, secure deletion policies, and cache lifecycle controls.
- Suggested Phase: Security implementation (alpha).

16) Compliance mismatch for regulated customers
- Warning Signs: Cannot answer where data resides, retention behavior, or auditability questions.
- Prevention Strategy: Data-flow documentation, retention controls, audit logs, and configurable policy presets.
- Suggested Phase: Enterprise readiness planning (beta).

17) Inadequate provenance undermining user trust
- Warning Signs: Users ask "where did this come from?" and cannot inspect source snippets quickly.
- Prevention Strategy: Source citations, deep links to original Slack/thread/issue artifacts, and confidence explanations.
- Suggested Phase: Core UX for trust (beta).

18) Feedback loops ignored, quality never improves
- Warning Signs: Dismissal/report actions are collected but not tied to retraining/recalibration cycles.
- Prevention Strategy: Closed-loop quality pipeline, weekly error taxonomy review, and measurable precision/recall targets.
- Suggested Phase: Post-MVP optimization (beta to GA).

19) Connector outage handling that fails "graceful degradation"
- Warning Signs: One provider outage blocks all catch-up results or crashes sync workers.
- Prevention Strategy: Circuit breakers, per-connector isolation, partial-result responses, and clear outage messaging.
- Suggested Phase: Resilience engineering (beta).

20) Misaligned trust messaging vs actual behavior
- Warning Signs: Marketing says "local-first" while hidden cloud fallbacks process sensitive context.
- Prevention Strategy: Explicit processing mode disclosures, opt-in cloud paths, and externally reviewable privacy controls.
- Suggested Phase: Product + legal alignment before launch (pre-GA).
