# Nexus-Sync Feature Landscape (MVP)

## Purpose
Define the domain feature set for an intelligent context bridge focused on:
- Slack + GitHub/Linear integrations
- Catch-up assistant workflows
- Decision summaries from conversations
- Auto-linking between chat and work items

## Framing
- Scope here is MVP only, not long-term platform expansion.
- Features are grouped as table stakes, differentiators, and anti-features.
- Complexity is relative: Low, Medium, High.
- Dependency notes call out technical and product prerequisites.

## Table Stakes (Must-Have for MVP Credibility)
| Category | Feature | Why It Matters | Complexity | Dependency Notes | MVP Notes |
|---|---|---|---|---|---|
| Table Stakes | Slack message/thread ingestion | Required to build any chat context | Medium | Slack OAuth, channel/thread read scopes, incremental sync cursoring | Start with selected channels + recent history window |
| Table Stakes | GitHub issue/PR ingestion | Needed to connect discussion to code work | Medium | GitHub App/OAuth, repo permissions, webhook or polling strategy | Focus on issues + PR metadata first |
| Table Stakes | Linear issue ingestion | Needed for planning context parity with GitHub | Medium | Linear API token/OAuth, team/project scoping, pagination | Ingest issue title, state, assignee, labels |
| Table Stakes | Unified entity model | Enables one context layer over heterogeneous sources | High | Canonical schema for messages, threads, issues, PRs, decisions | Keep schema minimal and extensible |
| Table Stakes | Source attribution in every summary | Trust and auditability | Low | Stable deep links to Slack/GitHub/Linear records | Every generated statement must map to source IDs |
| Table Stakes | Natural-language catch-up query | Primary user-facing value path | High | Retrieval pipeline, prompt orchestration, latency guardrails | Target "what changed on X" and "what do I need to know" |
| Table Stakes | Time-scoped catch-up (since yesterday/last week) | Reduces overload and ambiguity | Medium | Reliable timestamps, timezone normalization | Support absolute + relative time windows |
| Table Stakes | Decision summary extraction from threads | Converts chatter into actionable project memory | High | Thread segmentation, decision signal heuristics, confidence scoring | Prioritize explicit decisions, defer nuanced sentiment |
| Table Stakes | Auto-link suggestion (chat <-> issue/PR) | Bridges fragmented workflow contexts | High | Entity matching, lexical + semantic similarity, threshold tuning | Suggest links first, avoid automatic hard writes |
| Table Stakes | Local-first processing defaults | Core privacy promise and enterprise trust | High | On-device storage/index, local model or encrypted inference path | Cloud fallback only with explicit controls |
| Table Stakes | Encrypted transit and secure token storage | Baseline security requirement | Medium | OS keychain/secret vault, TLS enforcement, token refresh handling | Never persist plaintext secrets |
| Table Stakes | Background sync with low resource footprint | Required for always-on desktop agent | High | Efficient scheduling, rate-limit compliance, bounded index updates | Set strict CPU/memory budgets and monitor |
| Table Stakes | Failure visibility + retry status | Prevents silent context gaps | Medium | Job state tracking, retry queues, user-visible integration health | Show stale source warnings clearly |

## Differentiators (Should-Have for MVP Advantage)
| Category | Feature | Why It Matters | Complexity | Dependency Notes | MVP Notes |
|---|---|---|---|---|---|
| Differentiator | Cross-source decision timeline | Makes decisions legible across chat + work systems | Medium | Normalized decision object, temporal ordering | Render concise chronological output |
| Differentiator | "Why this is linked" rationale on auto-links | Increases trust in suggested associations | Medium | Explainability layer over similarity signals | Include top signals and confidence |
| Differentiator | Catch-up by objective (feature/bug/customer) | Mirrors real user intent better than source-first queries | High | Intent parsing, entity resolution, scoped retrieval | Support 3-5 objective templates |
| Differentiator | Contradiction detection across threads/issues | Highlights decision drift quickly | High | Decision state tracking, semantic comparison | Flag potential conflicts, not final truth |
| Differentiator | Action-item rollup from decision summaries | Converts context into next-step clarity | Medium | Imperative extraction + assignee/date detection | Keep as suggested tasks, no auto-creation |
| Differentiator | Relevance feedback loop (thumbs up/down) | Improves precision over time for a team | Medium | Local preference store, ranking feature toggles | Team-level tuning can be deferred |
| Differentiator | Privacy mode controls per workspace/project | Supports mixed-sensitivity environments | Medium | Policy layer over indexing/summarization behaviors | Ship simple presets, not full policy engine |

## Anti-Features (Explicitly Not in MVP)
| Category | Feature | Why Excluded | Complexity if Included | Dependency Notes | MVP Boundary |
|---|---|---|---|---|---|
| Anti-Feature | Email/Discord/Notion/Jira connectors | Breaks integration focus and slows validation | High | New auth flows, schemas, QA matrix expansion | Limit integrations to Slack + GitHub/Linear |
| Anti-Feature | Meeting transcription + voice assistant | Outside context bridge core loop | High | Audio pipeline, diarization, storage/privacy burden | Exclude from MVP roadmap |
| Anti-Feature | Full replacement project management UI | Conflicts with middleware strategy | High | Large frontend surface + workflow parity burden | Keep lightweight assistant experience |
| Anti-Feature | Autonomous ticket creation/edits by default | High risk of noisy or wrong writes | Medium | Strong approval workflows and guardrails needed | Suggest actions; require user confirmation |
| Anti-Feature | Cloud-only indexing and inference | Violates local-first trust positioning | Medium | Centralized data retention/compliance overhead | Local-first or encrypted transit only |
| Anti-Feature | Team-wide analytics dashboards | Not essential to core catch-up value | Medium | Aggregation pipelines, historical warehousing | Defer until core loop is proven |
| Anti-Feature | Complex workflow automation engine | Premature platformization | High | Rule builder UX, execution safety, observability | Keep automation minimal and explicit |

## Dependency Risk Notes
- Slack/GitHub/Linear API rate limits can degrade freshness; MVP needs graceful staleness messaging.
- Identity resolution across systems (same human across Slack + GitHub/Linear) is a likely quality bottleneck.
- Auto-link precision depends on clean metadata (titles, labels, thread hygiene) that may vary by team.
- Local model/runtime choice affects latency, privacy guarantees, and desktop resource profile.
- Decision extraction quality depends on thread structure; ambiguous chat should be marked low-confidence.

## Recommended MVP Slice (Execution Order)
1. Ingestion + unified model + secure storage.
2. Catch-up assistant with source-grounded summaries.
3. Decision extraction and decision timeline.
4. Auto-link suggestions with rationale and confidence.
5. Feedback loop and selective quality improvements.
