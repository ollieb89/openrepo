# Pipeline Tracking & Attribution Schema

This document defines the data structure for monetizing the SDR engine via performance-based metrics.

## Database Schema (SQL)
```sql
CREATE TABLE sdr_agents (
    agent_id UUID PRIMARY KEY,
    agent_name VARCHAR(255)
);

CREATE TABLE leads (
    lead_id UUID PRIMARY KEY,
    crm_id VARCHAR(255) UNIQUE,
    sdr_agent_id UUID REFERENCES sdr_agents(agent_id),
    intent_score INT DEFAULT 0,
    status VARCHAR(50) DEFAULT 'INITIAL_OUTREACH' -- INITIAL, QUALIFIED, MEETING_BOOKED, CLOSED_WON
);

CREATE TABLE attribution_events (
    event_id UUID PRIMARY KEY,
    lead_id UUID REFERENCES leads(lead_id),
    event_type VARCHAR(50), -- BOOKING, OPP_CREATED, SALE
    event_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deal_value DECIMAL(12, 2) DEFAULT 0.00
);
```

## Attribution Logic (Python Snippet)
```python
def calculate_commission(lead_id, closed_amount):
    """
    Calculate the 5% commission for a SDR-sourced deal.
    """
    commission_rate = 0.05
    return closed_amount * commission_rate

def generate_invoice(agent_id, month):
    """
    Sum up: 
    - Booking fees ($500 per meeting)
    - Sales commission (5% of closed-won)
    """
    # SQL: SELECT SUM(deal_value * 0.05) FROM attribution_events WHERE ...
    pass
```

## Performance Tiers
- **Meeting Fee**: $500 - $2,000 (Industry dependent).
- **Closed-Won Sharing**: 3% - 10% of final contract value.
```
