# Implementation Workflow: Phase 4 — Operational Scaling

**Source:** `venture_plan.md` (Phase 4: Operational Scaling + Cross-Cutting Concerns)
**Generated:** 2026-02-25
**Strategy:** Continuous, milestone-gated, rolling deployment
**Duration:** Ongoing from Week 8 — no end date. Scales with product surface area.
**Nature:** Unlike Phases 1-3 (build → ship → sell), Phase 4 is operational infrastructure that grows alongside the business.

---

## Legend

- `[B]` = Blocked by predecessor
- `[P]` = Parallelizable with siblings
- `[G]` = Gate / decision point
- `[D]` = Deliverable artifact
- `[R]` = Risk checkpoint
- `[C]` = Continuous / recurring activity

---

## Strategic Context

Phase 4 is NOT a sequential build phase. It's four parallel operational capabilities that activate at different times as Phases 1-3 mature:

| Capability | Activates | Why Then |
|-----------|-----------|----------|
| Monitoring & Governance | Week 8 | First pilot customer goes live |
| Cost Attribution | Week 10 | SMB clients start consuming actions |
| Drift Detection | Week 14 | Enough baseline data to detect anomalies |
| Prompt Management | Week 10 | Multiple agent templates in production |
| Bias Auditing | Week 16 | Compliance agents making automated decisions |
| Shadow AI Scanner | Week 20 | Enterprise add-on, sells into compliance customers |

---

## STREAM A: Monitoring & Governance (Week 8+)

### Wave A.1 — Production Health Dashboard (Week 8-9)

> Upgrade from Phase 0 Prometheus/Grafana baseline to per-agent, per-client observability.

| # | Task | Type | Depends | Output | Notes |
|---|------|------|---------|--------|-------|
| A.1.1 | Per-agent metrics: success rate, latency p50/p95/p99, error classification | [B] | G0 (0.5.1) | Extended Prometheus metrics | Not just request-level — per agent type (Lead Qual, Booking, Compliance, etc.) |
| A.1.2 | Per-client metrics aggregation | [B] | A.1.1 | Grafana dashboards per client | SMB clients: actions/day, lead scores, bookings. Compliance: assessments, risk scores |
| A.1.3 | API cost burn rate dashboard | [B] | G0 (0.4.4) | Grafana panel | Real-time cost/hour, projected monthly, per-model breakdown. Alert on >2x baseline |
| A.1.4 | Alerting rules: critical paths | [B] | A.1.1, G0 (0.5.3) | PagerDuty integration | Success rate <85% → page. Latency p99 >10s → alert. Cost spike >2x → alert |
| A.1.5 | Health status API (external) | [B] | A.1.1 | `routes/ops/health.py` | Public status page for customers. Per-service health. Incident history |
| A.1.6 | Dashboard access control | [B] | A.1.2 | Grafana org/team provisioning | Clients see only their dashboards. Internal team sees all |

**Existing asset:** `scaling_monitoring_tools.py` (25%) — extract health threshold logic (GREEN/AMBER/RED). Replace in-memory with Prometheus backend.

**Gate GA.1:** Live dashboards showing real agent metrics from Phase 1 pilot. Alerts fire correctly on simulated degradation.

---

### Wave A.2 — Cost Attribution Engine (Week 10-12)

> Every LLM call, API request, and infrastructure unit attributed to a specific client, agent, and model.

| # | Task | Type | Depends | Output | Notes |
|---|------|------|---------|--------|-------|
| A.2.1 | Cost attribution schema | [B] | G0 (0.4.4) | `models/ops/cost_attribution.py` + migration | Dimensions: org_id, agent_type, model_id, timestamp. Rollup: hourly, daily, monthly |
| A.2.2 | Real-time cost ingestion pipeline | [B] | A.2.1 | `services/ops/cost_pipeline.py` | Every SmartRouter call → cost record. Async write (don't block agent execution) |
| A.2.3 | Margin analysis per client | [B] | A.2.2, G0 (0.3.3) | `services/ops/margin.py` | Revenue (Stripe) - Cost (attribution) = margin per client. Alert if margin <50% |
| A.2.4 | Model routing optimizer | [B] | A.2.3 | `services/ops/routing_optimizer.py` | Identify agents over-using expensive models. Suggest downgrades with quality impact estimate |
| A.2.5 | Cost attribution API + dashboard | [B] | A.2.3 | `routes/ops/costs.py` + Grafana | Internal: per-client P&L. Per-model cost trends. Routing optimization recommendations |
| A.2.6 | Monthly cost report generation | [C] | A.2.3 | Automated report | Per-client, per-agent cost breakdown. Margin trends. Model usage breakdown |

**Gate GA.2:** Can answer "What is our gross margin on Client X this month?" with data, not estimates.

---

### Wave A.3 — Drift Detection (Week 14-18)

> Detect when agent performance deviates from established baselines. Early warning before clients notice.

| # | Task | Type | Depends | Output | Notes |
|---|------|------|---------|--------|-------|
| A.3.1 | Baseline capture per workflow | [B] | GA.1 | `services/ops/baseline.py` | 2-week rolling window: success rate mean + σ, latency mean + σ, cost mean + σ |
| A.3.2 | Statistical drift detector | [B] | A.3.1 | `services/ops/drift_detector.py` | Alert on >2σ deviation sustained for >1hr. Separate thresholds for success, latency, cost |
| A.3.3 | Drift alert routing | [B] | A.3.2, A.1.4 | PagerDuty + Slack integration | Severity: 2σ → warning (Slack). 3σ → critical (PagerDuty). Include: metric, deviation, possible causes |
| A.3.4 | Root cause suggestion engine | [B] | A.3.2, A.2.2 | `services/ops/root_cause.py` | Correlate drift with: prompt change, model update, data pattern shift, upstream API degradation |
| A.3.5 | Drift dashboard | [B] | A.3.2 | Grafana panel | Per-agent drift status. Historical drift events. Correlation with deployments |
| A.3.6 | Automated rollback trigger (opt-in) | [B] | A.3.4, B.1.4 | Policy-based | If drift detected + recent prompt change → auto-rollback to last known good (requires prompt registry) |

**Gate GA.3:** Simulated drift (inject 20% error rate increase) detected and alerted within 15 minutes.

---

## STREAM B: Prompt Management (Week 10+)

### Wave B.1 — Prompt Registry & Versioning (Week 10-12)

> Git-versioned prompts with deployment tracking. Foundation for A/B testing and rollback.

| # | Task | Type | Depends | Output | Notes |
|---|------|------|---------|--------|-------|
| B.1.1 | Prompt schema: YAML format with metadata | [B] | G0 (0.5.9) | Extended prompt registry | Fields: version, agent_type, vertical, variables, model_target, author, changelog |
| B.1.2 | Prompt deployment tracker | [B] | B.1.1 | `services/ops/prompt_deploy.py` | Track: which prompt version → which clients → when deployed → by whom |
| B.1.3 | Prompt diff viewer | [B] | B.1.1 | `routes/ops/prompts.py` | Side-by-side diff between versions. Highlight variable changes vs content changes |
| B.1.4 | One-click rollback to "Last Known Good" | [B] | B.1.2 | Rollback service | Tag LKG per agent type. Rollback → redeploy to all clients on that template |
| B.1.5 | Cross-client push mechanism | [B] | B.1.2 | `services/ops/prompt_push.py` | Fix for one client → test against all same-template clients → push if improvement |
| B.1.6 | Prompt change audit log | [B] | B.1.2, G0 (0.5.7) | Audit trail entries | Every prompt change logged with: who, what, why, which clients affected |

**Gate GB.1:** Deploy new prompt version to subset of clients, verify via metrics, rollback if regression.

---

### Wave B.2 — A/B Testing Framework (Week 16-20)

> Statistical rigor for prompt optimization. Not just "try and see" — proper significance testing.

| # | Task | Type | Depends | Output | Notes |
|---|------|------|---------|--------|-------|
| B.2.1 | Traffic splitter: percentage-based routing | [B] | GB.1 | `services/ops/ab_splitter.py` | Default: 90% control / 10% variant. Configurable per experiment |
| B.2.2 | Experiment definition schema | [B] | B.2.1 | `models/ops/experiment.py` | Hypothesis, metric, control version, variant version, traffic split, duration, significance threshold |
| B.2.3 | Statistical significance calculator | [B] | B.2.2 | `services/ops/significance.py` | Two-proportion z-test for conversion metrics. Welch's t-test for continuous (latency, cost) |
| B.2.4 | Auto-graduation: promote winning variant | [B] | B.2.3 | Policy-based | p < 0.05 + minimum sample size → auto-promote variant to 100%. Notify team |
| B.2.5 | Auto-abort: kill losing variant | [B] | B.2.3 | Policy-based | p < 0.05 unfavorable + minimum sample → revert to control. Post-mortem logged |
| B.2.6 | Experiment dashboard | [B] | B.2.3 | Grafana or custom UI | Running experiments, metric comparison, significance progress, historical results |
| B.2.7 | A/B testing integration tests | [B] | B.2.4 | `tests/test_ab_testing.py` | Simulate traffic → split → measure → significance → graduate/abort |

**Gate GB.2:** Run experiment on real traffic. Variant wins with p<0.05. Auto-promoted. Metrics confirm improvement.

---

## STREAM C: Bias Auditing & Fairness (Week 16+)

### Wave C.1 — Compliance Agent Bias Framework (Week 16-20)

> Mandatory for compliance agents making automated risk decisions. EU AI Act requires this.

| # | Task | Type | Depends | Output | Notes |
|---|------|------|---------|--------|-------|
| C.1.1 | Bias audit data pipeline | [B] | Phase 1 live | `services/ops/bias_pipeline.py` | Extract decision data: agent type, inputs, outputs, risk scores, outcomes. Anonymized |
| C.1.2 | Demographic parity analysis | [B] | C.1.1 | `services/ops/fairness.py` | Compare decision distributions across: facility type, region, operator size, inspection history |
| C.1.3 | Equal opportunity analysis | [B] | C.1.1 | Within fairness service | For known outcomes: are true positive rates equal across groups? |
| C.1.4 | Disparate impact ratio calculation | [B] | C.1.2 | Within fairness service | 4/5ths rule: selection rate of any group < 80% of highest group → flag |
| C.1.5 | Automated monthly bias report | [C] | C.1.2-C.1.4 | `services/ops/bias_report.py` | PDF/JSON report: metrics, flags, trends, recommendations. Attached to audit trail |
| C.1.6 | Bias alert: threshold breach | [B] | C.1.4 | PagerDuty alert | Disparate impact ratio < 0.8 → immediate review required |
| C.1.7 | Remediation playbook | [D] | C.1.5 | Documentation | When bias detected: investigate → root cause → prompt adjustment → retest → document |

**Gate GC.1:** First monthly bias audit completes. No critical flags on pilot data. Report format approved by compliance lead.

---

### Wave C.2 — SMB Agent Fairness Extension (Week 22-26)

> Extend bias monitoring to SMB agents. Lower stakes than compliance but still important.

| # | Task | Type | Depends | Output | Notes |
|---|------|------|---------|--------|-------|
| C.2.1 | Lead scoring fairness analysis | [B] | GC.1, Phase 2 live | Extended pipeline | Are leads from certain demographics/regions systematically scored lower? |
| C.2.2 | Appointment allocation fairness | [B] | GC.1 | Extended pipeline | Are certain client types getting worse time slots or longer response times? |
| C.2.3 | Invoice tone escalation fairness | [B] | GC.1 | Extended pipeline | Is escalation timing consistent across invoice sizes and client demographics? |
| C.2.4 | Cross-agent fairness dashboard | [B] | C.2.1-C.2.3 | Grafana panels | All agents, all fairness metrics, trend over time |
| C.2.5 | Quarterly fairness review process | [C] | C.2.4 | Process document | Quarterly review: examine trends, adjust thresholds, update prompts if needed |

**Gate GC.2:** Fairness monitoring covers all production agents. No systematic bias detected. Process documented.

---

## STREAM D: Shadow AI & Enterprise Security (Week 20+)

### Wave D.1 — Shadow AI Scanner (Week 20-24)

> Enterprise add-on: detect unauthorized AI API usage within customer's network. Sells into compliance vertical.

| # | Task | Type | Depends | Output | Notes |
|---|------|------|---------|--------|-------|
| D.1.1 | AI endpoint registry (known providers) | [B] | G0 | `services/ops/ai_registry.py` | OpenAI, Anthropic, Google, Cohere, Mistral, HuggingFace, Replicate + API patterns |
| D.1.2 | Network log ingestion adapter | [B] | D.1.1 | `services/ops/network_ingest.py` | Accept: proxy logs (Squid, Zscaler), firewall logs (Palo Alto, Fortinet), DNS logs |
| D.1.3 | AI traffic detection engine | [B] | D.1.1, D.1.2 | `services/ops/shadow_detector.py` | Pattern match: endpoint URLs, API key headers, bearer tokens, model-specific request shapes |
| D.1.4 | Policy engine: authorized vs unauthorized | [B] | D.1.3 | `services/ops/ai_policy.py` | Customer defines allowed: which models, which teams, which use cases. Everything else → alert |
| D.1.5 | Shadow AI alert + report | [B] | D.1.4 | `routes/ops/shadow_ai.py` | Dashboard: detected AI usage, authorized/unauthorized split, usage trends, risk assessment |
| D.1.6 | Data classification integration | [P] | D.1.3 | `services/ops/data_classifier.py` | Detect if PII/sensitive data is being sent to unauthorized AI endpoints |
| D.1.7 | Shadow AI scanner tests | [B] | D.1.4 | `tests/test_shadow_ai.py` | Inject mock network logs with known AI traffic → verify detection + policy enforcement |

**Existing asset:** `scaling_monitoring_tools.py:ShadowAIDiscovery` (25%) — extract endpoint list and regex patterns. Replace simulated scanning with real log ingestion.

**Gate GD.1:** Scanner detects planted unauthorized AI API calls in test network logs with >95% recall.

---

### Wave D.2 — Enterprise Governance Package (Week 24-30)

> Bundle Shadow AI + compliance monitoring into sellable enterprise add-on.

| # | Task | Type | Depends | Output | Notes |
|---|------|------|---------|--------|-------|
| D.2.1 | Governance dashboard (unified) | [B] | GD.1, GC.1 | Single pane of glass | Shadow AI status + compliance risk + bias metrics + audit trail |
| D.2.2 | Role-based access: CISO, compliance officer, auditor | [B] | D.2.1 | RBAC extension | Different views per role. Auditor gets read-only with full history |
| D.2.3 | Automated governance report (monthly) | [C] | D.2.1 | PDF report generator | Executive summary: AI usage, compliance status, bias metrics, risk trends |
| D.2.4 | SOC 2 evidence collection | [B] | D.2.1 | `services/ops/soc2.py` | Auto-collect evidence for SOC 2 Type II: access logs, change management, incident response |
| D.2.5 | Enterprise pricing tier in Stripe | [B] | D.2.1 | Stripe Product | Governance add-on: $3K-$8K/mo on top of compliance base |
| D.2.6 | Enterprise sales collateral | [D] | D.2.3 | Marketing assets | Governance package one-pager, demo environment, ROI calculator |

**Gate GD.2:** Governance package demo-ready. First enterprise prospect sees unified dashboard.

---

## STREAM E: Regulatory Compliance Operations (Continuous)

### Wave E.1 — Ongoing Compliance Activities

> Not a build stream — recurring operational activities that must happen on schedule.

| # | Activity | Frequency | Depends | Owner | Notes |
|---|----------|-----------|---------|-------|-------|
| E.1.1 | EU AI Act risk assessment per new agent type | Per deployment | G0 (0.5.8) | Compliance lead | Document risk category, HITL requirements, transparency obligations |
| E.1.2 | GDPR data processing records update | Per new client | G0 (0.5.4) | Ops | New client → new processing record. Update on scope change |
| E.1.3 | Right-to-erasure request processing | On request | G0 (0.5.5) | Automated + audit | 30-day SLA. Cascading delete. Verification log |
| E.1.4 | Norwegian Marketing Act compliance review | Per SDR campaign | Phase 3 live | Legal | B2B cold outreach has narrower exemptions than US. Review per campaign |
| E.1.5 | Norwegian Working Environment Act audit | Quarterly | Phase 1 live | Compliance lead | Verify anonymization: no individual PII in compliance outputs |
| E.1.6 | Monthly bias/fairness audit | Monthly | GC.1 | Automated + review | Automated report → human review → remediation if needed |
| E.1.7 | Quarterly prompt review | Quarterly | GB.1 | Engineering | Review all production prompts. Retire unused. Update for model changes |
| E.1.8 | Annual GDPR compliance audit | Annual | G0 | External auditor | Full review: processing records, consent, erasure, DPA with processors |
| E.1.9 | EU AI Act technical documentation update | Semi-annual | G0 (0.5.8) | Compliance lead | Update as regulations evolve (EU AI Act provisions phasing in through 2027) |

---

## Activation Timeline

```
Week 8   ┌─ A.1 Health Dashboard (pilot goes live)
Week 10  ├─ A.2 Cost Attribution (SMB clients start)
         ├─ B.1 Prompt Registry (multiple templates in prod)
         ├─ E.1 Compliance Ops BEGIN
Week 14  ├─ A.3 Drift Detection (enough baseline data)
Week 16  ├─ B.2 A/B Testing (enough traffic for experiments)
         ├─ C.1 Bias Auditing (compliance agents deciding)
Week 20  ├─ D.1 Shadow AI Scanner (enterprise add-on)
Week 22  ├─ C.2 SMB Fairness Extension
Week 24  └─ D.2 Enterprise Governance Package
```

---

## Phase 4 — Deliverable Checklist

### Monitoring & Governance (Stream A)
- [ ] Per-agent, per-client metrics dashboards
- [ ] API cost burn rate with alerting
- [ ] Cost attribution: per-client, per-agent, per-model
- [ ] Per-client margin analysis (revenue - cost)
- [ ] Model routing optimizer
- [ ] Drift detection with >2σ alerting
- [ ] Root cause suggestion engine
- [ ] Automated rollback on drift + recent prompt change

### Prompt Management (Stream B)
- [ ] Versioned prompt registry (YAML + metadata)
- [ ] Deployment tracker (version → clients → timestamp)
- [ ] One-click rollback to Last Known Good
- [ ] Cross-client push mechanism
- [ ] A/B testing with statistical significance
- [ ] Auto-graduation/abort of experiments

### Bias & Fairness (Stream C)
- [ ] Demographic parity analysis for compliance agents
- [ ] Equal opportunity analysis
- [ ] Disparate impact ratio (4/5ths rule)
- [ ] Automated monthly bias reports
- [ ] SMB agent fairness extension
- [ ] Quarterly fairness review process

### Enterprise Security (Stream D)
- [ ] Shadow AI endpoint detection
- [ ] Network log ingestion (proxy, firewall, DNS)
- [ ] Policy engine: authorized vs unauthorized AI
- [ ] Data classification (PII to unauthorized endpoints)
- [ ] Unified governance dashboard
- [ ] SOC 2 evidence collection
- [ ] Enterprise governance package (sellable add-on)

### Regulatory Operations (Stream E)
- [ ] EU AI Act risk assessments per agent type
- [ ] GDPR processing records maintained
- [ ] Right-to-erasure automated with audit
- [ ] Norwegian Marketing Act review per SDR campaign
- [ ] Norwegian Working Environment Act quarterly audit
- [ ] Monthly bias audit cadence
- [ ] Quarterly prompt review cadence

---

## Phase 4 — Revenue Impact

Phase 4 is primarily a cost center with two exceptions:

| Component | Revenue Impact | How |
|-----------|---------------|-----|
| Shadow AI Scanner | Direct revenue | Enterprise add-on: $3K-$8K/mo per customer |
| Governance Package | Upsell revenue | Bundles with compliance platform, increases contract value 20-40% |
| Cost Attribution | Margin protection | Identifies unprofitable clients/agents before they erode margins |
| Drift Detection | Churn prevention | Catches degradation before clients notice → prevents cancellation |
| A/B Testing | Revenue optimization | Better prompts → higher conversion → higher client ROI → lower churn |
| Bias Auditing | Risk reduction | Prevents regulatory fines, reputational damage, contract termination |

### Enterprise Governance Revenue Projection

| Month | Customers | MRR |
|-------|-----------|-----|
| 6 (launch) | 0 (building) | $0 |
| 9 | 1-2 enterprise | $3K-$16K/mo |
| 12 | 3-5 enterprise | $9K-$40K/mo |

---

## Full Program Dependency Map (All Phases)

```
PHASE 0 (Wk 1-3)
  Auth─Billing─LLM Router─Monitoring─GDPR─Audit Trail
  │
  ├──────────────────────────────────────────────────────────┐
  │                                                          │
PHASE 1 (Wk 4-20)           PHASE 4 (Wk 8+ continuous)     │
  Regulatory DB               │                              │
  Multimodal Pipeline     A: Monitoring ← pilot data         │
  Risk Engine             A: Cost Attribution ← client data  │
  HITL + Reports          B: Prompt Registry ← templates     │
  Pilot ──────────────→   A: Drift Detection ← baseline      │
  Optimization            C: Bias Auditing ← decisions       │
  Sales Pipeline          D: Shadow AI ← enterprise need     │
       │                  D: Governance Package               │
       │                  E: Regulatory Ops (continuous)      │
       │                       │                              │
PHASE 2 (Wk 10-24)           │                              │
  Template Framework ─────→ B: A/B Testing ← traffic        │
  Lead Qual + Booking        C: SMB Fairness ← SMB data     │
  Comms Infrastructure                                       │
  First 5 Clients                                            │
  Invoice Follow-Up                                          │
  Scale to 10+                                               │
       │                                                     │
       └── Revenue gate ($15K+ MRR) ──→ PHASE 3 (Wk 20-36) │
                                          RAG Knowledge Base ┘
                                          CRM Integration
                                          Pipeline Resurrection
                                          Objection Handler
                                          Monetization
```

---

## Staffing Alignment with Phase 4

| Period | Phase 4 Focus | Who |
|--------|--------------|-----|
| Months 1-3 (Wk 1-12) | Monitoring + cost attribution setup | Founder (infra hat) |
| Months 4-6 (Wk 13-24) | Drift detection, prompt registry, bias v1 | Senior engineer |
| Months 7-9 (Wk 25-36) | A/B testing, Shadow AI, governance | Senior engineer + junior |
| Months 10-12 (Wk 37+) | Enterprise governance package, SOC 2 | Dedicated ops/compliance hire |

---

## Combined Go/No-Go Gates (All Phases)

| Gate | Phase | Timing | Criteria | If Fail |
|------|-------|--------|----------|---------|
| G0 | 0 | Week 3 | Auth, billing, monitoring, LLM router functional | Delay all phases, fix foundation |
| G1.4 | 1 | Week 7 | Compliance foundation complete, HITL working | Extend by 2 weeks max |
| G2 (LOI) | 1 | Week 8 | Signed LOI with ≥1 enterprise prospect | Pivot to SMB-first |
| GA.1 | 4A | Week 9 | Live dashboards with real pilot metrics | Fix before scaling |
| GA.2 | 4A | Week 12 | Per-client margin calculable from data | Cannot scale without margin visibility |
| G2.2 | 2 | Week 13 | Lead Qual + Booking agents functional E2E | Debug before client deployment |
| GA.3 | 4A | Week 18 | Drift detection catches simulated degradation | Fix alerting before 10+ clients |
| G3 (Economics) | 2 | Week 18 | 5+ clients, <5% churn, >70% margin | Adjust pricing or vertical |
| GB.2 | 4B | Week 20 | A/B test runs with statistical significance | Fix before prompt optimization at scale |
| GC.1 | 4C | Week 20 | First bias audit completes, no critical flags | Remediate before expanding compliance sales |
| GD.1 | 4D | Week 24 | Shadow AI detects planted traffic >95% recall | Fix before selling enterprise add-on |
| G4 (Resurrection) | 3 | Week 28 | >15% revival-to-meeting conversion | Kill Phase 3, reallocate |
| GD.2 | 4D | Week 30 | Governance package demo-ready | Delay enterprise sales, not core business |
| G3.5 | 3 | Week 36 | 3+ paying SDR customers, positive unit economics | Phase 3 is optional — focus on Phase 1-2 |
