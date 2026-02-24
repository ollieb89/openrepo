# Nexus-Sync 2026 Stack Recommendations

## Scope and Assumptions
- Focus: MVP (Slack + GitHub/Linear) and v1.1 "Global Project Brain".
- Runtime target: Desktop agent with Rust/Tauri, privacy-by-default.

## Recommended Core Architecture
- Desktop shell: `Tauri v2` + Rust backend + minimal web UI (`HIGH`).
- Internal process model: single Rust supervisor + async workers (`tokio`) (`HIGH`).
- Data model: append-only local event log + derived materialized views (`HIGH`).

## v1.1 Specific Stack Additions

### Local Graph Storage
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| SQLite (Recursive CTEs) | 3.34+ | Cross-Project Context Graph | Pushes graph traversal to DB layer; avoids application-side recursion overhead. |
| Adjacency List Schema | N/A | Graph Storage Model | Simple, flexible, and performs well with indexing on (from_id, to_id). |

### Ingestion Expansion
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Microsoft Graph SDK | v1.0 | Teams Sync | Supports `deltaLink` for efficient incremental message synchronization. |
| Serenity / Discord REST | v0.12+ | Discord Sync | Combines WebSocket (Gateway) for real-time and REST for historical pagination. |

### Risk Intelligence & Visualization
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Structured LLM Prompting | N/A | Risk Drift Detection | Uses JSON-formatted objects for deterministic comparison between chat and issues. |
| Recharts / D3.js | v2.x | Project Health Dashboard | High-performance visualization of heatmaps and dependency sparklines. |

## Local Storage and Search
- Primary store: `SQLite` in WAL mode for reliability and low overhead (`HIGH`).
- Full-text fallback: `SQLite FTS5` for keyword search (`HIGH`).
- Vector store (default): `Qdrant` embedded/local mode (`MED`).

## Integrations
- Slack: official Web API + Events API (`HIGH`).
- GitHub: GraphQL for issue/PR context (`HIGH`).
- Linear: GraphQL API with incremental sync (`HIGH`).
- Teams: Microsoft Graph Delta Queries (`HIGH`).
- Discord: Gateway API + Paginated REST (`MED`).

## What to Avoid
- Avoid deep recursive CTEs without `LIMIT` or depth counters (prevents infinite loops in cyclic graphs).
- Avoid Discord message polling; use the Gateway API to stay within rate limits.
- Avoid over-complicated graph databases (Neo4j) for local desktop use; SQLite is sufficient.
