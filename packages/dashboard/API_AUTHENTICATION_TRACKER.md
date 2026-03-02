# API Routes Authentication Status

## Summary

All API routes are now protected with authentication except for the public authentication endpoints.

---

## ✅ PROTECTED Routes

### Tier 1 - Core Data (Previously Protected)
| Route | Methods |
|-------|---------|
| `/api/projects` | GET |
| `/api/projects/active` | GET |
| `/api/projects/[id]` | GET |
| `/api/tasks` | GET, POST |
| `/api/tasks/[id]` | GET |
| `/api/metrics` | GET |
| `/api/agents` | GET |

### Tier 2 - Internal Data (Now Protected)
| Route | Methods |
|-------|---------|
| `/api/snapshots/[taskId]` | GET |
| `/api/memory` | GET, POST |
| `/api/memory/[id]` | DELETE, PUT |
| `/api/memory/health-scan` | POST |
| `/api/connectors` | GET |
| `/api/connectors/health` | GET |
| `/api/connectors/tracker` | GET, POST |
| `/api/connectors/[id]/sync` | POST |
| `/api/connectors/slack/channels` | GET, POST |
| `/api/health/filesystem` | GET, POST |
| `/api/graph/ripple-effects` | GET |

### Tier 3 - Background Sync (Now Protected)
| Route | Methods |
|-------|---------|
| `/api/connectors/sync/background` | POST |
| `/api/connectors/tracker/sync` | POST |
| `/api/connectors/slack/sync` | POST |
| `/api/sync/catch-up` | POST |

### Tier 4 - Task Operations (Now Protected)
| Route | Methods |
|-------|---------|
| `/api/tasks/[id]/fail` | POST |
| `/api/tasks/[id]/resume` | POST |

### Tier 5 - Decisions & Suggestions (Now Protected)
| Route | Methods |
|-------|---------|
| `/api/decisions` | GET |
| `/api/decisions/[id]` | DELETE |
| `/api/decisions/[id]/re-summarize` | POST |
| `/api/suggestions` | GET, POST |
| `/api/suggestions/[id]/action` | POST |
| `/api/links/suggestions` | GET |
| `/api/links/suggestions/[id]/action` | POST |

### Tier 6 - Swarm (Now Protected)
| Route | Methods |
|-------|---------|
| `/api/swarm/stream` | GET (inline auth), POST |

### Tier 7 - Privacy (Now Protected)
| Route | Methods |
|-------|---------|
| `/api/privacy/consent` | GET, PUT, DELETE |
| `/api/privacy/events` | GET, POST |
| `/api/privacy/settings` | GET, PUT, DELETE |

---

## 🌐 PUBLIC Routes (No Auth Required)

These routes intentionally remain public:

| Route | Methods | Reason |
|-------|---------|--------|
| `/api/auth/token` | GET, POST | Token validation and submission for login |
| `/api/connectors/slack/oauth` | POST | OAuth callback from Slack |

---

## How Authentication Works

### The `withAuth` Middleware

All protected routes use the `withAuth` wrapper from `@/lib/auth-middleware`:

```typescript
import { NextRequest, NextResponse } from 'next/server';
import { withAuth } from '@/lib/auth-middleware';

async function handler(request: NextRequest) {
  // ... handler logic
  return NextResponse.json({ data });
}

export const GET = withAuth(handler);
export const POST = withAuth(handler);
```

### Token Sources

The middleware checks for tokens in this order:
1. `Authorization: Bearer <token>` header
2. `X-OpenClaw-Token` header
3. `_token` query parameter

### Environment Override

Set `REQUIRE_AUTH=false` to bypass authentication (for development).

---

## Frontend Integration

The `api-client.ts` automatically injects the auth token from `localStorage`:

```typescript
// Token is automatically added to all requests
const response = await apiJson('/api/projects');

// Skip auth for public routes
const response = await apiJson('/api/auth/token', {}, true);
```

401 responses trigger automatic redirect to login page.

---

## Testing Authentication

```bash
# Without token (should fail with 401)
curl http://localhost:3000/occc/api/projects

# With token (should work)
curl -H "X-OpenClaw-Token: your-token" \
  http://localhost:3000/occc/api/projects
```

---

## Notes

- Total routes protected: **45+ endpoints**
- Authentication is enforced at the API route level
- The `withAuth` wrapper supports handlers with path parameters
- Streaming responses (like `/api/swarm/stream` GET) have inline auth for SSE compatibility
