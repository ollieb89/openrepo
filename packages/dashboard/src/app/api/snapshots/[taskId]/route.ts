import { NextRequest, NextResponse } from 'next/server';
import { getSnapshot, getActiveProjectId } from '@/lib/openclaw';
import { withAuth } from '@/lib/auth-middleware';

async function handler(
  request: NextRequest,
  { params }: { params: Promise<{ taskId: string }> }
) {
  try {
    const { taskId } = await params;
    const { searchParams } = new URL(request.url);
    const projectId = searchParams.get('project') || await getActiveProjectId();
    const diff = await getSnapshot(projectId, taskId);
    if (!diff) {
      return NextResponse.json({ error: 'Snapshot not found' }, { status: 404 });
    }
    return NextResponse.json({ diff });
  } catch (error) {
    console.error('Error loading snapshot:', error);
    return NextResponse.json({ error: 'Failed to load snapshot' }, { status: 500 });
  }
}

export const GET = withAuth(handler);
