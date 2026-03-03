# Phase 60-02 Summary: Escalation Notifications & Real-time Alerts

**Status**: ✅ COMPLETE  
**Completed**: 2026-02-26  
**Plan**: 60-02-PLAN.md

## What Was Delivered

Implemented DSH-AUTO-02: Real-time escalation alerts and escalation context panel for operators.

### 1. Escalation Alert Banner (`EscalationAlertBanner.tsx`)

- Global fixed banner (top-right) when any task escalates
- WebSocket subscription to `autonomy.escalation_triggered`
- Shows task ID, reason, confidence score
- "View Task" and "Dismiss" actions
- Desktop Notification API integration (requests permission on first escalation)
- Handles both `event_type` and `type` for Python event bus compatibility

### 2. Escalation Context Panel (`EscalationContextPanel.tsx`)

- Detailed panel for escalated tasks in task detail view
- Shows reason, confidence at escalation, timestamp, status
- Autonomy event history (scrollable)
- Resume Task / Mark Failed buttons (call `/api/tasks/[id]/resume` and `/api/tasks/[id]/fail`)
- Red accent styling for urgency

### 3. Course Correction History (`CourseCorrectionHistory.tsx`)

- Expandable accordion of course corrections per task
- Uses `useCourseCorrections(taskId)` from WebSocket events
- Shows failed step action and recovery plan steps
- Timestamps for each correction

### 4. Global Escalations Dashboard (`EscalationsPage.tsx` + `/escalations` route)

- Dedicated page at `/escalations`
- Fetches `/api/tasks?state=escalating&project={projectId}`
- EscalationCard with View Details, Resume actions
- Empty state: "No escalated tasks. All autonomy agents running smoothly."
- Sorted by escalation timestamp (newest first)

### 5. Notification Settings (`NotificationSettings.tsx`)

- Desktop notification toggle
- Sound alert toggle
- Minimum confidence threshold slider (0–100%)
- Persisted to localStorage (`occc_notification_settings`)

### 6. API Routes

- `GET /api/tasks?state=escalating` — filter by task status
- `POST /api/tasks/[id]/resume?project={id}` — resume escalated task via Python state engine
- `POST /api/tasks/[id]/fail?project={id}` — mark task failed via Python state engine

## Files Modified/Created

| File | Changes |
|------|---------|
| `src/components/autonomy/EscalationAlertBanner.tsx` | Global escalation banner |
| `src/components/autonomy/EscalationContextPanel.tsx` | Escalation detail + Resume/Fail |
| `src/components/autonomy/CourseCorrectionHistory.tsx` | Course correction accordion |
| `src/components/autonomy/EscalationsPage.tsx` | Escalations list page |
| `src/components/autonomy/NotificationSettings.tsx` | Notification preferences |
| `src/app/escalations/page.tsx` | Escalations route |
| `src/app/layout.tsx` | EscalationAlertBanner in layout |
| `src/components/layout/Sidebar.tsx` | Escalations nav item |
| `src/app/api/tasks/route.ts` | `state` query param support |
| `src/app/api/tasks/[id]/resume/route.ts` | Resume API (spawns Python) |
| `src/app/api/tasks/[id]/fail/route.ts` | Fail API (spawns Python) |
| `src/lib/openclaw.ts` | `enrichTaskWithAutonomy()`, `getTaskState(projectId, { state })` |

## Dependencies

- WebSocket at `ws://localhost:8080/events` for real-time escalation events
- Browser Notification API
- `uv run python` for resume/fail (state engine update)

## Notes

- Resume/Fail APIs spawn `uv run python -c "from openclaw.state_engine import JarvisState; ..."` to update workspace-state.json with proper locking
- EscalationAlertBanner renders in root layout; visible across all pages
- NotificationSettings respects localStorage; desktop permission requested on first escalation
