import { NextRequest } from 'next/server';
import { getTaskState, getActiveProjectId } from '@/lib/openclaw';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const projectId = searchParams.get('project') || await getActiveProjectId();
    const state = searchParams.get('state') ?? undefined;
    const tasks = await getTaskState(projectId, { state });
    return Response.json({ tasks, projectId });
  } catch (error) {
    console.error('Error loading tasks:', error);
    return Response.json({ error: 'Failed to load tasks' }, { status: 500 });
  }
}
