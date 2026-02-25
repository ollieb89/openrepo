# Implementation Workflow: Phase 2 + Phase 3

**Source:** `venture_plan.md` (Phase 2: Productized SMB Workflows + Phase 3: Autonomous SDR Engine)
**Generated:** 2026-02-25
**Strategy:** Systematic, dependency-mapped, gate-driven
**Estimated Duration:** Weeks 10-36 (overlaps with Phase 1)
**Prerequisite:** Phase 0 complete (G0 passed)

---

## Legend

- `[B]` = Blocked by predecessor
- `[P]` = Parallelizable with siblings
- `[G]` = Gate / decision point
- `[D]` = Deliverable artifact
- `[R]` = Risk checkpoint

---

## PHASE 2: Productized SMB Workflows (Weeks 10-24)

### Strategic Context

**Vertical focus:** ONE vertical to start — dental practices or home services (plumbing, HVAC, electrical)
**Why these:** High no-show cost ($3K-$8K/mo recoverable), low tech sophistication, clear ROI, limited GoHighLevel penetration
**Revenue model:** Starter $500/mo, Growth $1,000/mo, Scale $2,000/mo — tiered by workflows + action limits
**Churn reality:** Budget 5% monthly churn → 5-6 new clients/year just to hold 10. First 90 days are critical.
**Labor reality:** 15-25 hrs/week, not the aspirational 8-10.

---

### Wave 2.1 — Agent Template Architecture (Week 10-11)

> Build the reusable template system that all SMB agents run on. This is the factory, not the agents themselves.

| # | Task | Type | Depends | Output | Notes |
|---|------|------|---------|--------|-------|
| 2.1.1 | Agent template framework: base class + lifecycle hooks | [B] | G0 | `services/smb/agent_template.py` | `BaseAgent` with: init → configure → deploy → monitor → teardown. Per-client config injection |
| 2.1.2 | Workflow execution engine | [B] | 2.1.1 | `services/smb/workflow_engine.py` | Trigger → condition check → action chain → result logging. Retry with exponential backoff |
| 2.1.3 | Per-client configuration store | [B] | G0 (0.2.1) | `models/smb/client_config.py` + migration | Business hours, timezone, tone preferences, integration credentials (encrypted) |
| 2.1.4 | Action metering integration | [B] | G0 (0.3.3) | `services/smb/metering.py` | Every agent action → Stripe usage record. Tier enforcement: soft-cap warning at 80%, hard-cap at limit |
| 2.1.5 | Client dashboard API | [B] | 2.1.3 | `routes/smb/dashboard.py` | Per-client view: actions consumed, leads scored, appointments booked, revenue recovered |
| 2.1.6 | Template framework tests | [B] | 2.1.2 | `tests/test_agent_template.py` | Template instantiation, config injection, action metering, tier enforcement |

**Gate G2.1:** Template framework can instantiate a no-op agent, meter actions, enforce tier limits.

---

### Wave 2.2 — P0 Agents: Lead Qualification + Appointment Booking (Weeks 11-13)

> The two highest-ROI agents. Lead Qual captures revenue, Appointment Booking recovers lost revenue.

#### 2.2a — Lead Qualification Agent

| # | Task | Type | Depends | Output | Notes |
|---|------|------|---------|--------|-------|
| 2.2.1 | Lead Qual system prompt (vertical-specific) | [B] | 2.1.1 | `prompts/smb/lead_qual_{vertical}.yaml` | 3-question rubric: budget, timeline, location. <60s response target |
| 2.2.2 | Inbound lead webhook handler | [B] | 2.1.2 | `services/smb/agents/lead_qual.py` | Website form, SMS, Facebook Messenger → unified lead intake |
| 2.2.3 | Lead scoring engine: HOT / WARM / COLD | [B] | 2.2.2 | Scoring logic in agent | HOT → immediate notification + CRM. WARM → nurture sequence. COLD → archive |
| 2.2.4 | CRM integration (generic adapter) | [P] | G0 | `services/integrations/crm_adapter.py` | Abstract interface. First impl: HubSpot free tier (most SMBs). Future: Salesforce |
| 2.2.5 | SMS/Email notification on HOT lead | [B] | 2.2.3 | Twilio + SendGrid integration | Owner gets SMS within 60s of HOT lead. Deliverability monitoring from day one |
| 2.2.6 | Lead Qual integration test | [B] | 2.2.3-2.2.5 | `tests/test_lead_qual.py` | Inbound lead → qualify → score → notify → CRM sync |

#### 2.2b — Appointment Booking Agent

| # | Task | Type | Depends | Output | Notes |
|---|------|------|---------|--------|-------|
| 2.2.7 | Booking system prompt (vertical-specific) | [B] | 2.1.1 | `prompts/smb/booking_{vertical}.yaml` | 3-slot offering, confirmation, rescheduling flows |
| 2.2.8 | Calendar integration (Google + Outlook) | [B] | G0 | `services/integrations/calendar.py` | OAuth2 flow, availability lookup, slot creation, conflict detection |
| 2.2.9 | Booking conversation flow | [B] | 2.2.7, 2.2.8 | `services/smb/agents/booking.py` | Natural language → slot selection → confirmation → calendar event created |
| 2.2.10 | Reminder sequence (24h + 2h before) | [B] | 2.2.9 | `services/smb/agents/booking_reminders.py` | SMS via Twilio. Haiku-routed (background task). Reschedule option in reminder |
| 2.2.11 | No-show detection + follow-up | [B] | 2.2.9 | Extension of booking agent | If no check-in within 15min of slot → SMS "Would you like to reschedule?" |
| 2.2.12 | Booking integration test | [B] | 2.2.9-2.2.11 | `tests/test_booking.py` | Book → confirm → remind → detect no-show → follow-up |

**Existing asset:** `smb_agent_specs.md` (95% specified, 0% code) — primary reference for both agents.

**Gate G2.2:** Both agents functional with mock calendar + CRM. Lead → qualify → score → book → remind flow works end-to-end.

---

### Wave 2.3 — Communication Infrastructure (Week 12, parallel with 2.2)

> Twilio + SendGrid + Voice AI setup. Shared across all SMB agents.

| # | Task | Type | Depends | Output | Notes |
|---|------|------|---------|--------|-------|
| 2.3.1 | Twilio SMS integration | [B] | G0 | `services/comms/sms.py` | Send/receive, delivery status webhooks, opt-out handling |
| 2.3.2 | SendGrid email integration | [P] | G0 | `services/comms/email.py` | Transactional emails, deliverability monitoring, bounce/complaint webhooks |
| 2.3.3 | Voice AI integration (Retell AI or Vapi) | [B] | G0 | `services/comms/voice.py` | Phone-based lead capture + booking. Evaluate Retell vs Vapi in Week 10-11 |
| 2.3.4 | Unified messaging orchestrator | [B] | 2.3.1-2.3.3 | `services/comms/orchestrator.py` | Channel selection logic: SMS for short, email for formal, voice for complex. Rate limiting per channel |
| 2.3.5 | Deliverability monitoring dashboard | [B] | 2.3.1, 2.3.2 | Grafana panels | Bounce rate, spam complaints, delivery rate per client. Alert on degradation |
| 2.3.6 | Comms integration tests | [B] | 2.3.4 | `tests/test_comms.py` | Send via each channel, verify delivery webhook, opt-out handling |

**Cost budget per Growth client/mo:** SMS ($30-50 via Twilio), Voice ($30-50 via Retell/Vapi), Email ($5-10 via SendGrid).

**Gate G2.3:** All three channels operational. Delivery monitoring active. Opt-out compliance working.

---

### Wave 2.4 — First 5 Clients (Weeks 14-18)

> Deploy Lead Qual + Booking to real businesses. Full audit for first 48 hours per client.

| # | Task | Type | Depends | Output | Notes |
|---|------|------|---------|--------|-------|
| 2.4.1 | Client onboarding flow (self-serve + assisted) | [B] | G2.2, G2.3 | `services/smb/onboarding.py` | Org setup → calendar connect → CRM connect → agent config → go-live |
| 2.4.2 | Client #1 deployment (Growth tier) | [B] | 2.4.1 | Live client | 48-hour full audit: review every interaction |
| 2.4.3 | Client #1 — 48hr audit report | [B] | 2.4.2 | Audit document | Tone accuracy, scoring correctness, false positives/negatives |
| 2.4.4 | Prompt tuning from audit findings | [B] | 2.4.3 | Updated prompts | Client-specific adjustments within template framework |
| 2.4.5 | Clients #2-5 deployment (staggered, 1/week) | [B] | 2.4.4 | 4 more live clients | Apply learnings from Client #1 to each deployment |
| 2.4.6 | 2-week supervised period per client | [B] | per client | Taper to 20% spot-check | Weekly check-in calls during supervised period |
| 2.4.7 | ROI documentation per client | [B] | 2.4.6 | Per-client ROI report | Leads responded to, response time delta, no-show rate change, conversion delta |
| 2.4.8 | First-90-day retention program launch | [B] | 2.4.2 | Retention playbook | Weekly ROI reports, proactive optimization, usage nudges |

**[R] Risk checkpoint (Week 16):** If churn >7% or client satisfaction <NPS 30, pause new deployments and diagnose.

**Gate G2.4:** 5 clients deployed. <5% monthly churn. ROI documented per client.

---

### Wave 2.5 — P1 Agent: Invoice Follow-Up (Weeks 16-18, parallel with 2.4)

> Third agent unlocked for Growth tier clients. +50-60% payment velocity.

| # | Task | Type | Depends | Output | Notes |
|---|------|------|---------|--------|-------|
| 2.5.1 | Invoice Follow-Up system prompt | [B] | 2.1.1 | `prompts/smb/invoice_{vertical}.yaml` | 3-stage tone escalation: gentle (Day 3) → formal (Day 10) → firm (Day 30) |
| 2.5.2 | Accounting integration adapter | [B] | G0 | `services/integrations/accounting.py` | QuickBooks Online first. Abstract interface for future (Xero, FreshBooks) |
| 2.5.3 | Invoice monitoring service | [B] | 2.5.2 | `services/smb/agents/invoice_followup.py` | Poll unpaid invoices daily. Trigger escalation sequence per aging policy |
| 2.5.4 | Tone escalation engine | [B] | 2.5.1, 2.5.3 | Within agent | Day 3: "Friendly reminder..." Day 10: "Please remit payment for invoice #..." Day 30: "Final notice..." |
| 2.5.5 | Payment confirmation + sequence stop | [B] | 2.5.3 | Webhook from accounting system | Payment received → immediately stop escalation, send thank-you |
| 2.5.6 | Invoice agent tests | [B] | 2.5.3-2.5.5 | `tests/test_invoice_followup.py` | Create overdue invoice → trigger sequence → simulate payment → verify stop |

**Gate G2.5:** Invoice Follow-Up agent deployed to 2+ existing Growth clients. Payment velocity improvement measured.

---

### Wave 2.6 — Scale to 10+ Clients (Weeks 18-24)

> Operational scaling, centralized monitoring, cross-client optimization.

| # | Task | Type | Depends | Output | Notes |
|---|------|------|---------|--------|-------|
| 2.6.1 | Centralized client health dashboard | [B] | G2.4, 0.5.2 | Grafana multi-client dashboard | Aggregate: active agents, actions/day, error rate, churn risk score per client |
| 2.6.2 | Cross-client prompt optimization pipeline | [B] | 2.4.4 | `services/smb/prompt_optimizer.py` | Fix for one client → evaluate against all same-template clients → push if improvement |
| 2.6.3 | P2 agent: Review Response (optional) | [P] | 2.1.1 | `services/smb/agents/review_response.py` | Google/Yelp review detection → tone-appropriate response. SEO-optimized positive replies |
| 2.6.4 | Referral program implementation | [P] | G2.4 | `services/smb/referral.py` | Existing client refers within vertical network. Track referral → conversion → reward |
| 2.6.5 | Automated onboarding (reduce human involvement) | [B] | 2.4.1 | Streamlined flow | Self-serve calendar + CRM connect. Human only for edge cases |
| 2.6.6 | Client #6-10+ deployment | [B] | 2.6.1, 2.6.5 | 5+ additional clients | Mix of Growth and Scale tiers |
| 2.6.7 | Churn prediction model (simple) | [B] | 2.6.1 | `services/smb/churn_predictor.py` | Usage drop + support ticket increase + payment delay → churn risk alert |
| 2.6.8 | Phase 2 financial review | [B] | 2.6.6 | Financial report | Actual vs projected: MRR, churn rate, gross margin, CAC, LTV |

**Gate G2.6 (= G3 from venture plan):** 10+ clients, <5% monthly churn, >70% gross margin validated.

**[R] Risk checkpoint (Week 22):** If unit economics don't hold at 10 clients, adjust pricing or vertical focus before Phase 3.

---

### Phase 2 — Deliverable Checklist

- [ ] Agent template framework with lifecycle hooks
- [ ] Lead Qualification agent (vertical-specific prompts)
- [ ] Appointment Booking agent with calendar integration
- [ ] Invoice Follow-Up agent with accounting integration
- [ ] Review Response agent (optional P2)
- [ ] Twilio SMS + SendGrid email + Voice AI operational
- [ ] Per-client action metering tied to Stripe
- [ ] Client dashboard showing ROI metrics
- [ ] Centralized multi-client health monitoring
- [ ] Cross-client prompt optimization pipeline
- [ ] Referral program live
- [ ] 10+ deployed clients with documented ROI
- [ ] Churn <5%/month, gross margin >70%

---

### Phase 2 — Margin Validation

| Cost Component | Per Growth Client/mo | Target |
|:---------------|:---------------------|:-------|
| LLM API (80% Haiku/GPT-4.1-mini) | $80-120 | Route routine through small models |
| Voice AI (Retell/Vapi) | $30-50 | Per-minute billing, cap at ~200 min/mo |
| SMS (Twilio) | $30-50 | ~500 messages/mo at $0.0079/segment |
| Email (SendGrid) | $5-10 | Transactional tier |
| Infrastructure (amortized) | $20-30 | Shared compute across clients |
| **Total provider cost** | **$165-260** | |
| **Revenue** | **$1,000** | Growth tier |
| **Gross margin** | **74-84%** | Target: >70% |

---

## PHASE 3: Autonomous SDR Engine (Weeks 20-36)

### Strategic Context

**Viability:** 5/10 — lowest of the three phases. Only proceed if Phase 1-2 revenue funds R&D.
**NOT building:** Full autonomous SDR platform (11x.ai has $74M, Artisan $46M in funding)
**Building instead:** Two focused capabilities:
1. **Pipeline Resurrection Engine** — standalone product, most differentiated
2. **RAG-Powered Objection Handler** — CRM add-on, not a replacement

**Revenue model:** $2K-$4K/mo SaaS + $200-$500 per revived meeting + $5K-$15K setup fee
**Go/No-Go prerequisite:** Phase 1-2 generating sufficient revenue (check at Week 20)

---

### Pre-Phase Gate

| Check | Criteria | If Fail |
|-------|----------|---------|
| Revenue gate | Phase 1 + Phase 2 combined >$15K/mo MRR | Defer Phase 3. Reallocate to Phase 1-2 growth |
| Margin gate | Blended gross margin >65% | Fix cost structure before adding more products |
| Capacity gate | Engineering bandwidth available | Hire before starting, or defer |

---

### Wave 3.1 — RAG Knowledge Base (Weeks 20-22)

> Production RAG system replacing the mocked `rag_orchestrator.py`. Foundation for both SDR capabilities.

| # | Task | Type | Depends | Output | Notes |
|---|------|------|---------|--------|-------|
| 3.1.1 | Vector store selection and setup | [B] | G0 | `services/sdr/vector_store.py` | Evaluate: pgvector (simplest, already have PG) vs ChromaDB (richer features). Decision by Week 20 |
| 3.1.2 | Embedding pipeline | [B] | 3.1.1 | `services/sdr/embedding.py` | Document → chunk (512 token windows, 50 token overlap) → embed (text-embedding-3-small) → store |
| 3.1.3 | Knowledge base ingestion: company docs, product specs, pricing, FAQs | [B] | 3.1.2 | `services/sdr/kb_ingest.py` | Per-customer knowledge base. Source-tagged chunks for citation |
| 3.1.4 | Retrieval service: top-K with relevance scoring | [B] | 3.1.3 | `services/sdr/retrieval.py` | Query → embed → similarity search → rerank → top 3-5 chunks with citations |
| 3.1.5 | RAG-augmented response generator | [B] | 3.1.4, 0.4.1 | `services/sdr/rag_responder.py` | Context injection into LLM prompt. Source citations in output. Haiku for simple, Sonnet for nuanced |
| 3.1.6 | Knowledge base management API | [B] | 3.1.3 | `routes/sdr/knowledge_base.py` | Upload docs, list indexed content, re-index, delete |
| 3.1.7 | RAG quality tests | [B] | 3.1.5 | `tests/test_rag.py` | Known Q&A pairs → verify correct retrieval + accurate response |

**Existing asset:** `rag_orchestrator.py` (15% ready) — extract separation-of-concerns pattern (orchestrator vs agent). Discard mock vector store, mock retrieval, stubbed LLM calls.

**Gate G3.1:** RAG system answers product questions accurately with source citations. Retrieval precision >80% on test set.

---

### Wave 3.2 — CRM Integration Layer (Weeks 21-23, overlaps with 3.1)

> Connectors for Salesforce and HubSpot. Needed by both Pipeline Resurrection and Objection Handler.

| # | Task | Type | Depends | Output | Notes |
|---|------|------|---------|--------|-------|
| 3.2.1 | CRM adapter interface (abstract) | [B] | G0 | `services/integrations/crm_adapter.py` | Extend existing adapter from Phase 2 (2.2.4) with deal/pipeline operations |
| 3.2.2 | Salesforce connector | [B] | 3.2.1 | `services/integrations/salesforce.py` | OAuth2 flow, deal CRUD, closed-lost scanning, activity logging, note extraction |
| 3.2.3 | HubSpot connector | [P] | 3.2.1 | `services/integrations/hubspot.py` | API key auth, deal pipeline, closed-lost scanning, email timeline extraction |
| 3.2.4 | Deal history extraction: notes, emails, transcripts | [B] | 3.2.2, 3.2.3 | `services/sdr/deal_history.py` | Full context per closed deal: why lost, who involved, what discussed |
| 3.2.5 | CRM integration tests | [B] | 3.2.2, 3.2.3 | `tests/test_crm_sdr.py` | Mock CRM APIs. Scan → extract → structure pipeline |

**Gate G3.2:** Can scan closed-lost deals from both CRMs, extract loss context, structure for analysis.

---

### Wave 3.3 — Pipeline Resurrection Engine (Weeks 23-28)

> The core differentiator. 25% of dead leads revivable within 12 months. Revival-to-opportunity: 30-50%.

| # | Task | Type | Depends | Output | Notes |
|---|------|------|---------|--------|-------|
| 3.3.1 | Loss reason analyzer (NLP) | [B] | G3.1, G3.2 | `services/sdr/loss_analyzer.py` | Extract from CRM notes + emails: pricing objection, feature gap, timing, competitor won, no budget, etc. |
| 3.3.2 | Loss reason taxonomy + classification | [B] | 3.3.1 | Structured loss categories | Standardized across CRMs: PRICE, FEATURE_GAP, TIMING, COMPETITOR, BUDGET, CHAMPION_LEFT, OTHER |
| 3.3.3 | Product-update matcher | [B] | 3.3.2, 3.1.3 | `services/sdr/product_matcher.py` | New feature/pricing released → scan loss reasons → identify addressable deals |
| 3.3.4 | Resurrection scoring model | [B] | 3.3.2 | `services/sdr/resurrection_scorer.py` | 0-100 score: recency, loss reason addressability, champion still present, company growth signals |
| 3.3.5 | Personalized re-engagement generator | [B] | 3.3.3, 3.3.4, 3.1.5 | `services/sdr/reengagement.py` | Context-rich email: references specific past conversation + what changed. RAG-powered accuracy |
| 3.3.6 | Re-engagement campaign orchestrator | [B] | 3.3.5, 2.3.4 | `services/sdr/campaign.py` | Email sequence (3 touches over 2 weeks). Stop on reply. Norwegian Marketing Act compliant |
| 3.3.7 | Campaign deliverability safeguards | [B] | 3.3.6 | Config + monitoring | Dedicated sending domain. 30/day/mailbox limit. 3-4 week warm-up. Stop on bounce spike >3% |
| 3.3.8 | Meeting booking from resurrection | [B] | 3.3.6, 2.2.8 | Calendar integration reuse | Interested reply → auto-propose meeting slots → book |
| 3.3.9 | Resurrection metrics tracking | [B] | 3.3.6, 3.3.8 | `services/sdr/metrics.py` | Deals scanned, qualified for resurrection, contacted, replied, meetings booked, conversion rate |
| 3.3.10 | Pipeline Resurrection E2E test | [B] | 3.3.8 | `tests/test_resurrection.py` | Import closed-lost → analyze → match to product update → generate outreach → simulate reply → book meeting |

**Existing asset:** `sdr_agent_specs.md` (90% specified) — reference for multi-channel sequence and pipeline attribution.
**Existing asset:** `pipeline_tracking.md` (60%) — SQL schema for leads + attribution. Extract and adapt.

**[R] Risk checkpoint (Week 26):** Run resurrection on pilot customer's closed-lost pipeline. If <10% qualify for outreach, the market signal is weak — reconsider.

**Gate G3.3 (= G4 from venture plan):** >15% revived-lead-to-meeting conversion in pilot. If fail → kill Phase 3, reallocate.

---

### Wave 3.4 — Objection Handler Add-On (Weeks 24-32, overlaps with 3.3)

> Intelligent reply handling for active pipeline. Not a full SDR — a CRM plugin.

| # | Task | Type | Depends | Output | Notes |
|---|------|------|---------|--------|-------|
| 3.4.1 | Reply classification engine | [B] | G3.1 | `services/sdr/reply_classifier.py` | Detect objection type from inbound email/LinkedIn: price, feature, competitor, timing, not interested |
| 3.4.2 | Intent scoring (0-10 scale) | [B] | 3.4.1 | Within classifier | 0-3: Archive. 4-7: RAG auto-response (draft). 8-10: Immediate AE alert |
| 3.4.3 | RAG-powered response drafting | [B] | 3.4.2, 3.1.5 | `services/sdr/objection_responder.py` | Objection type → query knowledge base → synthesize accurate, context-rich response |
| 3.4.4 | Human review queue | [B] | 3.4.3 | `services/sdr/review_queue.py` | Draft responses queue for AE review before sending. Trust-building phase |
| 3.4.5 | Review queue UI (minimal) | [B] | 3.4.4 | `routes/sdr/review.py` + frontend | AE sees: original message, objection type, intent score, drafted response, approve/edit/reject |
| 3.4.6 | AE feedback loop | [B] | 3.4.4 | Feedback capture | Edited responses → fine-tune prompts. Rejected drafts → analyze failure mode |
| 3.4.7 | Auto-send graduation (confidence-based) | [B] | 3.4.6 | Policy update | After N approved drafts with <10% edit rate → allow auto-send for that objection category |
| 3.4.8 | CRM activity sync | [B] | 3.4.3, G3.2 | CRM integration | All drafts/sends logged as CRM activities. Attribution to SDR engine |
| 3.4.9 | Objection Handler tests | [B] | 3.4.7 | `tests/test_objection_handler.py` | Inbound objection → classify → score → draft → review → send → log |

**Gate G3.4:** Objection handler drafting responses with >70% AE approval rate (no edits needed).

---

### Wave 3.5 — Monetization & Launch (Weeks 28-36)

> Pricing, billing, onboarding, and first paying customers.

| # | Task | Type | Depends | Output | Notes |
|---|------|------|---------|--------|-------|
| 3.5.1 | SDR product tiers in Stripe | [B] | G0 (0.3.2) | Stripe Products | Base SaaS: $2K-$4K/mo. Per-meeting fee: $200-$500. Setup: $5K-$15K |
| 3.5.2 | Meeting fee tracking + invoicing | [B] | 3.3.9, 3.5.1 | `services/sdr/billing.py` | Qualified meeting detected → usage record → appears on next invoice |
| 3.5.3 | CRM audit + KB indexing onboarding (setup fee deliverable) | [B] | G3.2, G3.1 | `services/sdr/onboarding.py` | Audit CRM data quality → ingest knowledge base → configure resurrection rules → go-live |
| 3.5.4 | Customer #1 deployment (pilot) | [B] | G3.3, 3.5.3 | Live customer | Discounted/free pilot converting to paid. Full HITL review for 2 weeks |
| 3.5.5 | Pilot metrics report | [B] | 3.5.4 | Case study | Deals scanned, resurrected, meetings booked, pipeline created, cost per meeting vs new lead |
| 3.5.6 | Customers #2-5 deployment | [B] | 3.5.5 | 4 additional customers | Apply learnings from pilot |
| 3.5.7 | Phase 3 financial review | [B] | 3.5.6 | Financial report | MRR, per-meeting revenue, setup fee revenue, gross margin, CAC |

**Gate G3.5 (Phase 3 Complete):** 3+ paying customers. Positive unit economics. Pipeline of 5+ prospects.

---

### Phase 3 — Deliverable Checklist

- [ ] Production RAG system with vector store + embedding pipeline
- [ ] Knowledge base management (upload, index, search, delete)
- [ ] Salesforce + HubSpot CRM connectors (deal scanning, history extraction)
- [ ] Loss reason analyzer (NLP classification of why deals failed)
- [ ] Product-update matcher (new feature → addressable lost deals)
- [ ] Resurrection scoring model (0-100 prioritization)
- [ ] Personalized re-engagement email generator (RAG-powered)
- [ ] Campaign orchestrator with deliverability safeguards
- [ ] Reply classification + intent scoring (0-10 scale)
- [ ] RAG-powered objection response drafting
- [ ] Human review queue with AE feedback loop
- [ ] Auto-send graduation (confidence-based)
- [ ] Meeting booking from resurrection pipeline
- [ ] Hybrid billing: SaaS base + per-meeting fee
- [ ] 3+ paying customers with documented ROI

---

### Phase 3 — Margin Validation

| Cost Component | Per Customer/mo | Notes |
|:---------------|:----------------|:------|
| LLM API — RAG retrieval (Haiku) | $30-60 | Embedding queries + chunk retrieval |
| LLM API — Response drafting (Sonnet) | $80-150 | Nuanced sales responses need quality |
| LLM API — Objection handling (Opus, rare) | $20-80 | Complex multi-turn objections only |
| Vector DB (pgvector, amortized) | $10-20 | Per-customer partition |
| CRM API usage | $0 (included in CRM subscription) | Salesforce/HubSpot API within standard limits |
| Email sending (dedicated domain) | $20-40 | Low volume per customer (30/day max) |
| Infrastructure (amortized) | $30-50 | Shared compute |
| **Total provider cost** | **$190-400** | |
| **Revenue (SaaS base only)** | **$2,000-4,000** | Before per-meeting fees |
| **Gross margin (SaaS only)** | **80-90%** | Per-meeting fees are nearly pure margin |
| **Blended with meeting fees** | **85-92%** | Assuming 2-5 meetings/mo at $300 avg |

---

## Cross-Phase Dependency Graph

```
PHASE 0 (Weeks 1-3)                                  PHASE 4 (Ongoing)
  [G0: Platform MVP] ─────────────────────────────→ Monitoring, Governance
        │                                              ↑
        ├─────────────────────────────────────────→ Prompt Management
        │                                              ↑
PHASE 1 (Weeks 4-20)                                   │
  1.1 Regulatory DB ──→ 1.4 HITL+Reports              │
  1.2 Multimodal    ──→    │                           │
  1.3 Risk Engine   ──→    │                           │
                      [G1.4]──→ 1.5 Pilot ──→ 1.6 ──→ │
                                   │                   │
PHASE 2 (Weeks 10-24)             │                   │
  2.1 Template Framework ──→ 2.2 P0 Agents            │
  2.3 Comms (parallel)  ──→    │                       │
                          [G2.2]──→ 2.4 First 5 ──→ 2.6 Scale 10+
                                      │              │
  2.5 Invoice Agent ──────────────────┘              │
                                                     │
PHASE 3 (Weeks 20-36)                               │
  Pre-phase gate ← Revenue from P1+P2 ──────────────┘
        │
  3.1 RAG Knowledge Base ──┬──→ 3.3 Pipeline Resurrection
  3.2 CRM Integration  ───┘        │
        │                    [G3.3]──→ 3.5 Monetize
  3.4 Objection Handler ──────────→    │
                                  [G3.5: Phase 3 Complete]
```

---

## Combined Risk Register (Phase 2 + Phase 3)

| Risk | Phase | Prob | Impact | Mitigation |
|------|-------|------|--------|------------|
| SMB churn exceeds 7%/month | P2 | High | Medium | First-90-day retention program, weekly ROI reports, embed in daily workflow |
| GoHighLevel undercuts pricing | P2 | Medium | Medium | Vertical specialization moat. They're horizontal at $97-297/mo — different market |
| Voice AI quality insufficient for booking | P2 | Medium | High | A/B test Retell vs Vapi in Week 10-11. Fallback to SMS-only booking |
| Calendar integration OAuth failures | P2 | Medium | Low | Support both Google + Outlook. Manual booking fallback |
| CRM data quality too poor for resurrection | P3 | High | High | CRM audit in onboarding (setup fee covers this). Disqualify if notes/emails sparse |
| Email deliverability destroyed | P3 | High | High | Dedicated sending domains, 30/day/mailbox, 3-4 week warm-up, stop on >3% bounce |
| AE adoption of review queue low | P3 | Medium | High | Embed in CRM (Salesforce sidebar). Don't require separate tool |
| Revival conversion <15% | P3 | Medium | High | Kill Phase 3 at G3.3. Reallocate to Phase 1-2 |
| Funded competitor launches similar resurrection | P3 | Medium | Medium | Speed, vertical specialization, bundle with compliance platform |

---

## Revenue Timeline (Combined All Phases)

| Month | Phase 1 (Compliance) | Phase 2 (SMB) | Phase 3 (SDR) | Total |
|-------|---------------------|---------------|---------------|-------|
| 3 | $0 (pilot) | $0 (building) | — | $0 |
| 6 | $10K/mo + $50K setup | $5K-$14K/mo | $0 (building) | $15K-$24K/mo |
| 9 | $15K-$25K/mo | $10K-$18K/mo | $9K-$20K/mo | $34K-$63K/mo |
| 12 | $25K-$40K/mo | $14K-$25K/mo | $15K-$30K/mo | $54K-$95K/mo |

---

## Shared Infrastructure Reuse Map

| Phase 0 Component | Used by Phase 2 | Used by Phase 3 |
|-------------------|-----------------|-----------------|
| Auth + multi-tenancy | Client org isolation | Customer org isolation |
| Stripe billing | Tier enforcement + metering | SaaS + per-meeting billing |
| SmartRouter | Haiku for reminders, Sonnet for conversations | Haiku for RAG, Sonnet for drafts, Opus for objections |
| Cost tracking | Per-client margin analysis | Per-customer margin analysis |
| Audit trail | Agent decision logging | Outreach + response logging |
| GDPR consent | Client data handling | Prospect data handling |
| Prompt registry | Vertical-specific agent prompts | Objection response prompts |
| Monitoring | Per-client health dashboards | Resurrection campaign metrics |
| Comms infra (Phase 2) | — | Re-engagement email sending |
| Calendar integration (Phase 2) | — | Meeting booking from resurrection |
| CRM adapter (Phase 2) | — | Extended for deal scanning |
