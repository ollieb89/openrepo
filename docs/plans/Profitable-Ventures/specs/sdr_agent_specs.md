# Phase 2: Autonomous SDR Engine Technical Specifications

This phase automates the high-value B2B sales development lifecycle using context-aware agents.

## 1. RAG-Enabled Knowledge Base
**Objective**: Ensure the SDR agent has deep, technically accurate knowledge of the company's products and policies.

### Architecture
- **Vector Store**: [ChromaDB / Pinecone] for indexing product manuals, Gong transcripts, and pricing matrices.
- **Retrieval Logic**:
  1. **Query Augmentation**: Rewrite prospect questions for better search relevance.
  2. **Top-K Retrieval**: Fetch top 3-5 relevant chunks.
  3. **Contextual Injection**: Force the agent to cite source material in its response.

## 2. Multi-Channel Outreach Orchestration
**Objective**: Maintain a persistent, intelligent presence across LinkedIn, Email, and SMS.

### Sequential Logic
- **Day 1**: Personalized LinkedIn Connection Request (Context: Mutual interest/Recent post).
- **Day 3 (If no response)**: Thought-leadership Email (Content: RAG-sourced whitepaper snippet).
- **Day 7**: SMS Follow-up (Tone: "Soft nudge", checking if email was received).
- **Stop Condition**: Manual response detected or "Stop" keyword.

## 3. Objection Handling & Intent Scoring
**Objective**: Grade prospect intent to determine when to route to a human Account Executive (AE).

### Intent Rubric
| Score | Behavior | Action |
| :--- | :--- | :--- |
| **0-3** | Generic "Not interested" or "Stop". | Archive / Polite Opt-out. |
| **4-7** | "Send more info" or specific technical query. | RAG Response + Soft Discovery-call proposal. |
| **8-10** | "Let's talk" or query about pricing/demo. | Immediate AE Alert + Booking Link dispatch. |

## 4. Pipeline Percentage Tracking
**Objective**: Monetize performance by tracking deal progression.

### Tracking Schema
- **LeadID**: Unique identifier linked to CRM.
- **Origin**: SDR Agent Name.
- **Milestones**:
  - Meeting Booked ($X fee).
  - Opportunity Created in CRM.
  - Closed-Won ($% Commission).
- **Attribution Logic**: Last-touch attribution for deals sourced by the SDR agent within [X] days.
