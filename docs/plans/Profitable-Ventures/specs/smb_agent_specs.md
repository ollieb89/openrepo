# Phase 1: SMB Workflow Suite Technical Specifications

This document defines the system prompts, rubrics, and logical flow for the five core SMB agents.

## 1. Lead Qualification Agent
**Objective**: Intercept inbound inquiries and qualify based on budget, timeline, and service fit.

### System Prompt Snippet
```markdown
You are a Lead Qualification Agent for [Business Name]. Your goal is to qualify inbound leads in under 60 seconds.
Follow this rubric:
- Budget: Must be > $[MinBudget].
- Timeline: Needs service within [X] weeks.
- Location: Must be within [Service Area].

Flow:
1. Greet and acknowledge specific inquiry.
2. Ask 2-3 targeted questions to extract the criteria above.
3. Score lead:
   - HOT: Meets all criteria. (Action: Trigger SMS Alert)
   - WARM: Meets 2/3 criteria. (Action: Start Email Nurture)
   - COLD: Fails core criteria. (Action: Polite Disqualification)
```

## 2. Appointment Booking Agent
**Objective**: Manage calendar scheduling, confirmations, and rescheduling via voice/text.

### Logic Flow
- **Step 1**: Check availability via [Calendar API] (Google/Outlook).
- **Step 2**: Offer 3 specific time slots.
- **Step 3**: Confirm booking and write to database.
- **Step 4**: Trigger sequence: 24h Reminder -> 2h Final Confirmation.

## 3. Invoice Follow-Up Agent
**Objective**: Accelerate payment velocity while maintaining client relationships.

### Tone Escalation Rubric
| Days Overdue | Tone | Channel |
| :--- | :--- | :--- |
| 3 Days | Gentle nudge, check if invoice was received. | Email |
| 10 Days | Formal reminder of payment terms. | Email + SMS |
| 30 Days | Firm final notice, mentioning potential pause in service. | SMS + Automated Call |

## 4. Review Response Agent
**Objective**: Autonomously respond to public feedback to boost SEO and reputation.

### System Prompt Strategy
- **Positive Reviews**: Express deep gratitude, mention a specific detail from the review, and invite back.
- **Negative Reviews**: Acknowledge the frustration immediately, apologize without admitting liability for complex issues, and move the conversation to a private channel (Email/Phone).

## 5. Inventory Alert Agent
**Objective**: Predictive stock monitoring to prevent stockouts.

### Analytical Parameters
- **Data Source**: Connection to Shopify/Square/POS.
- **Calculation**: `ForecastDate = CurrentStock / AverageDailySellThrough`.
- **Threshold**: Alert triggered when `ForecastDate < LeadTime + 7 Days`.
