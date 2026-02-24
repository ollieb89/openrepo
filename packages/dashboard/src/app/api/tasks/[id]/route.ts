import { NextRequest } from 'next/server';
import { getTask, getActiveProjectId } from '@/lib/openclaw';

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const { searchParams } = new URL(request.url);
    const projectId = searchParams.get('project') || await getActiveProjectId();
    const task = await getTask(projectId, params.id);
    if (!task) {
      return Response.json({ error: 'Task not found' }, { status: 404 });
    }
    return Response.json({ task });
  } catch (error) {
    console.error('Error loading task:', error);
    return Response.json({ error: 'Failed to load task' }, { status: 500 });
  }
}
