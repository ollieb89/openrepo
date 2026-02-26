import { NextResponse } from 'next/server';
import { runBackgroundSync } from '@/lib/sync/scheduler';

export async function POST() {
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
