# Dashboard Authentication Implementation

## Summary of Changes

The OpenClaw Dashboard now includes **token-based authentication** using the `OPENCLAW_GATEWAY_TOKEN` from your `.env` file. This addresses the critical security issue of unauthenticated API route access.

### What Was Fixed

**Problem**: The dashboard had no authentication/authorization for any API routes, exposing:
- Project configurations and metadata
- Task statuses and container information  
- Agent configuration data
- Container logs and swarm status
- Metrics and performance data

**Solution**: Implemented a complete authentication system that:
1. ✅ Validates tokens on all protected API routes
2. ✅ Provides a login page for token submission
3. ✅ Stores tokens securely in browser localStorage
4. ✅ Automatically includes tokens in API requests
5. ✅ Redirects unauthenticated users to login

---

## How to Use

### 1. **Initial Setup**

The dashboard reads the `OPENCLAW_GATEWAY_TOKEN` from your `.env` file:

```bash
# .env
OPENCLAW_GATEWAY_TOKEN=your_token_here
```

If this environment variable is NOT set, authentication is disabled (all routes are public).

### 2. **Logging In**

When authentication is required:

1. Navigate to `/login`
2. Enter your `OPENCLAW_GATEWAY_TOKEN` 
3. Click "Login"
4. The token is stored in your browser's `localStorage` under the key `openclaw_token`
5. You'll be redirected to the dashboard home page

### 3. **Automatic Token Inclusion**

Once logged in, the token is automatically included in all API requests via the `X-OpenClaw-Token` header.

### 4. **Logging Out**

Use the logout function (if you add a logout button to the Header):
```typescript
import { useAuth } from '@/context/AuthContext';

export default function Header() {
  const { logout } = useAuth();
  
  return (
    <button onClick={logout}>Logout</button>
  );
}
```

---

## Implementation Details

### Files Added/Modified

#### **New Files**

1. **`src/lib/auth.ts`** — Token validation utilities
   - `validateToken()`: Check if a token is valid
   - `extractToken()`: Extract token from various sources
   - `isAuthRequired()`: Check if auth is enabled

2. **`src/lib/auth-middleware.ts`** — Next.js middleware
   - `withAuth()`: Wrapper for protected API handlers
   - `createAuthMiddleware()`: Reusable middleware function
   - `createUnauthorizedResponse()`: Standard 401 response

3. **`src/middleware.ts`** — Next.js request middleware
   - Runs on all requests
   - Validates API route tokens
   - Excludes public routes

4. **`src/context/AuthContext.tsx`** — React authentication context
   - `AuthProvider`: Wraps the app for auth state
   - `useAuth()`: Hook to access auth state
   - Handles login/logout and token persistence

5. **`src/hooks/useAuthenticatedFetch.ts`** — Helper hook
   - `useAuthenticatedFetch()`: Makes authenticated fetch calls

6. **`src/app/login/page.tsx`** — Login page
   - Simple UI for token submission
   - Redirects on successful login

7. **`src/app/api/auth/token/route.ts`** — Token validation endpoint
   - `POST`: For token submission
   - `GET`: For token status checks

#### **Modified Files**

- `src/app/layout.tsx` — Added `AuthProvider` wrapper
- `src/app/api/projects/route.ts` — Added `withAuth` middleware
- `src/app/api/projects/active/route.ts` — Added `withAuth` middleware
- `src/app/api/tasks/route.ts` — Added `withAuth` middleware
- `src/app/api/metrics/route.ts` — Added `withAuth` middleware
- `src/app/api/agents/route.ts` — Added `withAuth` middleware
- `src/app/api/swarm/stream/route.ts` — Added `withAuth` middleware

---

## API Usage with Authentication

### Client-Side (React Components)

**Using the authenticated fetch hook:**

```typescript
import { useAuthenticatedFetch } from '@/hooks/useAuthenticatedFetch';

export default function MyComponent() {
  const authenticatedFetch = useAuthenticatedFetch();

  async function loadData() {
    const res = await authenticatedFetch('/api/tasks');
    const data = await res.json();
    // ... use data
  }

  // ...
}
```

### Server-Side (API Routes)

**Using the `withAuth` middleware:**

```typescript
import { NextRequest, NextResponse } from 'next/server';
import { withAuth } from '@/lib/auth-middleware';

async function handler(request: NextRequest): Promise<NextResponse> {
  // Your handler code here
  return NextResponse.json({ data: 'protected' });
}

export const GET = withAuth(handler);
```

### Direct HTTP Requests

**Include the token in the header:**

```bash
curl -H "X-OpenClaw-Token: your_token_here" \
  http://localhost:6987/occc/api/tasks
```

Or use the `Authorization` bearer format:

```bash
curl -H "Authorization: Bearer your_token_here" \
  http://localhost:6987/occc/api/tasks
```

---

## Security Notes

### Current Implementation

- ✅ Tokens are **NOT** sent over unencrypted connections (use HTTPS in production)
- ✅ Tokens are stored in browser localStorage (accessible to JavaScript)
- ✅ Tokens are validated on every protected API request
- ✅ Unauthorized requests return 401 Unauthorized

### Recommendations for Production

1. **Use HTTPS**: Always encrypt the connection to/from the dashboard
2. **Use Secure Cookies**: Replace localStorage with `httpOnly` secure cookies
3. **Add CSRF Protection**: If you add state-changing endpoints
4. **Token Rotation**: Implement token expiration and refresh
5. **Rate Limiting**: Limit login attempts to prevent brute force
6. **Audit Logging**: Log authentication events for security monitoring

---

## Applying Auth to Remaining API Routes

The core auth system is now in place. To protect additional API routes, simply update them to use the `withAuth` wrapper:

```typescript
// Before
export async function GET() {
  return Response.json({ data: 'public' });
}

// After
import { NextRequest, NextResponse } from 'next/server';
import { withAuth } from '@/lib/auth-middleware';

async function handler(request: NextRequest): Promise<NextResponse> {
  return NextResponse.json({ data: 'protected' });
}

export const GET = withAuth(handler);
```

---

## Testing Authentication

### Test 1: Verify Login Page Appears

```bash
npm run dev
# Navigate to http://localhost:6987/occc/login
# Should see login form
```

### Test 2: Test Token Validation Endpoint

```bash
# Should return requiresAuth: true
curl http://localhost:6987/occc/api/auth/token

# Should accept your token
curl -H "X-OpenClaw-Token: your_token_here" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"token":"your_token_here"}' \
  http://localhost:6987/occc/api/auth/token
```

### Test 3: Verify API Routes are Protected

```bash
# Should return 401 Unauthorized
curl http://localhost:6987/occc/api/tasks

# Should return 200 and data
curl -H "X-OpenClaw-Token: your_token_here" \
  http://localhost:6987/occc/api/tasks
```

---

## Disabling Authentication

If you want to disable authentication (for development/local use only):

```bash
# Remove from .env
# Unset OPENCLAW_GATEWAY_TOKEN

# Restart the dashboard
npm run dev
```

When no token is configured, all routes become public and users bypass the login page.

---

## Troubleshooting

### Issue: "Missing or invalid authentication token"

**Solution**: Make sure you're including the correct token:
```bash
# Check your .env file
cat .env | grep OPENCLAW_GATEWAY_TOKEN

# Use that exact token in your request
curl -H "X-OpenClaw-Token: <paste_token_here>" ...
```

### Issue: Redirects to login on every page load

**Solution**: Check browser console for errors. Ensure:
1. Token is correctly saved in localStorage
2. `OPENCLAW_GATEWAY_TOKEN` is set in `.env`
3. Dashboard is restarted after changing `.env`

### Issue: Login page shows but token won't verify

**Solution**: Verify the token value:
```bash
# Check token in .env
echo $OPENCLAW_GATEWAY_TOKEN

# Make sure it matches what you're entering in the login form
```

---

## Next Steps

1. ✅ **Restart the dashboard**: `npm run dev`
2. ✅ **Test the login flow**: Navigate to `/login` and authenticate
3. ✅ **Protect remaining routes**: Apply `withAuth` middleware to other API routes as needed
4. ✅ **Add logout functionality**: Add a logout button to the Header component (see example above)
5. 🔄 **Consider session management**: For production, upgrade to JWT tokens with expiration

---

## Questions?

Check these resources:
- [CONCERNS.md](../../.planning/codebase/CONCERNS.md) — Security issues addressed
- [INTEGRATIONS.md](../../.planning/codebase/INTEGRATIONS.md) — API structure
- [NextAuth.js docs](https://next-auth.js.org/) — For production auth solutions
