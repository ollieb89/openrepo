import { NextRequest, NextResponse } from 'next/server';
import { updateLinkSuggestionStatus } from '@/lib/sync/vector-store';

export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const { id } = params;
    const { action } = await request.json();

    if (!['accept', 'reject'].includes(action)) {
      return NextResponse.json({ error: 'Invalid action' }, { status: 400 });
    }

    const status = action === 'accept' ? 'accepted' : 'rejected';
    const success = updateLinkSuggestionStatus(id, status);

    if (!success) {
      return NextResponse.json({ error: 'Suggestion not found' }, { status: 404 });
    }

    return NextResponse.json({ success: true, status });
  } catch (error) {
    console.error('[API] Failed to update suggestion status:', error);
    return NextResponse.json({ error: 'Failed to update suggestion status' }, { status: 500 });
  }
}
