import { NextResponse } from 'next/server';
import { getPendingSuggestions } from '@/lib/sync/vector-store';
import { withAuth } from '@/lib/auth-middleware';

async function handler() {
  try {
    const suggestions = getPendingSuggestions();
    return NextResponse.json(suggestions);
  } catch (error) {
    console.error('[API] Failed to fetch suggestions:', error);
    return NextResponse.json({ error: 'Failed to fetch suggestions' }, { status: 500 });
  }
}

export const GET = withAuth(handler);
