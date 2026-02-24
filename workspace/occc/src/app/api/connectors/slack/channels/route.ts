import { NextRequest } from 'next/server';
import {
  DEFAULT_FIRST_SYNC_WINDOW_DAYS,
  getSlackConnectorState,
  listSlackChannels,
  saveSlackChannelSelection,
} from '@/lib/connectors/slack';

interface SaveChannelScopePayload {
  selectedChannelIds?: string[];
  firstSyncWindowDays?: number;
}

export async function GET() {
  try {
    const connector = await getSlackConnectorState();
    if (!connector) {
      return Response.json({ ok: true, connected: false, channels: [], selectedChannelIds: [] });
    }

    const channels = await listSlackChannels(connector.id);
    const metadata = (connector.metadata || {}) as Record<string, unknown>;
    const selectedChannelIds = Array.isArray(metadata.selectedChannelIds)
      ? metadata.selectedChannelIds.filter((value): value is string => typeof value === 'string')
      : [];

    const firstSyncWindowDays =
      typeof metadata.firstSyncWindowDays === 'number'
        ? metadata.firstSyncWindowDays
        : DEFAULT_FIRST_SYNC_WINDOW_DAYS;

    return Response.json({
      ok: true,
      connected: true,
      channels,
      selectedChannelIds,
      firstSyncWindowDays,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to load Slack channels';
    return Response.json({ ok: false, error: message }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as SaveChannelScopePayload;
    if (!Array.isArray(body.selectedChannelIds)) {
      return Response.json({ ok: false, error: 'selectedChannelIds must be an array' }, { status: 400 });
    }

    const connector = await saveSlackChannelSelection({
      selectedChannelIds: body.selectedChannelIds,
      firstSyncWindowDays: body.firstSyncWindowDays,
    });

    return Response.json({ ok: true, connector });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to save Slack channel scope';
    const status = message.includes('not connected') ? 404 : 500;
    return Response.json({ ok: false, error: message }, { status });
  }
}
