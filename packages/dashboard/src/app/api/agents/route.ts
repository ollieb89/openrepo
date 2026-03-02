import { NextRequest, NextResponse } from 'next/server';
import { listAgents } from '@/lib/openclaw';
import { withAuth } from '@/lib/auth-middleware';

async function handler(request: NextRequest): Promise<NextResponse> {
  try {
    const agents = await listAgents();
    return NextResponse.json({ agents });
  } catch (error) {
    console.error('Error loading agents:', error);
    return NextResponse.json({ error: 'Failed to load agents' }, { status: 500 });
  }
}

export const GET = withAuth(handler);
