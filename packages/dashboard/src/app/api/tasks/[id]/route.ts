import { NextRequest, NextResponse } from 'next/server';
import { getTask, getActiveProjectId } from '@/lib/openclaw';
import { withAuth } from '@/lib/auth-middleware';
import type { Task } from '@/lib/types';

function buildJourneyFromTask(task: Task) {
  const meta = task.metadata as Record<string, unknown>;
  const branch =
    typeof meta?.l3_branch === 'string' ? meta.l3_branch : null;
  const assignedAt =
    typeof meta?.started_at === 'number' ? (meta.started_at as number) : null;
  const completedAt =
    typeof meta?.completed_at === 'number'
      ? (meta.completed_at as number)
      : task.status === 'completed' || task.status === 'failed' || task.status === 'rejected'
        ? task.updated_at
        : null;
  return {
    dispatched_at: task.created_at ?? null,
    assigned_at: assignedAt,
    branch,
    completed_at: completedAt,
    stage: task.status,
  };
}

async function handler(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const { searchParams } = new URL(request.url);
    const projectId = searchParams.get('project') || await getActiveProjectId();
    const task = await getTask(projectId, id);
    if (!task) {
      return NextResponse.json({ error: 'Task not found' }, { status: 404 });
    }
    return NextResponse.json({ task, journey: buildJourneyFromTask(task) });
  } catch (error) {
    console.error('Error loading task:', error);
    return NextResponse.json({ error: 'Failed to load task' }, { status: 500 });
  }
}

export const GET = withAuth(handler);
