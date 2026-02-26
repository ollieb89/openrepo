# Context: Phase 7 — Risk Drift Intelligence

## High-Level Goal
Proactively identify contradictions between natural language decisions (e.g., in Slack) and structured ticket metadata (e.g., in GitHub or Linear).

---

## 1. Auditing Frequency & Triggers
- **Immediate Auditing**: New Slack decisions should trigger an audit against linked tracker items as soon as they are detected.
- **Tracker Updates**: An update to a GitHub/Linear ticket (e.g., date change, priority shift) must trigger a re-audit of all related decisions.
- **Manual Overrides**: Provide a "Full Project Audit" button for users to trigger a manual sweep across all historical context for a project.
- **Per-Project Control**: The auditing frequency (real-time vs. batching) should be configurable per project or connector.

---

## 2. Uncertainty & Confidence Handling
- **Transparency**: The "Contradiction Reason" (LLM's internal logic) must be exposed to the user for every detected risk.
- **Low-Confidence Display**: Risks with low confidence scores should be displayed as "Potential Risk" or "Needs Review" rather than hidden.
- **User Sensitivity Control**: A "Risk Sensitivity" slider (1-10) should be available in project settings to let users define the confidence threshold for alerts.
- **Local Feedback**: "Not a Contradiction" feedback should only dismiss the individual alert (no global tuning of the auditing engine yet).

---

## 3. Sensitivity & Thresholds
- **Full Spectrum Detection**: Flag both objective mismatches (Dates, Owners) and subjective drift (Priority, Scope).
- **Missing Data Alerts**: If a decision in Slack (e.g., a deadline) is missing from the corresponding tracker ticket, flag it as a "Missing Implementation Risk".
- **Custom Drift Rules**: Support project-level risk rules where users can define specific logic for drift detection (e.g., "Flag if assignee is not the same as the Slack mention").
- **30-Day TTL**: Only audit Slack decisions that are less than 30 days old against current ticket states.

---

## 4. Lifecycle & Reconciliation
- **Ephemeral Resolution**: Delete a risk alert as soon as it is reconciled (e.g., the ticket is updated to match the Slack decision).
- **Snooze Support**: Users should be able to "Snooze" an active risk alert to remind them later.
- **Risk Re-activation**: If an alert is dismissed but the underlying data drifts further, the risk should be re-opened automatically.
- **History Log**: Maintain a persistent "Risk History" log to track resolution rates and common drift patterns over time.

---

## Next Steps
1. **Research**: Investigate LLM prompt strategies for "Decision vs. Tracker" contradiction detection and scoring.
2. **Planning**: Create implementation plans for the audit pipeline and risk scoring engine.
