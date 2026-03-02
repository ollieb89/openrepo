# Dashboard Authentication - Quick Start Guide

## What Was Fixed

Your dashboard had **no authentication**, exposing all internal data (projects, tasks, agents, container logs, metrics) without requiring any password or token.

✅ **Now Fixed**: Token-based authentication using `OPENCLAW_GATEWAY_TOKEN` from your `.env` file.

---

## Quick Setup (2 minutes)

### Step 1: Restart the Dashboard

```bash
cd packages/dashboard

# Kill any running process
npm run dev
```

The dashboard will now read the `OPENCLAW_GATEWAY_TOKEN` from your `.env` file.

### Step 2: Login

1. Open http://localhost:6987/occc/
2. You should be **redirected to /login**
3. Copy your token from `.env`:
   ```bash
   grep OPENCLAW_GATEWAY_TOKEN .env
   # Output: OPENCLAW_GATEWAY_TOKEN=hPxqyUCJlT6SQUFKERkdgYZQD1gq2DfF5yUy1TmGhgcftjC3BPw05A3HAOmP6dav
   ```
4. Paste it into the login form
5. Click Submit

✅ You're now logged in! Token is saved in your browser.

---

##  How It Works

### Login Flow
```
User visits http://localhost:6987/occc/
↓
AuthProvider checks if token in localStorage
↓
No token? Redirect to /login
↓
User enters token, clicks Submit
↓
Token validated via POST /api/auth/token
↓
Token saved to localStorage
↓
Redirect to home dashboard
```

### API Protection
```
Client makes request: GET /api/tasks
↓
Middleware checks Authorization header (or X-OpenClaw-Token)
↓
Token invalid/missing? Return 401 Unauthorized
↓
Token valid? Continue to handler
```

---

## Using the Dashboard

### Within the Dashboard (Automatic)
- All API calls automatically include your token
- You don't need to do anything—just use the dashboard normally

### External API Calls
```bash
# Get your token
TOKEN="hPxqyUCJlT6SQUFKERkdgYZQD1gq2DfF5yUy1TmGhgcftjC3BPw05A3HAOmP6dav"

# Make authenticated request
curl -H "X-OpenClaw-Token: $TOKEN" \
  http://localhost:6987/occc/api/tasks
```

---

## Logout

To log out (add this button to your Header component):

```typescript
import { useAuth } from '@/context/AuthContext';

export function LogoutButton() {
  const { logout } = useAuth();
  return <button onClick={logout}>Logout</button>;
}
```

---

## Disable Authentication (Local Development)

To disable auth (for local development without a token):

```bash
# Remove/comment out in .env:
# OPENCLAW_GATEWAY_TOKEN=...

# Restart dashboard
npm run dev
```

When `OPENCLAW_GATEWAY_TOKEN` is not set, all routes are public.

---

## Protected Routes

The following routes now require authentication:

- ✅ `/api/projects`
- ✅ `/api/projects/active`
- ✅ `/api/projects/[id]`
- ✅ `/api/tasks`
- ✅ `/api/tasks/[id]`
- ✅ `/api/metrics`
- ✅ `/api/agents`
- ✅ `/api/swarm/stream`
- ⏳ Other routes (can be updated using the same pattern)

Public routes (no auth required):
- `/login`
- `/api/auth/token`
- `/api/health`

---

## Troubleshooting

### Problem: Still redirected to login after entering token

**Check:**
1. Did you copy the ENTIRE token from `.env`?
2. Is your browser allowing localStorage? (Check DevTools → Application → LocalStorage)
3. Did you restart the dashboard after `.env` changes?

**Fix:**
```bash
# Check token in .env
cat .env | grep OPENCLAW_GATEWAY_TOKEN

# Restart dashboard
npm run dev
```

### Problem: "Invalid token" error in login form

**Check:**
1. Token matches exactly what's in `.env`
2. No extra spaces or quotes

**Fix:**
```bash
# Make sure token is set
export OPENCLAW_GATEWAY_TOKEN="hPxqyUCJlT6SQUFKERkdgYZQD1gq2DfF5yUy1TmGhgcftjC3BPw05A3HAOmP6dav"
npm run dev
```

### Problem: Can't access API routes with token

**Check:** Token is being sent in the request header

```bash
#Test the auth endpoint
curl -H "X-OpenClaw-Token: your_token" \
  http://localhost:6987/occc/api/auth/token

# Should return: { "requiresAuth": true, "authenticated": true }
```

---

## File Summary

**New Files:**
- `src/lib/auth.ts` — Token validation
- `src/lib/auth-middleware.ts` — Route protection
- `src/middleware.ts` — Request-level auth enforcer
- `src/context/AuthContext.tsx` — Auth state management  
- `src/hooks/useAuthenticatedFetch.ts` — Authenticated HTTP calls
- `src/app/login/page.tsx` — Login page UI
- `src/app/api/auth/token/route.ts` — Token validation API
- `AUTHENTICATION.md` — Full documentation

**Modified Files:**
- `src/app/layout.tsx` — Added AuthProvider
- `src/app/api/projects/route.ts` ✅
- `src/app/api/projects/active/route.ts` ✅  
- `src/app/api/tasks/route.ts` ✅
- `src/app/api/metrics/route.ts` ✅
- `src/app/api/agents/route.ts` ✅
- `src/app/api/swarm/stream/route.ts` ✅

---

## Next Steps

1. ✅ Restart dashboard: `npm run dev`
2. ✅ Test login at `/login`
3. 🔄 **Optional**: Add logout button to Header
4. 🔄 **Optional**: Protect remaining API routes using `withAuth()` wrapper
5. 🔄 **Production**: Use HTTPS + secure cookies instead of localStorage

---

## Additional Resources

- [Full Authentication Documentation](./AUTHENTICATION.md)
- [Security Concerns Addressed](../.planning/codebase/CONCERNS.md)
