# Phase 0: Shared Infrastructure - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers the core platform MVP required to support the vertical compliance agents in Phase 1. It focuses purely on shared infrastructure: monorepo bootstrap, multi-tenant database & authentication, billing integration, a robust LLM abstraction routing layer, and monitoring/compliance baselines.
</domain>

<decisions>
## Implementation Decisions

### Infra Deployment Model
- **Deployment Strategy:** Managed Database + VMs for staging/prod, diverging slightly from a pure Docker Compose local dev.
- **Infrastructure as Code:** Terraform for Staging/Prod. 
- **Schema Management:** Focus heavily on automated schema provisioning scripts with Terraform.

### LLM Provider Defaults
- **Provider Tiers:** 
  - *Simple Tasks:* Flash-Lite or DeepSeek V3.2.
  - *Standard Tasks:* Flash 2.5, Haiku, Sonnet, or DeepSeek R1.
  - *Complex Tasks:* Opus or GPT-5.2.
- **Resilience:** Strict Circuit Breaker (e.g., opens after 5 failures/60s).
- **Cost Tracking:** Granular token tracking meticulously matching provider token prices per request and aggregated per org.

### Rate Limit Strategy
- **API Responses:** Rich Headers & Custom Codes, including precise `Retry-After` headers for dashboard clients to handle gracefully.
- **Storage Backend:** Redis Backed for distributed rate limit tracking across multiple API instances.

### Claude's Discretion
- **Tenant Isolation Depth:** Claude decides the implementation depth (likely App-Layer ORM filtering to start for velocity, adding Postgres RLS later if necessary). Data sharing will use a Hybrid approach: system data (like system configurations, global prompts) is global, while user data is strictly scoped to an `org_id`.
</decisions>

<specifics>
## Specific Ideas
- For LLM routing, heavily favor the cheapest capable models (e.g., DeepSeek R1 costs 90% less than Opus but provides similar reasoning quality; Flash-Lite/DeepSeek V3.2 are highly optimized for simple tasks).
</specifics>

<deferred>
## Deferred Ideas
None — discussion stayed within phase scope.
</deferred>

---

*Phase: 00-shared-infrastructure*
*Context gathered: 2026-02-25*
