import { listCheckpointsForConnector } from '@/lib/sync/checkpoints';
import { listConnectorStates } from '@/lib/connectors/store';
import { listConnectorProgress } from '@/lib/sync/engine';
import { buildConnectorHealthPayload } from '@/lib/connectors/health-payload';

export async function GET() {
  try {
    const connectors = await listConnectorStates();

    const [progressByConnectorEntries, checkpointsByConnectorEntries] = await Promise.all([
      Promise.all(
        connectors.map(async connector => {
          const progress = await listConnectorProgress(connector.id);
          return [connector.id, progress] as const;
        })
      ),
      Promise.all(
        connectors.map(async connector => {
          const checkpoints = await listCheckpointsForConnector(connector.id);
          return [connector.id, checkpoints] as const;
        })
      ),
    ]);

    const progressByConnector = Object.fromEntries(progressByConnectorEntries);
    const checkpointsByConnector = Object.fromEntries(checkpointsByConnectorEntries);

    const payload = buildConnectorHealthPayload({
      connectors,
      progressByConnector,
      checkpointsByConnector,
    });

    return Response.json(payload);
  } catch (error) {
    console.error('Error loading connector health:', error);
    return Response.json({ error: 'Failed to load connector health' }, { status: 500 });
  }
}
