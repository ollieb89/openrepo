import { NextResponse } from 'next/server';
import { getPendingSuggestions } from '@/lib/sync/vector-store';

export async function GET() {
  try {
    const suggestions = getPendingSuggestions();
    return NextResponse.json(suggestions);
  } catch (error) {
    console.error('[API] Failed to fetch suggestions:', error);
    return NextResponse.json({ error: 'Failed to fetch suggestions' }, { status: 500 });
  }
}
