# SMB Integration Templates (n8n / Make)

This document provides the structural blueprints for connecting the AI agents to external systems.

## Lead Qualification Workflow (JSON Blueprint)
```json
{
  "nodes": [
    {
      "name": "Webhook: Inbound Lead",
      "type": "n8n-nodes-base.webhook",
      "parameters": { "path": "lead-intake", "httpMethod": "POST" }
    },
    {
      "name": "AI Agent: Qualify",
      "type": "n8n-nodes-base.aiAgent",
      "parameters": {
        "model": "claude-4.6-opus",
        "systemPrompt": "Use smb_agent_specs.md #1 Lead Qualification Agent"
      }
    },
    {
      "name": "Switch: Score",
      "type": "n8n-nodes-base.switch",
      "parameters": {
        "rules": [
          { "value": "HOT", "destination": "SMS Alert" },
          { "value": "WARM", "destination": "Email Nurture" },
          { "value": "COLD", "destination": "Disqualify" }
        ]
      }
    }
  ]
}
```

## Appointment Booking Sync
- **Trigger**: New message from Lead.
- **Action**: Query `Calendar.getAvailability`.
- **Response**: Agent drafts availability options.
- **Finalize**: `Calendar.createEvent` on confirmation.

## Invoice Guardrail
- **Trigger**: Weekly Cron job.
- **Action**: Query `Quickbooks.getOverdueInvoices`.
- **Logic**: Apply `smb_agent_specs.md #3` tone rubric.
