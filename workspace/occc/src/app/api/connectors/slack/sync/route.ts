import { NextRequest } from 'next/server';
import { getConnectorState } from '@/lib/connectors/store';
import {
  DEFAULT_FIRST_SYNC_WINDOW_DAYS,
  SLACK_CONNECTOR_ID,
  ensureSlackAdapterRegistered,
  saveSlackChannelSelection,
} from '@/lib/connectors/slack';
import { listCheckpointsForConnector } from '@/lib/sync/checkpoints';
import { runIncrementalSync } from '@/lib/sync/engine';

interface SlackSyncPayload {
  firstSyncWindowDays?: number;
}

function isValidWindow(days: unknown): days is number {
  const n = Number(days);
  return Number.isFinite(n) && n >= 1 && n <= 90;
}

export async function POST(request: NextRequest) {
  try {
    ensureSlackAdapterRegistered();

    const body = (await request.json().catch(() => ({}))) as SlackSyncPayload;
    const connector = await getConnectorState(SLACK_CONNECTOR_ID);

    if (!connector) {
      return Response.json({ ok: false, error: 'Slack connector not found' }, { status: 404 });
    }

    const checkpoints = await listCheckpointsForConnector(SLACK_CONNECTOR_ID);
    const isFirstSync = checkpoints.length === 0;

    if (isFirstSync) {
      const metadata = (connector.metadata || {}) as Record<string, unknown>;
      const existingWindow = metadata.firstSyncWindowDays;
      const selectedWindow =
        isValidWindow(body.firstSyncWindowDays)
          ? body.firstSyncWindowDays
          : isValidWindow(existingWindow)
            ? existingWindow
            : DEFAULT_FIRST_SYNC_WINDOW_DAYS;

      await saveSlackChannelSelection({
        selectedChannelIds: Array.isArray(metadata.selectedChannelIds)
          ? metadata.selectedChannelIds.filter((value): value is string => typeof value === 'string')
          : [],
        firstSyncWindowDays: selectedWindow,
      });
    }

    const result = await runIncrementalSync({ connectorId: SLACK_CONNECTOR_ID });
    return Response.json({ ok: true, result });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to sync Slack';
    const status = message.toLowerCase().includes('not found') ? 404 : 500;
    return Response.json({ ok: false, error: message }, { status });
  }
}
