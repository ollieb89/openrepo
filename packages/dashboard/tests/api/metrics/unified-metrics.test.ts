/**
 * Tests for readPythonSnapshot() helper in /api/metrics/route.ts
 *
 * These tests verify:
 * - test_unified_response_has_python_and_meta: response includes python.* and meta.*
 * - test_graceful_degradation: ENOENT returns python: null, meta.snapshot_missing: true
 * - test_snapshot_age_computed: meta.snapshot_age_s computed from generated_at
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { readPythonSnapshot } from '@/app/api/metrics/route';

// ---------------------------------------------------------------------------
// Mock fs/promises so tests never touch the filesystem
// ---------------------------------------------------------------------------

vi.mock('fs/promises', () => ({
  readFile: vi.fn(),
}));

import { readFile } from 'fs/promises';
const mockReadFile = readFile as ReturnType<typeof vi.fn>;

beforeEach(() => {
  vi.resetAllMocks();
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('readPythonSnapshot', () => {
  it('test_unified_response_has_python_and_meta: returns python data and meta when file present', async () => {
    const now = Date.now() / 1000;
    const snapshotPayload = {
      python: {
        tasks: { total: 5, pending: 1, in_progress: 2, completed: 2, failed: 0 },
        pool: { active_containers: 2, max_concurrent: 3 },
        memory: { healthy: true, last_retrieval: null },
        autonomy: { active_contexts: 0, escalations_24h: 0 },
      },
      meta: {
        generated_at: now,
        source_state_mtime: now - 1,
      },
    };

    mockReadFile.mockResolvedValue(JSON.stringify(snapshotPayload));

    const result = await readPythonSnapshot('/fake/path/python-metrics.json');

    // python data must be present
    expect(result.python).not.toBeNull();
    expect(result.python).toMatchObject({
      tasks: { total: 5, pending: 1, in_progress: 2, completed: 2, failed: 0 },
      pool: { active_containers: 2, max_concurrent: 3 },
    });

    // meta must be present and snapshot_missing must be false
    expect(result.meta).toBeDefined();
    expect(result.meta.snapshot_missing).toBe(false);
    expect(result.meta.snapshot_age_s).toBeTypeOf('number');
  });

  it('test_graceful_degradation: returns python: null and snapshot_missing: true on ENOENT', async () => {
    const err = Object.assign(new Error('ENOENT: no such file'), { code: 'ENOENT' });
    mockReadFile.mockRejectedValue(err);

    const result = await readPythonSnapshot('/fake/path/python-metrics.json');

    expect(result.python).toBeNull();
    expect(result.meta.snapshot_missing).toBe(true);
    expect(result.meta.snapshot_age_s).toBeNull();
  });

  it('test_graceful_degradation: returns python: null on JSON parse error', async () => {
    mockReadFile.mockResolvedValue('this is not valid json {{{');

    const result = await readPythonSnapshot('/fake/path/python-metrics.json');

    expect(result.python).toBeNull();
    expect(result.meta.snapshot_missing).toBe(true);
    expect(result.meta.snapshot_age_s).toBeNull();
  });

  it('test_snapshot_age_computed: meta.snapshot_age_s is approximately 30 when generated_at is 30s ago', async () => {
    const generatedAt = Date.now() / 1000 - 30;
    const snapshotPayload = {
      python: {
        tasks: { total: 0, pending: 0, in_progress: 0, completed: 0, failed: 0 },
        pool: { active_containers: 0, max_concurrent: 3 },
        memory: { healthy: true, last_retrieval: null },
        autonomy: { active_contexts: 0, escalations_24h: 0 },
      },
      meta: {
        generated_at: generatedAt,
        source_state_mtime: generatedAt,
      },
    };

    mockReadFile.mockResolvedValue(JSON.stringify(snapshotPayload));

    const result = await readPythonSnapshot('/fake/path/python-metrics.json');

    expect(result.meta.snapshot_missing).toBe(false);
    expect(result.meta.snapshot_age_s).toBeTypeOf('number');
    // Allow ±2 seconds tolerance for test timing jitter
    expect(result.meta.snapshot_age_s).toBeGreaterThanOrEqual(28);
    expect(result.meta.snapshot_age_s).toBeLessThanOrEqual(32);
  });
});
