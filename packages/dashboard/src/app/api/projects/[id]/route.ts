import { NextRequest, NextResponse } from 'next/server';
import { getProject } from '@/lib/openclaw';
import { withAuth } from '@/lib/auth-middleware';

async function handler(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const project = await getProject(id);
    if (!project) {
      return NextResponse.json({ error: 'Project not found' }, { status: 404 });
    }
    return NextResponse.json({ project });
  } catch (error) {
    console.error('Error loading project:', error);
    return NextResponse.json({ error: 'Failed to load project' }, { status: 500 });
  }
}

export const GET = withAuth(handler);
