import { NextRequest, NextResponse } from 'next/server';
import { listProjects, getActiveProjectId } from '@/lib/openclaw';
import { withAuth } from '@/lib/auth-middleware';

async function handler(request: NextRequest): Promise<NextResponse> {
  try {
    const [projects, activeId] = await Promise.all([
      listProjects(),
      getActiveProjectId(),
    ]);
    return NextResponse.json({ projects, activeId });
  } catch (error) {
    console.error('Error loading projects:', error);
    return NextResponse.json(
      { error: 'Failed to load projects' },
      { status: 500 }
    );
  }
}

export const GET = withAuth(handler);
