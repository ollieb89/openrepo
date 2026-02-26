# Implementation Workflow: Phase 0 + Phase 1

**Source:** `venture_plan.md` (Phase 0: Shared Infrastructure + Phase 1: Vertical Compliance Agents)
**Generated:** 2026-02-25
**Strategy:** Systematic, dependency-mapped, gate-driven
**Estimated Duration:** Weeks 1-20

---

## Legend

- `[B]` = Blocked by predecessor
- `[P]` = Parallelizable with siblings
- `[G]` = Gate / decision point
- `[D]` = Deliverable artifact
- `[R]` = Risk checkpoint

---

## PHASE 0: Shared Infrastructure (Weeks 1-3)

### Wave 0.1 — Project Bootstrap (Week 1, Days 1-2)

> Stand up the monorepo, CI, and local dev environment. Everything else depends on this.

| # | Task | Type | Output | Notes |
|---|------|------|--------|-------|
| 0.1.1 | Initialize Python monorepo with `uv` workspace | [D] | `pyproject.toml`, `packages/` layout | FastAPI + SQLAlchemy + Alembic in `packages/platform/` |
| 0.1.2 | PostgreSQL Docker Compose for local dev | [P][D] | `docker-compose.yml` with `pg`, `pgadmin` services | Multi-tenant from day one — no SQLite |
| 0.1.3 | GitHub Actions CI scaffold | [P][D] | `.github/workflows/ci.yml` | Lint (ruff), test (pytest), type-check (pyright), build |
| 0.1.4 | Environment config structure | [P][D] | `config/settings.py` using pydantic-settings | `.env.example` with all required vars, no secrets in repo |
| 0.1.5 | Pre-commit hooks | [P][D] | `.pre-commit-config.yaml` | ruff, pyright, secret-scanner |

**Gate G0.1:** `make dev && make test` passes with empty test suite. Docker Compose `up` gives healthy PG.

---

### Wave 0.2 — Database & Auth (Week 1, Days 3-5)

> Multi-tenant data layer and JWT auth. Every API endpoint needs this.

| # | Task | Type | Depends | Output | Notes |
|---|------|------|---------|--------|-------|
| 0.2.1 | SQLAlchemy 2.0 async models: `Organization`, `User`, `ApiKey` | [B] | 0.1.1 | `models/auth.py` | Org-scoped tenant isolation via `org_id` FK on all tables |
| 0.2.2 | Alembic migration setup + initial migration | [B] | 0.2.1 | `alembic/` dir, first migration | `alembic revision --autogenerate` |
| 0.2.3 | JWT auth middleware (FastAPI dependency) | [P][D] | 0.1.1 | `middleware/auth.py` | RS256, 15min access + 7d refresh tokens, org_id in claims |
| 0.2.4 | Auth API routes: register, login, refresh, API key CRUD | [B] | 0.2.1, 0.2.3 | `routes/auth.py` | Rate-limited registration, bcrypt password hashing |
| 0.2.5 | Tenant isolation middleware | [B] | 0.2.3 | `middleware/tenant.py` | Auto-filter all queries by `org_id` from JWT |
| 0.2.6 | Auth integration tests | [B] | 0.2.4 | `tests/test_auth.py` | Register → login → access protected route → token refresh |

**Gate G0.2:** Authenticated request with org-scoped data isolation proven in test.

---

### Wave 0.3 — Billing Integration (Week 2, Days 1-3)

> Stripe subscriptions and usage metering. Needed before any customer-facing deployment.

| # | Task | Type | Depends | Output | Notes |
|---|------|------|---------|--------|-------|
| 0.3.1 | Stripe SDK integration + webhook handler | [B] | 0.2.1 | `services/billing.py`, `routes/webhooks.py` | Webhook signature verification mandatory |
| 0.3.2 | Subscription model: 3 tiers (Starter $500, Growth $1K, Scale $2K) | [B] | 0.3.1 | Stripe Products + Prices created via migration script | Replaces hardcoded `pricing_logic.py` |
| 0.3.3 | Usage metering: actions tracked per billing period | [B] | 0.3.1, 0.2.5 | `services/usage.py` | Stripe Usage Records API, per-org metering |
| 0.3.4 | Subscription lifecycle: create, upgrade, downgrade, cancel | [B] | 0.3.2 | `services/subscription.py` | Proration handling via Stripe, not custom |
| 0.3.5 | Billing dashboard API endpoints | [B] | 0.3.3, 0.3.4 | `routes/billing.py` | Current plan, usage, invoices, payment method |
| 0.3.6 | Billing integration tests (Stripe test mode) | [B] | 0.3.4 | `tests/test_billing.py` | Full lifecycle: subscribe → use → meter → invoice |

**Existing asset:** `pricing_logic.py` (25% ready) — extract tier definitions, discard in-memory tracking.

**Gate G0.3:** Stripe test-mode subscription lifecycle works end-to-end.

---

### Wave 0.4 — LLM Abstraction Layer (Week 2, Days 3-5)

> SmartRouter for model selection, cost tracking, and fallback chains. Margin-critical component.

| # | Task | Type | Depends | Output | Notes |
|---|------|------|---------|--------|-------|
| 0.4.1 | `SmartRouter` base: provider interface abstraction | [B] | 0.1.1 | `services/llm/router.py` | Unified interface: `route(task_type, prompt, **kwargs) → LLMResponse` |
| 0.4.2 | Provider adapters: Anthropic, OpenAI, Google | [P][D] | 0.4.1 | `services/llm/providers/` | Async httpx clients, streaming support |
| 0.4.3 | Task-type routing rules | [B] | 0.4.1 | `services/llm/routing_rules.py` | Config-driven: conversation→Sonnet, reasoning→Opus, background→Haiku, extraction→GPT-4.1-mini |
| 0.4.4 | Per-request cost tracking | [B] | 0.4.1, 0.2.5 | `services/llm/cost_tracker.py` | Token counting per model, org-attributed, stored in PG |
| 0.4.5 | Fallback chain + circuit breaker | [B] | 0.4.2 | `services/llm/resilience.py` | Primary → secondary → cached. Circuit opens after 5 failures in 60s |
| 0.4.6 | LLM layer tests | [B] | 0.4.3, 0.4.5 | `tests/test_llm_router.py` | Mock providers, verify routing, fallback triggers, cost attribution |

**Critical insight:** 80%+ volume through small models. Opus reserved for complex objection handling only.

**Gate G0.4:** Mock routing test shows correct model selection per task type, fallback triggers on simulated failure.

---

### Wave 0.5 — Monitoring & Compliance Baseline (Week 3)

> Observability, alerting, and GDPR/EU AI Act foundations. Non-negotiable for enterprise sales.

| # | Task | Type | Depends | Output | Notes |
|---|------|------|---------|--------|-------|
| 0.5.1 | Prometheus metrics exporter (FastAPI middleware) | [B] | 0.2.3 | `middleware/metrics.py` | Request count, latency histogram, error rate by endpoint |
| 0.5.2 | Grafana dashboard provisioning | [P][D] | 0.5.1 | `docker/grafana/dashboards/` | API health, LLM cost burn, per-org usage |
| 0.5.3 | PagerDuty integration for critical alerts | [P][D] | 0.5.1 | `services/alerting.py` | Success rate <85%, LLM cost spike >2x baseline |
| 0.5.4 | GDPR consent management | [B] | 0.2.1 | `models/consent.py`, `services/gdpr.py` | Per-org consent records, legal basis per workflow type |
| 0.5.5 | Right-to-erasure cascade | [B] | 0.5.4 | `services/gdpr.py:erase_user()` | Cascading delete across all stores including future vector DB |
| 0.5.6 | TTL policies for conversation logs | [P][D] | 0.2.1 | Alembic migration + PG cron job | 90-day default, configurable per-org |
| 0.5.7 | Audit trail: immutable append-only decision log | [B] | 0.2.1 | `models/audit.py`, `services/audit.py` | Timestamped, reasoning trace, agent_id, org_id. Append-only (no UPDATE/DELETE) |
| 0.5.8 | EU AI Act risk categorization registry | [B] | 0.5.7 | `services/ai_act.py` | Self-assessment per agent type, HITL gate config |
| 0.5.9 | Prompt registry (git-versioned) | [P][D] | 0.1.1 | `prompts/` dir + `services/prompt_registry.py` | Version-tagged YAML files, lookup by agent+version |
| 0.5.10 | Phase 0 integration test suite | [B] | all above | `tests/test_integration_p0.py` | Auth → create org → subscribe → route LLM call → verify metrics + audit log |

**Existing asset:** `scaling_monitoring_tools.py` (25% ready) — extract health threshold logic, discard in-memory dashboard.

**Gate G0:** **All Phase 0 gates pass. Auth, billing, LLM routing, monitoring, GDPR, audit trail functional.**

---

### Phase 0 — Deliverable Checklist

- [ ] FastAPI app boots, serves OpenAPI docs
- [ ] PostgreSQL multi-tenant schema with Alembic migrations
- [ ] JWT auth with org-scoped data isolation
- [ ] Stripe subscription lifecycle (test mode)
- [ ] Usage metering per org per billing period
- [ ] SmartRouter routes to correct model per task type
- [ ] Fallback chain and circuit breaker functional
- [ ] Per-request LLM cost tracked and attributed to org
- [ ] Prometheus metrics exported, Grafana dashboards provisioned
- [ ] GDPR consent management + right-to-erasure cascade
- [ ] Immutable audit trail logging
- [ ] EU AI Act risk categorization registry
- [ ] Git-versioned prompt registry
- [ ] CI green: lint, test, type-check
- [ ] Integration test: full request lifecycle

---

## PHASE 1: Vertical Compliance Agents (Weeks 4-20)

### Strategic Context

**Target verticals:** Offshore energy (Stavanger), Legal IP compliance
**NOT competing with:** DNV in Norwegian aquaculture (they own both standards AND tooling)
**Revenue model:** $15K-$30K implementation (mid-market) / $50K-$250K (enterprise) + $5K-$20K/mo recurring

---

### Wave 1.1 — Regulatory Knowledge Base (Week 4)

> Structured regulatory data as queryable knowledge. Everything in Phase 1 queries this.

| # | Task | Type | Depends | Output | Notes |
|---|------|------|---------|--------|-------|
| 1.1.1 | Regulatory DB schema: regulations, sections, requirements, cross-references | [B] | G0 | `models/regulatory.py` + migration | Versioned regulations (amendments tracked), jurisdiction tagging |
| 1.1.2 | NYTEK regulation ingestion pipeline | [B] | 1.1.1 | `services/regulatory/ingest.py` | PDF/HTML → structured sections → PG. Manual QA pass required |
| 1.1.3 | EU AI Act requirements ingestion | [P] | 1.1.1 | Same pipeline, different source | Focus on: risk categories, transparency, HITL requirements |
| 1.1.4 | GDPR article-level requirements | [P] | 1.1.1 | Same pipeline | Cross-reference with consent model from Phase 0 |
| 1.1.5 | Offshore energy regulatory corpus (Norwegian Petroleum Safety Authority) | [P] | 1.1.1 | Structured PSA regulations | Primary beachhead vertical regulations |
| 1.1.6 | Regulatory search API | [B] | 1.1.2-1.1.5 | `routes/regulatory.py` | Full-text search + structured queries (by jurisdiction, domain, requirement type) |
| 1.1.7 | Regulation cross-reference engine | [B] | 1.1.6 | `services/regulatory/cross_ref.py` | "This facility action triggers requirements from NYTEK §4.2 AND PSA §29" |

**Gate G1.1:** Can query "What are the structural integrity requirements for offshore installations under PSA?" and get correct, cited results.

---

### Wave 1.2 — Multimodal Ingestion Pipeline (Weeks 5-6)

> Video analysis, sensor telemetry, and document parsing feeding into a unified compliance assessment.

| # | Task | Type | Depends | Output | Notes |
|---|------|------|---------|--------|-------|
| 1.2.1 | Video analysis service (GPT-4o Vision) | [B] | 0.4.2 | `services/compliance/video_analyzer.py` | Frame extraction → anomaly detection → structured findings |
| 1.2.2 | InfluxDB setup for sensor telemetry | [B] | 0.1.2 | Docker Compose service + `services/compliance/telemetry.py` | Time-series storage, threshold alerting, trend analysis |
| 1.2.3 | Document parsing pipeline | [P] | G0 | `services/compliance/doc_parser.py` | PDF/DOCX inspection reports → structured data extraction (GPT-4.1-mini) |
| 1.2.4 | Unified ingestion orchestrator | [B] | 1.2.1-1.2.3 | `services/compliance/ingestion.py` | Merges multimodal signals into single assessment context per facility |
| 1.2.5 | Ingestion API endpoints | [B] | 1.2.4 | `routes/compliance/ingest.py` | Upload video, push telemetry, submit documents |
| 1.2.6 | Ingestion tests with fixture data | [B] | 1.2.4 | `tests/test_ingestion.py` | Sample video frames, mock telemetry, test PDFs |

**Existing asset:** `compliance_engine.py` (20% ready) — extract multimodal concept, discard mock data and additive scoring.

**Gate G1.2:** Ingest sample video + telemetry + document → unified assessment context produced.

---

### Wave 1.3 — Risk Scoring Engine (Weeks 5-6, parallel with 1.2)

> ML-calibrated risk scoring replacing the simplistic additive model.

| # | Task | Type | Depends | Output | Notes |
|---|------|------|---------|--------|-------|
| 1.3.1 | Risk model architecture: feature engineering from multimodal signals | [B] | 1.1.1 | `services/compliance/risk_model.py` | Input features: sensor readings, vision findings, document flags, historical violations |
| 1.3.2 | Calibrated weight system (replace additive scoring) | [B] | 1.3.1 | Configurable weights per regulation domain | Start with expert-tuned weights, calibrate with pilot data |
| 1.3.3 | Risk category classification (EU AI Act aligned) | [B] | 1.3.1, 1.1.3 | Risk levels: Minimal, Limited, High, Unacceptable | Maps to HITL requirements per level |
| 1.3.4 | Confidence scoring per risk assessment | [B] | 1.3.1 | `0.0-1.0` confidence with explanation | Low confidence → mandatory HITL review |
| 1.3.5 | Explainability layer: CoT reasoning traces | [B] | 1.3.1, 0.5.7 | `services/compliance/explainability.py` | Every risk score comes with natural-language explanation + regulation citations |
| 1.3.6 | Risk engine tests with ground-truth scenarios | [B] | 1.3.2-1.3.5 | `tests/test_risk_engine.py` | Known-good and known-bad scenarios with expected outcomes |

**Gate G1.3:** Risk engine produces explainable, regulation-cited scores for test scenarios. Confidence below threshold triggers HITL.

---

### Wave 1.4 — HITL & Report Generation (Week 7)

> Human-in-the-loop gates and pre-filled regulatory reports.

| # | Task | Type | Depends | Output | Notes |
|---|------|------|---------|--------|-------|
| 1.4.1 | HITL workflow engine | [B] | 1.3.3, 0.5.8 | `services/compliance/hitl.py` | Queue system: pending reviews, approve/reject/modify, feedback capture |
| 1.4.2 | HITL review API + minimal UI | [B] | 1.4.1 | `routes/compliance/review.py` | Domain expert sees: assessment, risk score, reasoning, recommended action |
| 1.4.3 | Compliance report generator (structured) | [B] | 1.3.5, 1.1.7 | `services/compliance/report_gen.py` | JSON + PDF output. Pre-filled regulatory forms with citations |
| 1.4.4 | Report API endpoints | [B] | 1.4.3 | `routes/compliance/reports.py` | Generate, list, download, share reports per facility |
| 1.4.5 | Digital twin API contract (interface only) | [P] | G0 | `services/compliance/digital_twin.py` | Abstract interface for facility modeling — implementation deferred |
| 1.4.6 | Phase 1 Foundation integration test | [B] | 1.4.1-1.4.4 | `tests/test_compliance_e2e.py` | Ingest → assess → risk score → HITL review → report generation |

**Existing asset:** `compliance_engine.py:generate_compliance_report()` — text template to replace with structured JSON+PDF generator.

**Gate G1.4 (= G2 from venture plan):** Foundation complete. Ready for pilot customer deployment.

**[R] Risk checkpoint:** If no pilot customer LOI by Week 8, pivot to SMB-first (Phase 2).

---

### Wave 1.5 — Pilot Deployment (Weeks 8-14)

> Single-facility deployment with one offshore energy operator. Full HITL for first 4 weeks.

| # | Task | Type | Depends | Output | Notes |
|---|------|------|---------|--------|-------|
| 1.5.1 | Deployment infrastructure: staging + production environments | [B] | G1.4 | Terraform/Docker configs | Staging mirrors production, customer data isolated |
| 1.5.2 | Customer onboarding flow | [B] | 0.2.4, 0.3.2 | `services/onboarding.py` | Org creation → user setup → subscription → facility config |
| 1.5.3 | Single-facility deployment (1 offshore platform) | [B] | 1.5.1, 1.5.2 | Live system for pilot customer | Single regulatory domain to start |
| 1.5.4 | 100% HITL review period (Weeks 8-12) | [B] | 1.5.3 | Expert feedback dataset | Every agent decision reviewed, feedback captured for calibration |
| 1.5.5 | Model calibration from expert feedback | [B] | 1.5.4 | Updated risk weights, confidence thresholds | Ground-truth dataset from 4 weeks of expert review |
| 1.5.6 | Explainability audit with regulatory auditor | [B] | 1.5.4 | Audit report | Verify reasoning traces satisfy auditor expectations |
| 1.5.7 | Pilot metrics dashboard | [P] | 1.5.3, 0.5.2 | Grafana dashboard per facility | Risk assessments/day, HITL review time, accuracy vs expert |
| 1.5.8 | Weekly pilot review meetings | — | 1.5.3 | Meeting notes, action items | Weeks 8-14, stakeholder alignment |

**Gate G1.5:** Pilot customer operational for 4+ weeks. Expert feedback incorporated. No critical failures.

---

### Wave 1.6 — Optimization & Expansion (Weeks 15-20)

> Scale to multiple facilities. Reduce HITL dependency. ERP integration.

| # | Task | Type | Depends | Output | Notes |
|---|------|------|---------|--------|-------|
| 1.6.1 | Expand to 2-3 facilities (same customer) | [B] | G1.5 | Multi-facility deployment | Proves horizontal scaling |
| 1.6.2 | ERP/compliance software connectors | [B] | 1.6.1 | `services/integrations/erp.py` | SAP, Oracle adapters — read existing data, write compliance reports |
| 1.6.3 | HITL reduction: exception-based review | [B] | 1.5.5 | Updated HITL policy | Confidence ≥ 0.85 → auto-approve. Below → HITL queue |
| 1.6.4 | Anonymization layer (Norwegian Working Environment Act) | [B] | 1.6.1 | `services/compliance/anonymize.py` | Aggregate at Team/Station level, no individual PII in outputs |
| 1.6.5 | First bias/fairness audit | [B] | 1.6.1 | Audit report | Monthly cadence begins. Statistical parity checks |
| 1.6.6 | Performance optimization: batch processing, caching | [P] | 1.6.1 | Perf improvements | Target: <30s for standard assessment, <5min for full multimodal |

**Gate G1.6:** 2+ facilities operational. HITL load reduced by >50%. No compliance gaps identified.

---

### Wave 1.7 — Sales Pipeline (Weeks 12-20, parallel with 1.5-1.6)

> Revenue generation activities running in parallel with technical work.

| # | Task | Type | Depends | Output | Notes |
|---|------|------|---------|--------|-------|
| 1.7.1 | Case study from pilot (quantified ROI) | [B] | 1.5.4 (4 weeks of data) | Case study document | Fines prevented, labor hours saved, compliance score delta |
| 1.7.2 | Sales collateral: deck, demo environment | [P] | 1.7.1 | Marketing assets | Demo with anonymized pilot data |
| 1.7.3 | Target prospect list: offshore energy + legal IP | [P] | — | CRM pipeline | 3-5 enterprise prospects, 5-10 mid-market |
| 1.7.4 | Outbound campaign to prospects | [B] | 1.7.1, 1.7.2, 1.7.3 | Pipeline of qualified leads | Personal outreach leveraging Stavanger network |
| 1.7.5 | Mid-market tier packaging ($15K-$30K implementation) | [B] | 1.6.3 | Tier definition + pricing page | Simplified onboarding, fewer customizations than enterprise |
| 1.7.6 | First enterprise proposal(s) | [B] | 1.7.4 | Signed LOI or SOW | Target: 1 enterprise + 2 mid-market by Week 20 |

**Gate G1.7 (Revenue Gate):** At least 1 signed customer beyond pilot. Pipeline of 3+ qualified prospects.

---

## Dependency Graph (Simplified)

```
PHASE 0
  0.1 Bootstrap ──┬── 0.2 DB & Auth ──┬── 0.3 Billing
                   │                    │
                   ├── 0.4 LLM Router ──┤
                   │                    │
                   └── 0.5 Monitoring ──┘── [G0: Platform MVP]
                                                │
PHASE 1                                         │
  1.1 Regulatory DB ─────────────────────────────┤
  1.2 Multimodal Pipeline ───────────────────────┤
  1.3 Risk Engine (parallel with 1.2) ───────────┤
                                                 │
  1.4 HITL + Reports ───── [G1.4: Foundation] ───┤
                                                 │
  1.5 Pilot Deployment ── [G1.5: Pilot Live] ────┤
                                                 │
  1.6 Optimization ─── [G1.6: Scale Proven] ─────┤
                                                 │
  1.7 Sales Pipeline (parallel from Week 12) ──── [G1.7: Revenue]
```

---

## Risk Checkpoints

| Week | Risk | Check | Mitigation |
|------|------|-------|------------|
| 3 | Platform MVP incomplete | G0 fails | Prioritize auth + LLM router. Defer monitoring polish |
| 6 | Regulatory data quality | Garbage-in risk | Manual QA pass on 10% of ingested regulations |
| 8 | No pilot customer LOI | G2 from venture plan | Pivot to SMB-first (Phase 2), defer compliance |
| 12 | Pilot failure rate high | Expert review data | Double HITL period, recalibrate before scaling |
| 14 | LLM cost exceeds margin target | Cost tracking data | Shift more to Haiku/GPT-4.1-mini, cache common assessments |
| 18 | ERP integration blocked by customer IT | Dependency on 3rd party | Offer standalone mode (manual data import) as interim |
| 20 | No revenue beyond pilot | G1.7 fails | Re-evaluate compliance vertical, consider pivot |

---

## Technology Stack Summary

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| API Framework | FastAPI (async) | Async-native, OpenAPI auto-docs, lightweight |
| Database | PostgreSQL 16+ | Multi-tenant, JSONB for flexible schemas, proven |
| ORM | SQLAlchemy 2.0 (async) | Type-safe, async session support |
| Migrations | Alembic | Standard, autogenerate support |
| Auth | JWT (RS256) | Stateless, org-scoped claims |
| Billing | Stripe Billing | Subscriptions, usage metering, invoicing |
| LLM Providers | Anthropic, OpenAI, Google | Multi-provider for fallback and cost optimization |
| Time-series | InfluxDB | Sensor telemetry storage and alerting |
| Monitoring | Prometheus + Grafana | Industry standard, self-hosted |
| Alerting | PagerDuty | On-call rotation, escalation |
| CI/CD | GitHub Actions | Standard, free for open-source |
| Infrastructure | Docker Compose (dev), Terraform (prod) | Local dev parity with production |
| Vector DB | ChromaDB (eval) / pgvector | RAG for Phase 3, evaluate during Phase 1 |

---

## Revenue Targets (Restated)

| Milestone | Timing | Target |
|-----------|--------|--------|
| Platform MVP | Week 3 | $0 (investment) |
| Pilot customer live | Week 8 | $0 (pilot, potentially discounted) |
| Pilot converting to paid | Week 14 | $50K implementation + $10K/mo |
| 1 enterprise + 2 mid-market signed | Week 20 | $100K implementation + $25K/mo |

---

## Existing Assets → Workflow Mapping

| Asset | Current State | Used In | Action |
|-------|--------------|---------|--------|
| `pricing_logic.py` | 25% — hardcoded tiers, in-memory | Wave 0.3 | Extract tier defs → Stripe Products |
| `compliance_engine.py` | 20% — additive risk, mock data | Wave 1.2, 1.3 | Extract multimodal concept; replace risk model entirely |
| `scaling_monitoring_tools.py` | 25% — in-memory metrics | Wave 0.5 | Extract health thresholds → Prometheus config |
| `rag_orchestrator.py` | 15% — fully mocked | Phase 3 (not this workflow) | Defer |
| `compliance_agent_specs.md` | 85% specified | Wave 1.1-1.4 | Primary reference for compliance agent implementation |
| `scaling_monitoring_specs.md` | 80% specified | Wave 0.5 | Reference for monitoring and observability |

---

## Next Steps After This Workflow

1. **Phase 2 Workflow** (SMB Productized Workflows) — begin Week 10, overlapping with Phase 1.5
2. **Phase 3 Workflow** (SDR Engine) — begin Week 20, contingent on Phase 1-2 revenue
3. **Phase 4 Workflow** (Operational Scaling) — continuous from Week 8
