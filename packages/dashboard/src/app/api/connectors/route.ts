import { NextRequest } from 'next/server';
import { getConnectorState, listConnectorStates } from '@/lib/connectors/store';
import { listCheckpointsForConnector } from '@/lib/sync/checkpoints';
import { listConnectorProgress } from '@/lib/sync/engine';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const id = searchParams.get('id');

    if (id) {
      const connector = await getConnectorState(id);
      if (!connector) {
        return Response.json({ error: 'Connector not found' }, { status: 404 });
      }

      const [checkpoints, progress] = await Promise.all([
        listCheckpointsForConnector(id),
        listConnectorProgress(id),
      ]);

      return Response.json({ connector, checkpoints, progress });
    }

    const connectors = await listConnectorStates();
    return Response.json({ connectors });
  } catch (error) {
    console.error('Error loading connectors:', error);
    return Response.json({ error: 'Failed to load connectors' }, { status: 500 });
  }
}
