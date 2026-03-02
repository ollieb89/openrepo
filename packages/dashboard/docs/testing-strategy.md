# Testing Strategy: OpenClaw Dashboard Filesystem Operations

## Executive Summary

**Critical Issues Identified:**
1. **EACCES (Permission Denied)**: Attempting to create `/home/ollie/.openclaw/workspace/.openclaw` without proper permissions
2. **ENOENT (No Such File)**: Missing directory `/home/ollie/.openclaw/projects` causes API failures
3. **Missing Directory Validation**: No graceful handling of missing parent directories before operations

**Impact**: High - Complete API failure causing 500 errors in production

**Root Cause**: Functions assume filesystem structure exists; no defensive programming for missing directories

---

## Risk Assessment

| Risk Area | Impact | Probability | Priority | Strategy |
|-----------|--------|-------------|----------|----------|
| Missing directories | Critical | High | 1 | Validate existence before all I/O ops |
| Permission errors | Critical | Medium | 1 | Check permissions + graceful fallback |
| Concurrent directory creation | High | Medium | 2 | Use fs.mkdir recursive with error handling |
| Hardcoded paths | High | High | 2 | Inject paths for testability |
| Missing environment vars | High | Medium | 3 | Validate env + provide defaults |
| Race conditions in mkdir | Medium | Low | 4 | Idempotent directory creation |

---

## Test Coverage Strategy

### Unit Tests (Target: 90% coverage)

**File: `tests/lib/openclaw-filesystem.test.ts`**

Focus areas:
- Directory existence validation
- Permission error handling
- Missing parent directory scenarios
- Environment variable fallbacks
- Concurrent operation safety

### Integration Tests (Target: 85% coverage)

**File: `tests/integration/api-filesystem.test.ts`**

Focus areas:
- API routes with missing directories
- API routes with permission errors
- Directory creation race conditions
- Multi-user concurrent access

### E2E Tests (Critical paths only)

**File: `tests/e2e/dashboard-initialization.spec.ts`**

Focus areas:
- Fresh installation (no directories exist)
- Degraded filesystem (partial structure)
- Permission-restricted environments

---

## Edge Cases Identified

### Directory Operations

❌ **Current Problems:**
```typescript
// openclaw.ts:17 - No directory existence check
const entries = await fs.readdir(projectsDir, { withFileTypes: true });

// openclaw.ts:158 - Creates directory but parent might not exist
await fs.mkdir(logDir, { recursive: true });

// vector-store.ts:16 - Synchronous check with async operations
if (!fs.existsSync(dbDir)) {
  fs.mkdirSync(dbDir, { recursive: true });
}
```

✅ **Edge Cases to Test:**

1. **Missing Root Directory**
   - `/home/ollie/.openclaw` doesn't exist
   - Expected: Create with proper permissions
   - Current: ENOENT error

2. **Missing Intermediate Directories**
   - `/home/ollie/.openclaw` exists but `/workspace` doesn't
   - Expected: Create missing intermediates
   - Current: Depends on recursive flag

3. **Permission Denied on Root**
   - User doesn't have write access to parent directory
   - Expected: Graceful error with actionable message
   - Current: EACCES crashes server

4. **Partial Directory Structure**
   - Some project directories exist, others don't
   - Expected: Continue processing valid directories
   - Current: May fail iteration

5. **Concurrent Directory Creation**
   - Multiple API calls try creating same directory
   - Expected: One succeeds, others are idempotent
   - Current: Possible race condition

6. **Symbolic Link Handling**
   - `OPENCLAW_ROOT` points to symlink
   - Expected: Resolve and follow
   - Current: Unknown behavior

7. **Read-Only Filesystem**
   - Mounted filesystem is read-only
   - Expected: Detect and provide clear error
   - Current: EACCES with unclear message

8. **Disk Space Exhaustion**
   - No space left on device
   - Expected: Graceful degradation
   - Current: Unknown

### Environment Variable Issues

❌ **Current Problems:**
```typescript
// openclaw.ts:8 - Falls back to hardcoded path
const OPENCLAW_ROOT = process.env.OPENCLAW_ROOT || '/home/ollie/.openclaw';
```

✅ **Edge Cases to Test:**

1. **Missing OPENCLAW_ROOT**
   - Env var not set
   - Expected: Use sensible default
   - Current: Hardcoded `/home/ollie`

2. **Invalid OPENCLAW_ROOT Path**
   - Env var = `/nonexistent/path`
   - Expected: Validate and error early
   - Current: Fails at first I/O

3. **Relative Path in Env Var**
   - `OPENCLAW_ROOT=./local`
   - Expected: Resolve to absolute
   - Current: Inconsistent behavior

4. **Environment Mismatch**
   - Different users have different `OPENCLAW_ROOT`
   - Expected: Isolated workspaces
   - Current: Assumes single-user

### File Operation Edge Cases

1. **Malformed JSON in project.json**
   - Syntax errors, incomplete JSON
   - Current: Caught with try/catch (good)
   - Test: Verify graceful handling

2. **Empty Files**
   - Zero-byte project.json
   - Expected: Skip with warning
   - Current: JSON parse fails (caught)

3. **Large Files**
   - Multi-megabyte configuration files
   - Expected: Handle or limit size
   - Current: No size validation

4. **File Locks**
   - Another process has file locked
   - Expected: Retry or clear error
   - Current: EBUSY or EAGAIN

5. **Encoding Issues**
   - Non-UTF-8 files
   - Expected: Detect and handle
   - Current: Unknown

---

## Implementation Plan

### Phase 1: Defensive Filesystem Utils (Priority 1)

**Create: `src/lib/filesystem-utils.ts`**

```typescript
/**
 * Defensive filesystem operations with comprehensive error handling
 */

export class FilesystemError extends Error {
  constructor(
    message: string,
    public code: string,
    public path: string,
    public originalError?: Error
  ) {
    super(message);
    this.name = 'FilesystemError';
  }
}

/**
 * Ensures directory exists with proper error handling
 * @returns true if directory exists/created, false if operation failed
 */
export async function ensureDirectory(
  dirPath: string,
  options?: { permissions?: number }
): Promise<{ success: boolean; error?: FilesystemError }> {
  // Implementation with all edge cases handled
}

/**
 * Safely reads directory with existence check
 */
export async function safeReadDir(dirPath: string): Promise<
  { success: true; entries: Dirent[] } | 
  { success: false; error: FilesystemError }
> {
  // Implementation
}

/**
 * Validates OPENCLAW_ROOT and creates structure if missing
 */
export async function initializeWorkspace(
  root: string
): Promise<{ success: boolean; error?: FilesystemError }> {
  // Implementation
}
```

### Phase 2: Refactor openclaw.ts (Priority 1)

**Key Changes:**
1. Add directory existence checks before all operations
2. Use defensive filesystem utils
3. Return proper error types instead of throwing
4. Add initialization function for workspace setup

### Phase 3: Comprehensive Test Suite (Priority 1)

**Create test files:**
1. `tests/lib/filesystem-utils.test.ts` - 90%+ coverage
2. `tests/lib/openclaw.test.ts` - Refactored with mocks
3. `tests/integration/api-routes.test.ts` - API-level tests
4. `tests/e2e/initialization.spec.ts` - End-to-end flows

### Phase 4: API Route Hardening (Priority 2)

**Update API routes:**
- Add initialization check middleware
- Return 503 Service Unavailable if workspace not initialized
- Provide actionable error messages with setup instructions

---

## Test Implementation Examples

### Unit Test: Directory Validation

```typescript
// tests/lib/filesystem-utils.test.ts

describe('ensureDirectory', () => {
  let tempDir: string;

  beforeEach(async () => {
    tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'openclaw-test-'));
  });

  afterEach(async () => {
    await fs.rm(tempDir, { recursive: true, force: true });
  });

  it('should create directory if it does not exist', async () => {
    const testPath = path.join(tempDir, 'new-dir');
    const result = await ensureDirectory(testPath);
    
    expect(result.success).toBe(true);
    expect(await fs.stat(testPath).then(() => true).catch(() => false)).toBe(true);
  });

  it('should create nested directories recursively', async () => {
    const testPath = path.join(tempDir, 'a', 'b', 'c');
    const result = await ensureDirectory(testPath);
    
    expect(result.success).toBe(true);
    expect(await fs.stat(testPath).then(() => true).catch(() => false)).toBe(true);
  });

  it('should return success if directory already exists', async () => {
    const testPath = path.join(tempDir, 'existing');
    await fs.mkdir(testPath);
    
    const result = await ensureDirectory(testPath);
    expect(result.success).toBe(true);
  });

  it('should handle permission denied gracefully', async () => {
    const readOnlyDir = path.join(tempDir, 'readonly');
    await fs.mkdir(readOnlyDir);
    await fs.chmod(readOnlyDir, 0o444); // Read-only
    
    const testPath = path.join(readOnlyDir, 'subdir');
    const result = await ensureDirectory(testPath);
    
    expect(result.success).toBe(false);
    expect(result.error?.code).toBe('EACCES');
    expect(result.error?.message).toContain('Permission denied');
  });

  it('should be idempotent when called concurrently', async () => {
    const testPath = path.join(tempDir, 'concurrent');
    
    const results = await Promise.all([
      ensureDirectory(testPath),
      ensureDirectory(testPath),
      ensureDirectory(testPath),
      ensureDirectory(testPath),
      ensureDirectory(testPath),
    ]);
    
    expect(results.every(r => r.success)).toBe(true);
    expect(await fs.stat(testPath).then(() => true).catch(() => false)).toBe(true);
  });

  it('should handle paths with special characters', async () => {
    const testPath = path.join(tempDir, 'special chars @#$%');
    const result = await ensureDirectory(testPath);
    
    expect(result.success).toBe(true);
  });

  it('should reject paths outside allowed root', async () => {
    const testPath = '/tmp/../../../etc/evil';
    const result = await ensureDirectory(testPath);
    
    expect(result.success).toBe(false);
    expect(result.error?.message).toContain('Invalid path');
  });
});
```

### Integration Test: API Routes

```typescript
// tests/integration/api-routes.test.ts

describe('GET /api/projects', () => {
  it('should return 503 when workspace not initialized', async () => {
    // Mock missing OPENCLAW_ROOT directory
    process.env.OPENCLAW_ROOT = '/nonexistent-test-path';
    
    const response = await fetch('http://localhost:3000/api/projects');
    
    expect(response.status).toBe(503);
    const data = await response.json();
    expect(data.error).toContain('Workspace not initialized');
    expect(data.hint).toContain('Run initialization script');
  });

  it('should return empty array when projects directory is empty', async () => {
    // Setup: Create empty projects directory
    const testRoot = await createTestWorkspace();
    process.env.OPENCLAW_ROOT = testRoot;
    
    const response = await fetch('http://localhost:3000/api/projects');
    
    expect(response.status).toBe(200);
    const data = await response.json();
    expect(data.projects).toEqual([]);
  });

  it('should skip projects with invalid JSON', async () => {
    const testRoot = await createTestWorkspace();
    await fs.writeFile(
      path.join(testRoot, 'projects', 'broken', 'project.json'),
      'invalid json {'
    );
    
    const response = await fetch('http://localhost:3000/api/projects');
    
    expect(response.status).toBe(200);
    // Should not crash, just skip invalid project
  });
});
```

---

## Success Criteria

### Must Have (Blocking)
- [ ] All filesystem operations have existence checks
- [ ] Permission errors return 503 with actionable messages
- [ ] 90%+ unit test coverage on filesystem utils
- [ ] Zero crashes on missing directories
- [ ] Concurrent operations are safe (no race conditions)

### Should Have (Important)
- [ ] Initialization script for workspace setup
- [ ] Health check endpoint for filesystem status
- [ ] 85%+ integration test coverage
- [ ] Comprehensive error logging

### Nice to Have (Future)
- [ ] Automatic workspace repair
- [ ] File system monitoring/health checks
- [ ] Performance benchmarks for I/O operations
- [ ] Disk space usage warnings

---

## Monitoring & Observability

### Error Tracking
```typescript
// Add to all filesystem operations
logger.error('Filesystem operation failed', {
  operation: 'mkdir',
  path: dirPath,
  error: err.code,
  stack: err.stack,
  user: process.env.USER,
  permissions: await getPermissions(dirPath)
});
```

### Health Check Endpoint
```typescript
// GET /api/health/filesystem
{
  "workspace_root": "/home/ollie/.openclaw",
  "exists": true,
  "writable": true,
  "directories": {
    "projects": { "exists": true, "count": 5 },
    "workspace": { "exists": true, "writable": true },
    "agents": { "exists": true, "count": 3 }
  },
  "disk_space": {
    "total": "500GB",
    "available": "200GB",
    "used_percent": 60
  }
}
```

---

**Next Steps:**
1. Create filesystem-utils.ts with defensive operations
2. Write comprehensive unit tests
3. Refactor openclaw.ts to use defensive utils
4. Add API route error handling
5. Create initialization script
6. Deploy with monitoring
