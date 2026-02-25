# Phase 1: Vertical Compliance Agents - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers the core value proposition: multimodal ingestion (video, telemetry, documents), ML-calibrated risk scoring mapped to regulatory databases, and Human-in-the-Loop (HITL) workflows, initially targeting offshore energy compliance.
</domain>

<decisions>
## Implementation Decisions

### HITL Interface Density & Mechanics
- **Density:** Pinpoint Context. The interface must show exactly the offending frame, the sensor anomaly blip, and the specific regulatory clause violated. It should be high density with low scrolling required.
- **Reviewer Interaction:** Full Overrides. The reviewer can adjust the confidence score, override the specific regulation cited, or write a custom remediation step, rather than just simple binary classification.

### Ingestion Workflow
- **Upload Strategy:** Deferred Bulk Uploads to accommodate low-bandwidth offshore rigs. 
- **Architecture:** A reliable Backend Async Queue (e.g., Celery/RabbitMQ) with an API that supports resumable chunked uploads for large video and sensor dumps.

### Report Format Strictness
- **Output Style:** Modern Digital First. Provide a modern, structured digital report (JSON + clean PDF) focusing on data clarity over legacy form layouts.
- **Client Adaptation:** Custom Client Mappers. Build capabilities for the pilot customer to map our JSON output into their own internal legacy templates if required.

### Claude's Discretion
- Technical implementation of the async queue and chunking API specifics.
- UI framework details for the HITL interface, provided it adheres to the "Pinpoint Context" requirement.
</decisions>

<specifics>
## Specific Ideas
- The HITL interface needs to be optimized for reviewer speed, given that 100% of flags will be reviewed during the initial pilot phase.
- Resumable chunked uploads are a hard requirement due to the unreliable internet connections on offshore platforms.
</specifics>

<deferred>
## Deferred Ideas
None — discussion stayed within phase scope.
</deferred>

---

*Phase: 01-vertical-compliance-agents*
*Context gathered: 2026-02-25*
