# Profitable Ventures: Implementation Guide

This guide provides a detailed breakdown of the technical assets, implementation protocols, and monetization mechanics for the three high-margin AI agent business models outlined in the strategic blueprint.

---

## Directory Structure

```
docs/plans/Profitable-Ventures/
├── Profitable Ventures Implementation Plan.md   # Full strategic blueprint (source of truth)
├── implementation_guide.md                       # This file
├── specs/
│   ├── smb_agent_specs.md             # Phase 1: System prompts, rubrics, logic flows
│   ├── sdr_agent_specs.md             # Phase 2: RAG architecture, outreach sequences
│   ├── compliance_agent_specs.md      # Phase 3: Multimodal ingestion, EU AI Act guardrails
│   └── scaling_monitoring_specs.md    # Phase 4: Dashboard metrics, Shadow AI, prompt management
└── code/
    ├── pricing_logic.py               # Phase 1: Tier enforcement (action caps, workflow limits)
    ├── integration_templates.md       # Phase 1: n8n/Make JSON blueprints for lead/booking/invoice
    ├── rag_orchestrator.py            # Phase 2: Vector store indexing + Top-K retrieval
    ├── pipeline_tracking.md           # Phase 2: SQL schema + attribution/commission logic
    ├── compliance_engine.py           # Phase 3: Multimodal risk scoring + report generation
    └── scaling_monitoring_tools.py    # Phase 4: Health dashboard + Shadow AI network scanner
```

---

## Phase 1: Productized SMB Workflow Suite

### Target Market
Local/regional SMBs with zero operational automation (73% of the market). Plug-and-play agents that run inside apps already on the owner's phone.

### Five Core Agents

| Agent | Function | Key Metric | Model |
|:------|:---------|:-----------|:------|
| Lead Qualification | Intercept inquiries, score as HOT/WARM/COLD in <60s | +30-50% conversion rate | Claude Opus 4.6 |
| Appointment Booking | Calendar lifecycle (book/confirm/reschedule) via voice/SMS/email | -40-60% no-show rate | GPT-5.2 |
| Invoice Follow-Up | Escalating payment reminders (3d → 10d → 30d) with tone calibration | +50-60% payment velocity | Claude Opus 4.6 |
| Review Response | Monitor Yelp/Google/Facebook, auto-draft empathetic replies | +12% revenue from full response coverage | Claude Opus 4.6 |
| Inventory Alert | Predictive stockout forecasting from POS/Shopify data | -20-30% overstock costs | Gemini 3.1 Pro |

**Cost optimization**: Use Claude Haiku 4.5 or GPT-5.2-mini for high-volume background tasks (routine reminders) to compress API costs by 60-70%.

### Technical Assets

**`specs/smb_agent_specs.md`** — Contains:
- Lead Qualification system prompt with scoring rubric (budget/timeline/location criteria → HOT/WARM/COLD routing)
- Appointment Booking logic flow (availability check → 3 slots → confirm → 24h/2h reminder sequence)
- Invoice Follow-Up tone escalation table (gentle nudge at 3d → formal reminder at 10d → firm final notice at 30d)
- Review Response strategy (positive: gratitude + specific detail; negative: acknowledge → apologize → move to private channel)
- Inventory Alert formula: `ForecastDate = CurrentStock / AverageDailySellThrough`, alert when `ForecastDate < LeadTime + 7 Days`

**`code/pricing_logic.py`** — Tier enforcement engine:
- `PricingTier` class with `name`, `price`, `max_workflows`, `max_actions`
- Three tiers: STARTER ($500/mo, 1 workflow, 200 actions), GROWTH ($1000/mo, 3 workflows, 1000 actions), SCALE ($2000/mo, 5 workflows, unlimited)
- `ClientAccount.track_action()` hard-blocks after limit; `reset_month()` for billing cycle resets
- Verified: Starter tier correctly blocks at 200 actions

**`code/integration_templates.md`** — n8n/Make blueprints:
- Lead Qualification: Webhook (POST `/lead-intake`) → AI Agent (Claude Opus 4.6 with spec #1 prompt) → Switch node (HOT→SMS, WARM→Email Nurture, COLD→Disqualify)
- Appointment Booking: Message trigger → `Calendar.getAvailability` → Agent drafts options → `Calendar.createEvent` on confirm
- Invoice Follow-Up: Weekly cron → `Quickbooks.getOverdueInvoices` → Apply tone rubric from spec #3

### 6-Step Deployment Protocol
1. **Criteria Mapping** — Audit actual workflow (not claimed workflow). Build to run in apps already on the owner's phone.
2. **Intake Architecture** — n8n/Make webhooks capturing events from social forms, email, voice-to-text.
3. **Prompt Engineering** — System prompts with absolute guardrails, sequential questions, mathematical scoring rubric.
4. **Routing Configuration** — Divergent paths: HOT→immediate SMS, WARM→email nurture, COLD→polite disqualification.
5. **Stress Testing** — Adversarial inputs in sandbox: ideal customer, out-of-area, low-budget, ambiguous inquirer.
6. **Monitored Deployment** — 48h full audit → 2-week supervision → 20% randomized spot-check.

Target: <8h first deployment, 1-2h subsequent clients using refined templates.

### Monetization (85% Gross Margin)

| Tier | MRR | Workflows | Actions | Provider Cost | Margin |
|:-----|:----|:----------|:--------|:-------------|:-------|
| Starter | $500 | 1 | 200 | $50-80 | ~85% |
| Growth | $1,000 | 3 | 1,000 | $120-180 | ~85% |
| Scale | $2,000 | 5 | Unlimited | $200-350 | ~83% |

Solo operator at 10 Growth clients = $10,000 MRR, ~$8,800 net profit, 8-10h/week maintenance.

---

## Phase 2: Autonomous SDR Engine

### Target Market
B2B companies spending $700K-1M+ NOK/year on human SDRs for top-of-funnel cold outreach. The agent eliminates per-hour labor costs ($312-482 NOK/hr in Norway) with near-zero marginal cost at scale.

### Core Capabilities
- **Personalized cold outreach** across email, LinkedIn, and SMS with real-time contextual adaptation
- **Intelligent objection handling** — queries internal knowledge base to synthesize accurate technical responses
- **Pipeline resurrection** — scans dormant CRM "closed-lost" deals, re-engages when product updates solve the original objection
- **Multi-channel sequencing** — Day 1 LinkedIn → Day 3 Email → Day 7 SMS, with stop conditions

### Technical Assets

**`specs/sdr_agent_specs.md`** — Contains:
- RAG architecture: ChromaDB/Pinecone vector store → Query Augmentation → Top-K (3-5 chunks) → Contextual Injection with source citations
- Multi-channel outreach sequence: LinkedIn connection (Day 1) → Thought-leadership email with RAG whitepaper snippet (Day 3) → Soft SMS nudge (Day 7) → Stop on manual response or "Stop" keyword
- Intent scoring rubric: 0-3 (Archive), 4-7 (RAG Response + soft discovery call), 8-10 (Immediate AE Alert + booking link)
- Pipeline attribution: LeadID → Origin (agent) → Milestones (meeting booked → opp created → closed-won) with last-touch attribution

**`code/rag_orchestrator.py`** — Knowledge base engine:
- `RAGOrchestrator` class: `index_documents()` walks a `knowledge_base/` directory, `retrieve_context(query)` returns top-K relevant chunks
- `SDRAgent` class: `handle_reply(reply_text)` retrieves RAG context → constructs prompt with technical accuracy guidelines + soft discovery call proposal
- Currently mock/simulated — swap `vector_store=None` for ChromaDB/Pinecone client in production

**`code/pipeline_tracking.md`** — SQL schema + attribution logic:
- Three tables: `sdr_agents`, `leads` (with `intent_score` and `status` progression), `attribution_events` (BOOKING/OPP_CREATED/SALE with `deal_value`)
- Commission calculation: 5% default rate on closed-won deals
- Invoice generation: Sum of booking fees ($500/meeting) + sales commission per agent per month
- Performance tiers: Meeting fee $500-2,000 (industry dependent), closed-won sharing 3-10%

### 5-Step Implementation Protocol
1. **System & Data Audit** — Map CRM schema, isolate clean data (past transactions, ICPs, product specs). Garbage in = garbage out.
2. **Knowledge Base Integration** — Connect to product manuals, pricing matrices, Gong transcripts via RAG. Ensures brand-voice accuracy.
3. **Multi-Channel Orchestration** — Authorized API connections to email servers, LinkedIn automation, calendar scheduling. Encryption + MFA mandatory.
4. **Behavioral Parameterization** — Strict rules of engagement: follow-up frequency, tone calibration, intent threshold for AE routing.
5. **Iterative Testing** — Closed sandbox with synthetic prospect personas. Must achieve statistically significant accuracy before live deployment.

### Monetization Models

| Model | Structure | Revenue Range |
|:------|:----------|:-------------|
| Performance-Based | Pay per qualified meeting booked | $500-2,000 per meeting |
| SaaS Licensing | Base fee + variable compute cost | $3,000-5,000/mo + usage |
| Pipeline Percentage | % of closed-won revenue attributed to agent | 3-10% of deal value |

---

## Phase 3: Vertical-Specific Compliance Agents

### Target Market
Heavily regulated industries (aquaculture, energy, legal, healthcare, manufacturing) where generalist AI fails. Focus: Norwegian energy/aquaculture (Stavanger region) as operational blueprint.

### Core Capabilities
- **Multimodal data ingestion** — Live underwater video, sensor telemetry (water quality, sonar biomass), maintenance logs
- **Real-time regulatory cross-reference** — NYTEK, GDPR, EU AI Act databases checked against incoming data
- **Predictive risk assessment** — Anomaly detection triggers digital twin modeling of failure points + regulatory deadline lookup + auto-filled compliance docs
- **Norwegian Working Environment Act compliance** — Aggregated/anonymized performance data only, no individual PII storage

### Technical Assets

**`specs/compliance_agent_specs.md`** — Contains:
- Multimodal ingestion architecture: Vision layer (GPT-4o/Gemini 1.5 Pro for video), Sensor layer (InfluxDB for time-series), Cross-Reference Engine (risk evaluator against regulatory databases)
- EU AI Act guardrails: Mandatory HITL sign-off for physical infrastructure interventions, "Reasoning Trace" (CoT) with regulatory citations for every decision, periodic bias audits
- Report modules: Disaster mitigation assessments, DNV/Norwegian Maritime Authority pre-filled forms, real-time Compliance Health Score dashboard
- Norwegian Working Environment Act (Ch. 9/13): Anonymization layer aggregates at Team/Station level, strict prohibition on individual PII storage

**`code/compliance_engine.py`** — Multimodal risk scoring:
- `ComplianceMonitor` class: `process_multimodal_data(video_analysis, sensor_telemetry)` combines vision alerts (+70 risk) and sensor alerts (low oxygen: +40 risk)
- Risk threshold: score >50 triggers `generate_compliance_report()` with HITL alert
- Report output: Pre-filled regulatory doc with facility name, timestamp, findings, NYTEK Section 4 citation, decision trace with score breakdown
- Full audit log maintained as list of dicts (timestamp, facility, risk_score, findings, action_taken)
- Verified: "Critical" alert (anomaly + low oxygen) correctly generates pre-filled report

### 4-Phase Enterprise Implementation

| Phase | Duration | Deliverables |
|:------|:---------|:-------------|
| 1. Foundation | Weeks 1-4 | Executive sponsorship, data quality audit, infrastructure readiness assessment, strategic blueprint, data governance framework |
| 2. Expansion | Weeks 5-12 | Predictive algorithms, knowledge retrieval databases, digital twins of physical assets, single-facility pilot deployment |
| 3. Optimization | Weeks 13-24 | Human-in-the-loop model refinement, algorithmic explainability for audits, ERP/compliance software integration |
| 4. Innovation | Month 6+ | Horizontal scaling across facilities, transition from advisory to active orchestration role |

Critical: 95% of GenAI enterprise pilots fail without a defined roadmap, clear success criteria, or adequate data readiness.

### Monetization (Hybrid Structure)

| Component | Range |
|:----------|:------|
| Upfront Implementation Fee | $50,000 - $250,000+ |
| Monthly Licensing & Maintenance | $5,000 - $20,000+/mo |
| Multi-year contracts | Standard for enterprise tier |

Value prop: A single prevented environmental fine or operational shutdown delivers ROI exceeding lifetime system cost.

---

## Phase 4: Operational Scaling & Governance

### Cross-Cutting Infrastructure (applies to all three models)

**`specs/scaling_monitoring_specs.md`** — Contains:
- Centralized monitoring: Success rate %, latency, API burn rate (USD vs. budget), drift detection alerts
- Shadow AI discovery: Network scanning for known AI endpoints, packet inspection for API keys/sensitive data, policy enforcement alerts
- Bias detection: Parity audits, Equal Opportunity / Demographic Parity benchmarks, monthly automated decision log synthesis
- Prompt management: Git-based prompt registry, 10% A/B testing rollout, instant "Last Known Good" rollback

**`code/scaling_monitoring_tools.py`** — Two production-ready classes:
- `MonitoringDashboard`: `log_action(success, cost, latency)` with running average, `get_health_status()` returns GREEN (>95%) / AMBER (>85%) / RED with cost tracking
- `ShadowAIDiscovery`: `scan_outbound_log(log_entry)` checks against known AI endpoints (OpenAI, Anthropic, Google Vertex) and suspicious patterns (`sk-*` keys, `Bearer` tokens, `AI_SECRET`)
- Verified: API key pattern `sk-proj...` correctly flagged in network logs

### Governance Platforms

| Category | Function | When to Deploy |
|:---------|:---------|:---------------|
| Bias Detection & Fairness | Identify discriminatory patterns in AI outputs | Hiring, lending, healthcare decisions |
| Automated Monitoring | Track model behavior, detect data drift, flag anomalies | All production AI deployments |
| Compliance Management | Map AI to regulatory requirements, automate audit reports | EU AI Act, industry regs, privacy laws |
| Shadow AI Discovery | Scan networks for unauthorized AI usage | Large enterprises mitigating data leakage |

### Regulatory Compliance Checklist

- **EU AI Act** (Norway adoption mid-2026): Risk-based categorization, high-risk agents require human oversight + cybersecurity + decision transparency
- **GDPR**: Documented legal basis for processing personal data, consumer data erasure rights
- **Norwegian Working Environment Act (Ch. 9/13)**: No unlawful employee surveillance, anonymize/aggregate performance data, no automated employment decisions violating non-discrimination

---

## Verification Summary

| Asset | Verification |
|:------|:------------|
| `pricing_logic.py` | Starter tier correctly blocks actions at 200 limit |
| `rag_orchestrator.py` | SDR agent retrieves correct context for technical queries |
| `compliance_engine.py` | Critical alert (risk >50) triggers pre-filled regulatory report |
| `scaling_monitoring_tools.py` | API key patterns (`sk-proj...`) correctly flagged in network logs |

All assets preserve the strategic intent of the blueprint while providing clear technical implementation paths. Norwegian Working Environment Act and GDPR considerations are embedded throughout.
