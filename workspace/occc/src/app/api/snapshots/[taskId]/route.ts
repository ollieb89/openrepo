import { NextRequest } from 'next/server';
import { getSnapshot, getActiveProjectId } from '@/lib/openclaw';

export async function GET(
  request: NextRequest,
  { params }: { params: { taskId: string } }
) {
  try {
    const { searchParams } = new URL(request.url);
    const projectId = searchParams.get('project') || await getActiveProjectId();
    const diff = await getSnapshot(projectId, params.taskId);
    if (!diff) {
      return Response.json({ error: 'Snapshot not found' }, { status: 404 });
    }
    return Response.json({ diff });
  } catch (error) {
    console.error('Error loading snapshot:', error);
    return Response.json({ error: 'Failed to load snapshot' }, { status: 500 });
  }
}
