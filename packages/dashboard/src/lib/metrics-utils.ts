import { readFile } from 'fs/promises';

export interface PythonSnapshotResult {
  python: Record<string, unknown> | null;
  meta: {
    snapshot_missing: boolean;
    snapshot_age_s: number | null;
    snapshot_error: string | null;
  };
}

/**
 * Read python-metrics.json from disk and return a normalized result.
 *
 * Returns:
 * - { python: data, meta: { snapshot_missing: false, snapshot_age_s: N } } on success
 * - { python: null, meta: { snapshot_missing: true, snapshot_age_s: null } } on any error
 *
 * All errors (ENOENT, JSON parse, etc.) are swallowed — the dashboard still
 * renders without Python-side metrics.
 */
export async function readPythonSnapshot(snapshotPath: string): Promise<PythonSnapshotResult> {
  try {
    const raw = await readFile(snapshotPath, 'utf-8');
    const data = JSON.parse(raw) as { python: Record<string, unknown>; meta: { generated_at: number } };

    const generatedAt = data?.meta?.generated_at;
    const snapshotAgeS =
      typeof generatedAt === 'number'
        ? Math.round((Date.now() / 1000 - generatedAt) * 10) / 10
        : null;

    return {
      python: data.python ?? null,
      meta: {
        snapshot_missing: false,
        snapshot_age_s: snapshotAgeS,
        snapshot_error: null,
      },
    };
  } catch (err) {
    return {
      python: null,
      meta: {
        snapshot_missing: true,
        snapshot_age_s: null,
        snapshot_error: err instanceof Error ? err.message : 'unknown error',
      },
    };
  }
}
