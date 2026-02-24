import { NextRequest, NextResponse } from 'next/server';
import { loadDecisions, saveDecisions, loadSyncRecords } from '@/lib/sync/storage';
import { extractDecisionsFromThread } from '@/lib/sync/summarizer';
import { listConnectorStates } from '@/lib/connectors/store';
import { ThreadRecord } from '@/lib/types/decisions';

export async function POST(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  const { id } = params;
  const { hint } = await req.json();

  try {
    const connectors = await listConnectorStates();
    let originalDecision: any = null;
    let connectorId: string = '';

    for (const connector of connectors) {
      const decisions = await loadDecisions(connector.id);
      originalDecision = decisions.find(d => d.id === id);
      if (originalDecision) {
        connectorId = connector.id;
        break;
      }
    }

    if (!originalDecision) {
      return NextResponse.json({ error: 'Decision not found' }, { status: 404 });
    }

    // Load original thread
    const records = await loadSyncRecords(connectorId, originalDecision.sourceId) as ThreadRecord[];
    const thread = records.find(r => r.id === originalDecision.threadId);

    if (!thread) {
      return NextResponse.json({ error: 'Original thread record not found' }, { status: 404 });
    }

    // Re-summarize with hint
    const newDecisions = await extractDecisionsFromThread(
      thread, 
      connectorId, 
      originalDecision.sourceId, 
      hint
    );

    if (newDecisions.length === 0) {
      return NextResponse.json({ error: 'Failed to generate new summary from thread' }, { status: 500 });
    }

    // For now, we take the first outcome if multiple were generated, 
    // or we could replace all related ones. 
    // Usually, a hint targets a specific outcome.
    // We'll preserve the ID of the original one to replace it in the UI.
    const updatedDecision = {
      ...newDecisions[0],
      id: originalDecision.id, // Preserve ID for UI consistency
      updatedAt: new Date().toISOString(),
    };

    await saveDecisions(connectorId, [updatedDecision]);

    return NextResponse.json(updatedDecision);
  } catch (error) {
    console.error(`Failed to re-summarize decision ${id}:`, error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
