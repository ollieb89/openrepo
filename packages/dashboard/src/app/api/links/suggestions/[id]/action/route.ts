import { NextRequest, NextResponse } from 'next/server';
import { updateLinkSuggestionStatus } from '@/lib/sync/vector-store';
import { addEdge } from '@/lib/sync/graph';
import { withAuth } from '@/lib/auth-middleware';

async function handler(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const { action } = await request.json();

    if (!['accept', 'reject'].includes(action)) {
      return NextResponse.json({ error: 'Invalid action' }, { status: 400 });
    }

    const status = action === 'accept' ? 'accepted' : 'rejected';
    const suggestion = updateLinkSuggestionStatus(id, status);

    if (!suggestion) {
      return NextResponse.json({ error: 'Suggestion not found' }, { status: 404 });
    }

    if (status === 'accepted') {
      addEdge(suggestion.decision_id, suggestion.issue_id, 'relates_to');
    }

    return NextResponse.json({ success: true, status });
  } catch (error) {
    console.error('[API] Failed to update suggestion status:', error);
    return NextResponse.json({ error: 'Failed to update suggestion status' }, { status: 500 });
  }
}

export const POST = withAuth(handler);
