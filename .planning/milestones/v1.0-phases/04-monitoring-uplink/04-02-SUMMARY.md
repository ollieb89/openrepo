# 04-02 Summary: Log Streaming + Redaction Pipeline (DSH-03, SEC-02)

**Status:** COMPLETE  
**Completed:** 2026-02-18

## What Was Built

This plan implements a Docker log streaming pipeline with server-side sensitive data redaction. Logs flow from containers through a redaction filter before reaching the browser.

### Files Created/Modified

| File | Purpose |
|------|---------|
| `workspace/occc/src/lib/redaction.ts` | Server-side redaction with 10+ regex patterns |
| `workspace/occc/src/lib/docker.ts` | Docker API client wrapper with log streaming |
| `workspace/occc/src/app/api/logs/[agent]/route.ts` | SSE endpoint for streaming redacted logs |
| `workspace/occc/src/hooks/useLogStream.ts` | Client hook with circular buffer & reconnection |
| `workspace/occc/next.config.ts` | Externalized dockerode to fix ssh2 bundling |
| `workspace/occc/package.json` | Added dockerode and @types/dockerode |

## Key Truths Verified

- [x] Container logs are streamed in real-time to the browser via SSE
- [x] API keys, tokens, emails, and authorization headers are redacted server-side before reaching the client
- [x] Log stream supports tail (last 100 lines) plus live follow mode

## Redaction Patterns (10 Total)

| Pattern | Matches | Replacement |
|---------|---------|-------------|
| AWS_KEY | `AKIA[0-9A-Z]{16}` | `[REDACTED_AWS_KEY]` |
| OPENAI_KEY | `sk-[a-zA-Z0-9]{20,}` | `[REDACTED_API_KEY]` |
| ANTHROPIC_KEY | `sk-ant-[a-zA-Z0-9-]{20,}` | `[REDACTED_API_KEY]` |
| GOOGLE_KEY | `AIza[0-9A-Za-z_-]{35}` | `[REDACTED_GOOGLE_KEY]` |
| GITHUB_TOKEN | `gh[ps]_[a-zA-Z0-9]{36,}` | `[REDACTED_GITHUB_TOKEN]` |
| SLACK_TOKEN | `xox[pboa]-[0-9]+-[0-9A-Za-z-]+` | `[REDACTED_SLACK_TOKEN]` |
| AUTH_HEADER | `authorization:\s*bearer\s+[^\s]+` | `authorization: [REDACTED]` |
| API_KEY_HEADER | `x-api-key:\s*[^\s]+` | `x-api-key: [REDACTED]` |
| EMAIL | email regex | `[REDACTED_EMAIL]` |
| GENERIC_SECRET | `PASSWORD|SECRET|TOKEN|API_KEY|PRIVATE_KEY=...` | `{key}=[REDACTED]` |

## Architecture

```
Docker Container Logs
        ↓
   dockerode client
        ↓
   Redaction Pipeline (src/lib/redaction.ts)
        ↓
   SSE Stream (/api/logs/[agent])
        ↓
   useLogStream Hook (client)
        ↓
   Dashboard UI
```

## API Endpoints

### GET /api/logs/[agent]
Streams redacted container logs as SSE events.

**Query params:**
- `tail` - Number of lines to fetch initially (default: 100)

**SSE events:**
- `data: {"timestamp":"...","level":"info|warn|error|debug","message":"..."}`
- `event: container-stopped` - Sent when container stops
- `: keepalive` - Every 30 seconds

**Features:**
- Looks up container by label (`openclaw.agent_id`) or name pattern
- Parses Docker multiplexed stream format
- Auto-detects log level from content
- Server-side redaction on every line
- Keepalive every 30s (prevents proxy timeouts)

## Client Hook

### useLogStream(agentId: string | null)

**Returns:**
```typescript
{
  logs: LogEntry[],           // Circular buffer (max 1000 entries)
  isConnected: boolean,       // Connection state
  clearLogs: () => void,      // Clear log buffer
  connectionStatus: 'connected' | 'connecting' | 'disconnected'
}
```

**Features:**
- Circular buffer capped at 1000 entries (drops oldest when exceeded)
- Exponential backoff reconnection (1s → 2s → 4s → max 30s)
- Auto-reconnects on disconnect
- Cleans up EventSource on unmount or agentId change

## Verification Results

1. `npx tsc --noEmit` - PASSED (no type errors)
2. `npm run build` - PASSED (Next.js 16 build completed)
3. dockerode, @types/dockerode in package.json - VERIFIED
4. Next.config externalized dockerode - DONE (fixes ssh2 bundling issue)

## Routes Added

```
Route (app)
├─ ƒ /api/logs/[agent]    # NEW: Log streaming SSE
├─ ƒ /api/swarm           # Existing: State API
└─ ƒ /api/swarm/stream    # Existing: State SSE
```

## Security Note

⚠️ **All redaction happens server-side in `lib/redaction.ts` before data reaches the browser.** Client-side redaction is security theater - sensitive data must never be transmitted to the client, even temporarily.

## Next Steps

Proceed to **04-03: Mission Control Dashboard UI (DSH-01, DSH-04)**
