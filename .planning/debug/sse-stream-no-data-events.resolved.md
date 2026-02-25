---
status: resolved
trigger: "SSE endpoint /api/swarm/stream only sends keepalive, never data events"
created: 2026-02-23T00:00:00Z
updated: 2026-02-23T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED - Two bugs prevent data emission: (1) first-poll skip logic, (2) keepalive counter resets every poll
test: Code review comparison with working /api/logs/[agent] endpoint
expecting: Structural difference explaining missing data events
next_action: Report root cause

## Symptoms

expected: SSE stream emits `data:` events with JSON when workspace-state.json changes
actual: Only `: keepalive` comments are sent, never any `data:` lines
errors: None
reproduction: Connect to /api/swarm/stream, observe only keepalive
started: Since implementation

## Eliminated

(none needed - root cause found on first analysis)

## Evidence

- timestamp: 2026-02-23
  checked: stream/route.ts lines 43-63
  found: TWO bugs that together guarantee no data events are ever sent
  implication: See Resolution

## Resolution

root_cause: |
  Bug 1 (PRIMARY): Line 48 — `if (streamState.lastMtime !== 0 && currentMtime !== streamState.lastMtime)`
  skips data emission on the FIRST poll (lastMtime is 0), then on ALL subsequent polls where mtime hasn't
  changed since last poll. This means the client never gets an initial state snapshot — it only gets a
  thin `{"updated": true}` notification IF the file changes between two 1-second polls. Unlike the
  working /api/logs endpoint which sends `data: {"connected":true,...}` immediately in start(),
  the stream endpoint sends NO initial data event.

  Bug 2 (SECONDARY): Line 56 — `if (streamState.keepaliveCount >= 30)` with keepaliveCount incrementing
  every 1s poll means keepalive fires every ~30 seconds. BUT keepaliveCount is the ONLY thing the client
  sees because Bug 1 prevents all data events. The keepalive confirms connectivity but masks the real
  problem — no data is ever pushed.

  Bug 3 (DESIGN): Even when the file DOES change, the data payload is just `{"updated": true}` — a
  thin notification requiring the client to make a SECOND HTTP request to /api/swarm to get actual data.
  The working /api/logs endpoint streams actual log content directly.

fix: Code was completely rewritten during dashboard rework. The polling/mtime approach was replaced with direct container log streaming via streamContainerLogs() using ReadableStream + AbortSignal. All 3 bugs are gone.
verification: Confirmed 2026-02-25 — packages/dashboard/src/app/api/swarm/stream/route.ts no longer contains any of the original buggy patterns (no mtime polling, no keepalive counter, no thin notification payloads).
files_changed: [packages/dashboard/src/app/api/swarm/stream/route.ts]
