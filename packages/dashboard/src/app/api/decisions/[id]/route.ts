import { NextRequest, NextResponse } from 'next/server';
import { loadDecisions, saveDecisions } from '@/lib/sync/storage';
import { listConnectorStates } from '@/lib/connectors/store';
import { withAuth } from '@/lib/auth-middleware';

async function handler(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  try {
    const connectors = await listConnectorStates();
    let found = false;

    for (const connector of connectors) {
      const decisions = await loadDecisions(connector.id);
      const decisionIndex = decisions.findIndex(d => d.id === id);

      if (decisionIndex !== -1) {
        decisions[decisionIndex].isHidden = true;
        decisions[decisionIndex].updatedAt = new Date().toISOString();
        await saveDecisions(connector.id, [decisions[decisionIndex]]);
        found = true;
        break;
      }
    }

    if (!found) {
      return NextResponse.json({ error: 'Decision not found' }, { status: 404 });
    }

    return NextResponse.json({ ok: true });
  } catch (error) {
    console.error(`Failed to hide decision ${id}:`, error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

export const DELETE = withAuth(handler);
