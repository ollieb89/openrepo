import { NextRequest, NextResponse } from 'next/server';
import {
  DEFAULT_FIRST_SYNC_WINDOW_DAYS,
  getSlackConnectorState,
  listSlackChannels,
  saveSlackChannelSelection,
} from '@/lib/connectors/slack';
import { withAuth } from '@/lib/auth-middleware';

interface SaveChannelScopePayload {
  selectedChannelIds?: string[];
  firstSyncWindowDays?: number;
}

async function getHandler() {
  try {
    const connector = await getSlackConnectorState();
    if (!connector) {
      return NextResponse.json({ ok: true, connected: false, channels: [], selectedChannelIds: [] });
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

    return NextResponse.json({
      ok: true,
      connected: true,
      channels,
      selectedChannelIds,
      firstSyncWindowDays,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to load Slack channels';
    return NextResponse.json({ ok: false, error: message }, { status: 500 });
  }
}

async function postHandler(request: NextRequest) {
  try {
    const body = (await request.json()) as SaveChannelScopePayload;
    if (!Array.isArray(body.selectedChannelIds)) {
      return NextResponse.json({ ok: false, error: 'selectedChannelIds must be an array' }, { status: 400 });
    }

    const connector = await saveSlackChannelSelection({
      selectedChannelIds: body.selectedChannelIds,
      firstSyncWindowDays: body.firstSyncWindowDays,
    });

    return NextResponse.json({ ok: true, connector });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to save Slack channel scope';
    const status = message.includes('not connected') ? 404 : 500;
    return NextResponse.json({ ok: false, error: message }, { status });
  }
}

export const GET = withAuth(getHandler);
export const POST = withAuth(postHandler);
