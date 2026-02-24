import {
  getCheckpointByKey,
  listCheckpointEntries,
  saveCheckpointByKey,
} from '@/lib/connectors/store';
import type { ConnectorCheckpoint, ConnectorCursorPayload } from '@/lib/types/connectors';

export function buildCheckpointKey(connectorId: string, sourceId: string): string {
  return `${connectorId}::${sourceId}`;
}

export async function loadCheckpoint(
  connectorId: string,
  sourceId: string
): Promise<ConnectorCheckpoint | null> {
  return getCheckpointByKey(buildCheckpointKey(connectorId, sourceId));
}

export async function saveCheckpoint(input: {
  connectorId: string;
  sourceId: string;
  cursor: ConnectorCursorPayload;
}): Promise<ConnectorCheckpoint> {
  const checkpoint: ConnectorCheckpoint = {
    connectorId: input.connectorId,
    sourceId: input.sourceId,
    cursor: input.cursor,
    updatedAt: new Date().toISOString(),
  };

  return saveCheckpointByKey(buildCheckpointKey(input.connectorId, input.sourceId), checkpoint);
}

export async function listCheckpointsForConnector(connectorId: string): Promise<ConnectorCheckpoint[]> {
  const entries = await listCheckpointEntries();
  return entries.filter(entry => entry.connectorId === connectorId);
}
