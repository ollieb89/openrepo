import { NextRequest, NextResponse } from 'next/server';
import { getTask, getActiveProjectId } from '@/lib/openclaw';
import { withAuth } from '@/lib/auth-middleware';

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
    return NextResponse.json({ task });
  } catch (error) {
    console.error('Error loading task:', error);
    return NextResponse.json({ error: 'Failed to load task' }, { status: 500 });
  }
}

export const GET = withAuth(handler);
