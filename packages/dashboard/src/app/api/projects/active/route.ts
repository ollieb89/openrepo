import { NextRequest, NextResponse } from 'next/server';
import { getActiveProjectId, getProject } from '@/lib/openclaw';
import { withAuth } from '@/lib/auth-middleware';

async function handler(request: NextRequest): Promise<NextResponse> {
  try {
    const id = await getActiveProjectId();
    const project = await getProject(id);
    return NextResponse.json({ id, project });
  } catch (error) {
    console.error('Error loading active project:', error);
    return NextResponse.json({ error: 'Failed to load active project' }, { status: 500 });
  }
}

export const GET = withAuth(handler);
