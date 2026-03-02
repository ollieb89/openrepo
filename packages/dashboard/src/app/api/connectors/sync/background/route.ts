import { NextResponse } from 'next/server';
import { runBackgroundSync } from '@/lib/sync/scheduler';
import { withAuth } from '@/lib/auth-middleware';

async function handler() {
  try {
    const result = await runBackgroundSync();
    return NextResponse.json(result);
  } catch (error) {
    console.error('[API] Background sync error:', error);
    return NextResponse.json(
      { error: 'Internal Server Error' },
      { status: 500 }
    );
  }
}

export const POST = withAuth(handler);
