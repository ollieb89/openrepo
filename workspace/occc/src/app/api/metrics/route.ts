import { NextRequest } from 'next/server';
import { getTaskState, getActiveProjectId, getProject } from '@/lib/openclaw';
import type { MetricsResponse } from '@/lib/types';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const projectId = searchParams.get('project') || await getActiveProjectId();

    const [tasks, project] = await Promise.all([
      getTaskState(projectId),
      getProject(projectId),
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

    const response: MetricsResponse = {
      completionDurations: durationEntries,
      lifecycle: { pending, active, completed, failed },
      poolUtilization,
      poolMax,
      poolActive,
      projectId,
    };

    return Response.json(response);
  } catch (error) {
    console.error('Error loading metrics:', error);
    return Response.json({ error: 'Failed to load metrics' }, { status: 500 });
  }
}
