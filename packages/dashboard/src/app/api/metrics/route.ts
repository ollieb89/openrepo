import { NextRequest, NextResponse } from 'next/server';
import { getTaskState, getActiveProjectId, getProject } from '@/lib/openclaw';
import { withAuth } from '@/lib/auth-middleware';
import type { MetricsResponse } from '@/lib/types';
import path from 'path';
import os from 'os';
import { readFile } from 'fs/promises';
import { aggregateTodayUsage } from './usage-aggregator';
import { readPythonSnapshot } from '@/lib/metrics-utils';

const OPENCLAW_ROOT = process.env.OPENCLAW_ROOT || path.join(os.homedir(), '.openclaw');

async function checkMemoryHealth(): Promise<{ healthy: boolean; latency?: number }> {
  try {
    let baseUrl = 'http://localhost:18791';
    
    try {
      const { readFile } = await import('fs/promises');
      const raw = await readFile(path.join(OPENCLAW_ROOT, 'openclaw.json'), 'utf-8');
      const config = JSON.parse(raw);
      baseUrl = config.memory?.memu_api_url || baseUrl;
    } catch {
      // Use default
    }

    const start = Date.now();
    const res = await fetch(`${baseUrl}/health`, { signal: AbortSignal.timeout(2000) });
    const latency = Date.now() - start;
    
    return { healthy: res.ok, latency };
  } catch {
    return { healthy: false };
  }
}

async function handler(request: NextRequest): Promise<NextResponse> {
  try {
    const { searchParams } = new URL(request.url);
    const projectId = searchParams.get('project') || await getActiveProjectId();

    const snapshotPath = path.join(OPENCLAW_ROOT, 'workspace', '.openclaw', projectId, 'python-metrics.json');

    const [[tasks, project], memoryHealth, usageResult, pythonSnapshot] = await Promise.all([
      Promise.all([
        getTaskState(projectId),
        getProject(projectId),
      ]),
      checkMemoryHealth(),
      (async () => {
        const usagePath = path.join(OPENCLAW_ROOT, 'workspace', '.openclaw', projectId, 'usage.ndjson');
        try {
          const raw = await readFile(usagePath, 'utf-8');
          const agg = aggregateTodayUsage(raw.split('\n'));
          return { present: true, tokens: agg.tokens, costUsd: agg.costUsd };
        } catch (err: unknown) {
          if ((err as NodeJS.ErrnoException).code !== 'ENOENT') {
            console.error('[metrics] Failed to read usage.ndjson:', err);
          }
          return { present: false, tokens: 0, costUsd: 0 };
        }
      })(),
      readPythonSnapshot(snapshotPath),
    ]);

    const poolMax = project?.l3_overrides?.max_concurrent ?? 3;

    // Compute completion durations from tasks with both timestamps
    const durationEntries = tasks
      .filter(t =>
        typeof (t.metadata.completed_at as number) === 'number' &&
        typeof (t.metadata.container_started_at as number) === 'number'
      )
      .map(t => ({
        id: t.id,
        completedAt: t.metadata.completed_at as number,
        durationS: Math.round(
          ((t.metadata.completed_at as number) - (t.metadata.container_started_at as number)) * 10
        ) / 10,
      }))
      .sort((a, b) => a.completedAt - b.completedAt)
      .slice(-15)
      .map(({ id, durationS }) => ({ id, durationS }));

    // Compute lifecycle counts by status
    let pending = 0;
    let active = 0;
    let completed = 0;
    let failed = 0;

    for (const task of tasks) {
      switch (task.status) {
        case 'pending':
          pending++;
          break;
        case 'in_progress':
        case 'starting':
        case 'testing':
          active++;
          break;
        case 'completed':
          completed++;
          break;
        case 'failed':
        case 'rejected':
          failed++;
          break;
      }
    }

    const poolActive = active;
    const poolUtilization = Math.min(100, Math.max(0, Math.round((poolActive / poolMax) * 100)));

    // Compute autonomy aggregates
    const tasksWithConfidence = (tasks as any[]).filter(t => typeof t.autonomy?.confidence_score === 'number');
    const avgConfidence = tasksWithConfidence.length > 0
      ? tasksWithConfidence.reduce((acc, t) => acc + (t as any).autonomy.confidence_score, 0) / tasksWithConfidence.length
      : 1.0;

    const response: MetricsResponse & { python: Record<string, unknown> | null; meta: { snapshot_missing: boolean; snapshot_age_s: number | null; snapshot_error: string | null } } = {
      completionDurations: durationEntries,
      lifecycle: { pending, active, completed, failed },
      poolUtilization,
      poolMax,
      poolActive,
      projectId,
      autonomy: {
        avgConfidence: Math.round(avgConfidence * 100) / 100,
        activeContexts: active,
      },
      memory: {
        healthy: memoryHealth.healthy,
        latencyMs: memoryHealth.latency,
      },
      todayTokens: usageResult.tokens,
      todayCostUsd: usageResult.costUsd,
      usageLogPresent: usageResult.present,
      python: pythonSnapshot.python,
      meta: pythonSnapshot.meta,
    };

    return NextResponse.json(response);
  } catch (error) {
    console.error('Error loading metrics:', error);
    return NextResponse.json({ error: 'Failed to load metrics' }, { status: 500 });
  }
}

export const GET = withAuth(handler);
