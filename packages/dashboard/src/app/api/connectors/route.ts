import { NextRequest, NextResponse } from 'next/server';
import { getConnectorState, listConnectorStates } from '@/lib/connectors/store';
import { listCheckpointsForConnector } from '@/lib/sync/checkpoints';
import { listConnectorProgress } from '@/lib/sync/engine';
import { withAuth } from '@/lib/auth-middleware';

async function handler(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const id = searchParams.get('id');

    if (id) {
      const connector = await getConnectorState(id);
      if (!connector) {
        return NextResponse.json({ error: 'Connector not found' }, { status: 404 });
      }

      const [checkpoints, progress] = await Promise.all([
        listCheckpointsForConnector(id),
        listConnectorProgress(id),
      ]);

      return NextResponse.json({ connector, checkpoints, progress });
    }

    const connectors = await listConnectorStates();
    return NextResponse.json({ connectors });
  } catch (error) {
    console.error('Error loading connectors:', error);
    return NextResponse.json({ error: 'Failed to load connectors' }, { status: 500 });
  }
}

export const GET = withAuth(handler);
