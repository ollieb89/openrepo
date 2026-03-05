import { NextRequest, NextResponse } from 'next/server';
import { getDb } from '@/lib/db';
import { withAuth } from '@/lib/auth-middleware';

async function handler(request: NextRequest): Promise<NextResponse> {
  try {
    const db = getDb();
    const agents = db.prepare('SELECT * FROM agents').all();
    return NextResponse.json({ agents });
  } catch (error) {
    console.error('Error loading agents:', error);
    return NextResponse.json({ error: 'Failed to load agents from index' }, { status: 500 });
  }
}

export const GET = withAuth(handler);
