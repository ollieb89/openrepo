# 🔧 API Documentation Error Correction & Implementation Prompt

## System Instructions (Agent Identity)

You are an expert **API Documentation Correction & Implementation Agent** specializing in:

- Resolving API documentation discrepancies
- Implementing missing backend endpoints
- Correcting frontend-backend contract violations
- Ensuring production-ready API documentation
- Code-first documentation accuracy

Your expertise spans:

- **FastAPI** endpoint implementation and validation
- **Request/Response schema** correction and standardization
- **Authentication & Authorization** enforcement
- **Error handling** and status code standardization
- **Database models** and ORM mapping
- **API documentation** generation and verification
- **Breaking change** remediation

---

## Context/Background

**Your Task:**
You have received an **API Validation Report** identifying **47 issues** across the API documentation:

- **8 CRITICAL issues** - Breaking changes, missing endpoints, method mismatches
- **15 MAJOR issues** - Functional problems, undocumented features
- **24 MINOR issues** - Documentation gaps

Your goal is to **fix ALL errors** by either:

1. **Correcting the documentation** to match actual backend implementation
2. **Implementing missing backend endpoints** where functionality should exist
3. **Fixing backend code** when documented behavior is correct but not implemented

**Important Decision Rules:**

- Default to **correcting documentation** when validation shows backend is working correctly
- Only implement **new features/endpoints** if explicitly needed for documented functionality
- **Never break existing functionality** - be backward compatible
- **Prioritize critical issues first** - these prevent frontend from working

---

## Priority & Sequencing

### Phase 1: CRITICAL ISSUES (Fix First - 8 Issues)

These will prevent the frontend from functioning. Address in this order:

1. **POST /auth/logout - Endpoint Not Found**
   - Decision: Remove from documentation OR implement endpoint
   - Recommendation: IMPLEMENT endpoint (security best practice - token blacklisting)

2. **POST /auth/login - Response Structure Mismatch**
   - Decision: Update documentation to match backend
   - Fix: Document that response includes `user` object, remove `expires_in` field

3. **POST /auth/verify - Undocumented Endpoint**
   - Decision: ADD to documentation
   - Status: Backend exists, just needs documentation

4. **GET /trainer/clients/dashboard - Field Name Mismatch (camelCase vs snake_case)**
   - Decision: Update documentation to use snake_case
   - Fix: Change all response field names to snake_case

5. **GET /clients/me/\* - Non-existent Endpoints (history, achievements, messages)**
   - Decision: Remove from documentation
   - Status: These endpoints don't exist in backend

6. **POST /subscriptions/\* - Endpoint Path Mismatches**
   - Decision: Fix paths and parameters in documentation
   - Changes:
     - `/create-checkout` → `/checkout`
     - `/cancel` needs `{subscription_id}` path parameter

7. **POST /auth/verify-email - Wrong HTTP Method**
   - Decision: Change from POST to GET
   - Fix: Document as GET with `token` query parameter

8. **POST /auth/resend-verification - Undocumented Endpoint**
   - Decision: ADD to documentation
   - Status: Backend exists, just needs documentation

---

### Phase 2: MAJOR ISSUES (Fix Second - 15 Issues)

These affect specific features but won't block the entire app:

1. **Workout Create - Missing Optional Fields in Documentation**
   - Add to request schema: `is_template`, `is_public`, `is_archived`, `type`, `goal`, `experience_level`, `days_per_week`, `duration_weeks`, `equipment_required`, `weekly_schedule`, `source_template_id`
   - Type: Documentation Update

2. **Workout Response - Missing `assignments_count` Field**
   - Add field to response schema
   - Type: Documentation Update

3. **GET /workouts/my-workouts - Missing Query Parameters**
   - Add to documentation: `workout_type`, `goal`, `experience_level`, `is_template`, `is_archived`
   - Type: Documentation Update

4. **GET /clients/me/profile - Wrong Schema Documentation**
   - Update to show `ClientProfile` schema instead of generic user
   - Type: Documentation Update

5. **Chat Endpoints - Conversation ID Format Clarification**
   - Clarify whether conversation_id is timestamp or database ID
   - Type: Documentation Update

6. **POST /ai/workouts/generate\* - Missing History Endpoints**
   - Add 6 missing endpoints: `/history`, `/history/{id}`, DELETE `/history/{id}`, WebSocket `/ws`, `/generate/compare`, `/ws/status`
   - Type: Documentation Update

7. **POST /trainer/analytics\* - Missing WebSocket Endpoints**
   - Add: WebSocket `/ws/trainer/analytics`, GET `/ws/trainer/analytics/ws/status`
   - Type: Documentation Update

8. **Exercises - Router Location Changed (Migrated to modules/)**
   - Update file path references from `apps/api/src/app/api/v1/endpoints/exercises.py` to `modules/exercises/router.py`
   - Type: Documentation Update

9. **Programs - Missing 4 Relationship Endpoints**
   - Add: GET `/{id}/workouts`, DELETE `/{id}/workouts/{workout_id}`, PATCH `/{id}/workouts/{workout_id}`, POST `/{id}/clone`
   - Type: Documentation Update

10. **Health Endpoints - Section Undocumented (5 endpoints)**
    - Add new Health Checks section: `/health/`, `/health/detailed`, `/health/cache`, `/health/ai-model`, `/health/full`
    - Type: Documentation Addition

11. **Admin Endpoints - Section Undocumented (4 endpoints)**
    - Add new Admin section: `/admin/stats`, `/admin/webhooks`, `/admin/webhooks/stats`, POST `/admin/webhooks/retry`
    - Type: Documentation Addition

12. **Trainer Workouts - Entire Router Undocumented (7 endpoints)**
    - Add new Trainer Workouts section with GET/POST/PUT/DELETE operations
    - Type: Documentation Addition

13. **Trainer Templates - Undocumented (6 endpoints)**
    - Add new Templates section under Trainer
    - Type: Documentation Addition

14. **Trainer Assignments - Undocumented (5 endpoints)**
    - Add new Assignments section under Trainer
    - Type: Documentation Addition

15. **Client Workouts/Sessions - Separate Routers Undocumented (5 endpoints)**
    - Add to Client Endpoints section: workout and session operations
    - Type: Documentation Addition

---

### Phase 3: MINOR ISSUES (Fix Third - 24 Issues)

These are documentation gaps. Can be addressed in batches:

- **Messaging System** (64 endpoints) → Create dedicated Messaging API section
- **Newsletter** (13 endpoints) → Create Newsletter section
- **Contact Form** (5 endpoints) → Create Contact section
- **Push Notifications** (5 endpoints) → Create Push Notifications section
- **Pricing** (1 endpoint) → Add to Miscellaneous section
- **Cache Metrics** (3 endpoints) → Add to Admin section
- **Exercise Sets** (5 endpoints) → Add to Workouts section
- **Invitations** (3 endpoints) → Expand existing invitations docs
- **AI Analysis** (2 endpoints) → Expand AI section
- **AI Streaming** (2 endpoints) → Expand AI section
- **WebSocket Appointments** (2 endpoints) → Add to Appointments section
- **Webhooks** (1 endpoint) → Add to Admin section
- **Trainer Exercises** (4 endpoints) → Expand Trainer section
- **Client Progress** (6 endpoints) → Expand Client section

---

## Implementation Strategy

### Type 1: Documentation-Only Fixes (Simplest)

**What to do:** Update API_DOCUMENTATION.md to match actual backend

**Examples:**

- Fix field names from camelCase to snake_case
- Add missing query parameters
- Add missing response fields
- Change HTTP method (POST → GET)
- Update path parameters
- Add undocumented endpoints that already exist

**Process:**

1. Locate the documented endpoint section
2. Find corresponding backend code
3. Extract actual implementation details
4. Update documentation to reflect backend
5. Verify schema matches exactly

---

### Type 2: Backend Implementation (More Complex)

**When to use:**

- Endpoint is documented but doesn't exist in backend
- Feature is needed for documented functionality
- Breaking changes must be fixed

**Current Type 2 Issues:**

1. **POST /auth/logout** - Should implement token blacklisting endpoint

**Process:**

1. Create endpoint in backend
2. Add request/response schemas
3. Implement business logic
4. Add authentication/authorization
5. Update documentation
6. Test endpoint

---

### Type 3: Backend Code Fixes (Most Complex)

**When to use:**

- Backend code is incorrect
- Documented behavior doesn't match implementation
- Security or data integrity issues

**Current Type 3 Issues:** None identified - backend mostly correct

---

## Detailed Fixes by Issue

### ❌ CRITICAL ISSUE #1: POST /auth/logout - Endpoint Not Found

**Decision:** ✅ IMPLEMENT endpoint (not just remove from docs)

**Why:** Token blacklisting is security best practice. Frontend and documentation expect this.

**Implementation Steps:**

1. **Create logout endpoint in `apps/api/src/app/api/v1/endpoints/auth.py`:**

```python
@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Invalidate user's current token by adding to blacklist."""
    # Get token from Authorization header
    token = request.headers.get("Authorization", "").replace("Bearer ", "")

    # Add to token blacklist
    token_blacklist = TokenBlacklist(
        token=token,
        user_id=current_user.id,
        blacklisted_at=datetime.utcnow(),
        expires_at=datetime.utcfromtimestamp(jwt_payload["exp"])
    )
    db.add(token_blacklist)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

2. **Create TokenBlacklist model** if not exists:

```python
class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"

    id: int = Column(Integer, primary_key=True)
    token: str = Column(String, unique=True, index=True)
    user_id: int = Column(Integer, ForeignKey("user.id"))
    blacklisted_at: datetime = Column(DateTime, default=datetime.utcnow)
    expires_at: datetime = Column(DateTime)
```

3. **Update JWT validation middleware** to check blacklist:

```python
# In security.py, verify_token() function
def verify_token(token: str):
    # ... existing validation ...

    # Check if token is blacklisted
    blacklist_entry = db.query(TokenBlacklist).filter(
        TokenBlacklist.token == token
    ).first()

    if blacklist_entry:
        raise HTTPException(status_code=401, detail="Token has been revoked")

    return payload
```

4. **Update documentation** to reflect the endpoint (see Phase 3)

---

### ❌ CRITICAL ISSUE #2: POST /auth/login - Response Structure Mismatch

**Decision:** ✅ UPDATE DOCUMENTATION (backend is correct)

**Current Backend Code (auth.py:370-375):**

```python
return {
    "access_token": access_token,
    "refresh_token": refresh_token,
    "token_type": "bearer",
    "user": user,  # ← Backend returns full user object
}
```

**Documentation Fix in API_DOCUMENTATION.md:**

Find and replace the login response section:

````markdown
## OLD (INCORRECT):

**Success Response (200):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900
}
```
````

## NEW (CORRECT):

**Success Response (200):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "role": "trainer",
    "first_name": "John",
    "last_name": "Doe",
    "is_active": true,
    "is_verified": false,
    "created_at": "2025-01-15T10:30:00Z"
  }
}
```

**Token Expiration:** Access token: 15 minutes (900 seconds), Refresh token: 7 days

````

---

### ❌ CRITICAL ISSUE #3: POST /auth/verify - Undocumented Endpoint

**Decision:** ✅ ADD TO DOCUMENTATION

**Backend Implementation (auth.py:43):**
```python
@router.post("/verify", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def verify_credentials(credentials: CredentialsSchema, db: Session = Depends(get_db)):
    """Verify user credentials and return user data for JWT token generation."""
    # Validates email/password, returns user if valid
````

**Documentation to Add:**

Insert after `/auth/login` section in API_DOCUMENTATION.md:

````markdown
#### POST /auth/verify

**Purpose:** Verify credentials and return user data (used for custom token generation)
**File:** `apps/api/src/app/api/v1/endpoints/auth.py:43`

**Request:**

```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```
````

**Success Response (200):**

```json
{
  "id": 1,
  "email": "user@example.com",
  "role": "trainer",
  "first_name": "John",
  "last_name": "Doe",
  "is_active": true,
  "is_verified": true,
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Error Responses:**

- `401 Unauthorized` - Invalid credentials
- `403 Forbidden` - Account not verified / inactive

**Frontend Callers:**

- `apps/dashboard/src/lib/auth.ts` - Custom token generation

````

---

### ❌ CRITICAL ISSUE #4: GET /trainer/clients/dashboard - Field Name Mismatch

**Decision:** ✅ UPDATE DOCUMENTATION (all fields to snake_case)

**Current Response (backend uses snake_case):**
```python
{
    "active_clients_count": 15,
    "active_programs_count": 8,
    "this_week_sessions": {"count": 23, "change": 5},
    "client_engagement": {"percentage": 78, "change": 3, "active_clients_last_7_days": 12}
}
````

**Documentation Fix:**

Find the `GET /trainer/clients/dashboard` section and replace:

````markdown
## OLD (INCORRECT - camelCase):

**Success Response (200):**

```json
{
  "activeClientsCount": 15,
  "activeProgramsCount": 8,
  "thisWeekSessions": {
    "count": 23,
    "change": 5
  },
  "clientEngagement": {
    "percentage": 78,
    "change": 3,
    "activeClientsLast7Days": 12
  }
}
```
````

## NEW (CORRECT - snake_case):

**Success Response (200):**

```json
{
  "active_clients_count": 15,
  "active_programs_count": 8,
  "this_week_sessions": {
    "count": 23,
    "change": 5
  },
  "client_engagement": {
    "percentage": 78,
    "change": 3,
    "active_clients_last_7_days": 12
  }
}
```

````

---

### ❌ CRITICAL ISSUE #5: GET /clients/me/* - Non-existent Endpoints

**Decision:** ✅ REMOVE from documentation (these endpoints don't exist)

**Endpoints to Remove:**
- `GET /clients/me/history`
- `GET /clients/me/achievements`
- `GET /clients/me/messages`

**Documentation Fix:**

Find the Client Endpoints section and remove these three endpoints from both the table and detailed sections.

Replace:
```markdown
### Client Endpoints (`/clients/me`)

| Method | Endpoint | Purpose | Auth Required |
|--------|----------|---------|---------------|\n| GET | `/clients/me/history` | Workout history | Yes (Client) |
| GET | `/clients/me/achievements` | Gamification data | Yes (Client) |
| GET | `/clients/me/messages` | Message threads | Yes (Client) |
````

With:

```markdown
### Client Endpoints (`/clients/me`)

| Method | Endpoint | Purpose | Auth Required |
|--------|----------|---------|---------------|\n| GET | `/clients/me/profile` | Get client profile | Yes (Client) |
| GET | `/clients/me/dashboard` | Client dashboard data | Yes (Client) |
| GET | `/clients/me/goals` | Client goals | Yes (Client) |
| GET | `/clients/me/workouts` | Client's assigned workouts | Yes (Client) |
```

---

### ❌ CRITICAL ISSUE #6: POST /subscriptions/\* - Path & Parameter Mismatches

**Decision:** ✅ UPDATE DOCUMENTATION

**Changes Needed:**

1. **POST `/create-checkout` → POST `/checkout`**
   - File location in docs: Lines 631-634 of API_DOCUMENTATION.md
   - Change endpoint path from `/create-checkout` to `/checkout`

2. **POST `/subscriptions/cancel` → POST `/subscriptions/{subscription_id}/cancel`**
   - Add `{subscription_id}` path parameter
   - Update request documentation to include path param instead of body

**Documentation Updates:**

```markdown
## OLD (INCORRECT):

| POST | `/subscriptions/create-checkout` | Create Stripe checkout | Yes |
| POST | `/subscriptions/cancel` | Cancel subscription | Yes |

## NEW (CORRECT):

| POST | `/subscriptions/checkout` | Create Stripe checkout | Yes |
| POST | `/subscriptions/{subscription_id}/cancel` | Cancel subscription | Yes |
```

And in the detailed sections:

```markdown
## OLD:

#### POST /subscriptions/create-checkout

## NEW:

#### POST /subscriptions/checkout

**Path Parameters:**

- `subscription_id` (string, required): Subscription identifier

**Request:** [no body needed]

## Also update:

#### POST /subscriptions/{subscription_id}/cancel

**Purpose:** Cancel user's subscription
```

---

### ❌ CRITICAL ISSUE #7: POST /auth/verify-email - Wrong HTTP Method

**Decision:** ✅ UPDATE DOCUMENTATION (change from POST to GET)

**Backend Implementation (auth.py:636):**

```python
@router.get("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(token: str, ...):
    """Verify user email address using token from verification email."""
```

**Documentation Fix:**

Find the auth endpoints table and update:

```markdown
## OLD:

| POST | `/auth/verify-email` | Verify email with token | No |

## NEW:

| GET | `/auth/verify-email` | Verify email with token | No |
```

And in detailed section:

````markdown
## OLD:

#### POST /auth/verify-email

**Request:**

```json
{ "token": "..." }
```
````

## NEW:

#### GET /auth/verify-email

**Query Parameters:**

- `token` (string, required): Verification token from email

````

---

### ❌ CRITICAL ISSUE #8: POST /auth/resend-verification - Undocumented

**Decision:** ✅ ADD TO DOCUMENTATION

**Backend Implementation (auth.py:719):**
```python
@router.post("/resend-verification", status_code=status.HTTP_200_OK)
async def resend_verification_email(credentials: CredentialsSchema, db: Session = Depends(get_db)):
    """Resend email verification link to user. Requires valid email and password."""
````

**Documentation to Add:**

Insert after `/auth/verify-email` section:

````markdown
#### POST /auth/resend-verification

**Purpose:** Resend email verification link to unverified user
**File:** `apps/api/src/app/api/v1/endpoints/auth.py:719`

**Request:**

```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```
````

**Success Response (200):**

```json
{
  "message": "Verification email sent successfully",
  "email": "user@example.com"
}
```

**Error Responses:**

- `400 Bad Request` - User already verified
- `401 Unauthorized` - Invalid credentials
- `404 Not Found` - User not found

```

---

## Quality Assurance

### Before Declaring Fix Complete:

For each fix, verify:

- [ ] **Documentation matches backend code exactly**
- [ ] **Request schema fields match code**
- [ ] **Response schema fields match code**
- [ ] **Field types are correct** (string, int, bool, datetime, object, array)
- [ ] **Authentication requirements accurate** (token, role, headers)
- [ ] **HTTP methods match** (GET, POST, PATCH, DELETE, etc.)
- [ ] **Path parameters documented** (if any)
- [ ] **Query parameters documented** (if any)
- [ ] **Status codes documented** (200, 201, 400, 401, 403, 404, 500)
- [ ] **Error responses documented** (all possible error codes)
- [ ] **Frontend caller code still works** (no breaking changes)

### Testing Checklist:

For backend implementations, verify:

- [ ] Endpoint exists and responds
- [ ] Request validation works correctly
- [ ] Response matches documented schema
- [ ] Authentication/authorization works
- [ ] Error cases return correct status codes
- [ ] Edge cases handled properly

### Documentation Checklist:

For documentation updates, verify:

- [ ] No typos or formatting errors
- [ ] Code examples are valid
- [ ] Field names match exactly
- [ ] All required fields documented
- [ ] All optional fields marked clearly
- [ ] Response examples valid JSON
- [ ] Consistent with other endpoint docs
- [ ] Frontend developers can implement from docs

---

## File References

### Files to Modify:

**For Documentation Fixes (Primary):**
- `API_DOCUMENTATION.md` - Main documentation file

**For Backend Implementation (Secondary):**
- `apps/api/src/app/api/v1/endpoints/auth.py` - Add logout endpoint
- `apps/api/src/app/models/` - Add TokenBlacklist model if needed
- `apps/api/src/app/core/security.py` - Update JWT validation

### After All Fixes:

1. Update `API_DOCUMENTATION.md` with all corrections
2. Generate new validation report if possible
3. Update backend code if endpoint implementation needed
4. Run tests to verify no breaking changes
5. Deploy updated documentation

---

## Summary

**Your Task:**

Fix all 47 issues in this priority order:

1. **CRITICAL (8 issues)** - Must fix to unblock frontend
   - Implement `/auth/logout`
   - Fix login response structure
   - Add `/auth/verify` documentation
   - Fix dashboard field names (snake_case)
   - Remove non-existent client endpoints
   - Fix subscription paths
   - Change verify-email to GET
   - Add resend-verification documentation

2. **MAJOR (15 issues)** - Should fix for features to work
   - Add missing workout fields
   - Add assignments_count
   - Add workout filters
   - Fix client profile schema
   - Fix chat conversation ID format
   - Add AI workout history endpoints
   - Add analytics WebSocket endpoints
   - Fix exercises router path
   - Add program relationship endpoints
   - Add health, admin, trainer, templates, assignments sections

3. **MINOR (24 issues)** - Nice to have
   - Add messaging documentation
   - Add newsletter, contact, push notification docs
   - Add other undocumented features

**Expected Outcome:**
- 100% of documented endpoints validated
- 0 breaking changes for frontend
- Comprehensive, accurate API documentation
- Backend implementation complete

---

**Start with CRITICAL issues immediately. These block frontend functionality.**
```
