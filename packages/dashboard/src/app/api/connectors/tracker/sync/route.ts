import { NextResponse } from 'next/server';
import { getConnectorState } from '@/lib/connectors/store';
import { createGithubTrackerAdapter } from '@/lib/connectors/tracker-github';
import { createLinearTrackerAdapter } from '@/lib/connectors/tracker-linear';
import {
  TRACKER_PROVIDER_GITHUB,
  TRACKER_PROVIDER_LINEAR,
  assertTrackerProvider,
} from '@/lib/connectors/tracker';
import { runIncrementalSync } from '@/lib/sync/engine';
import { withAuth } from '@/lib/auth-middleware';

const DEFAULT_TRACKER_CONNECTOR_ID = 'connector-tracker';

function buildAdapter(provider: string) {
  const safeProvider = assertTrackerProvider(provider);
  if (safeProvider === TRACKER_PROVIDER_GITHUB) {
    return createGithubTrackerAdapter();
  }
  if (safeProvider === TRACKER_PROVIDER_LINEAR) {
    return createLinearTrackerAdapter();
  }
  return null;
}

async function handler(request: Request) {
  try {
    const body = (await request.json().catch(() => ({}))) as { connectorId?: string };
    const connectorId = body.connectorId || DEFAULT_TRACKER_CONNECTOR_ID;
    const connector = await getConnectorState(connectorId);

    if (!connector) {
      return NextResponse.json({ ok: false, error: 'Tracker connector not found' }, { status: 404 });
    }

    const adapter = buildAdapter(connector.provider);
    if (!adapter) {
      return NextResponse.json({ ok: false, error: 'Unsupported tracker provider' }, { status: 400 });
    }

    const result = await runIncrementalSync({
      connectorId: connector.id,
      adapter,
    });

    return NextResponse.json({ ok: true, result });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to run tracker sync';
    const status = message.includes('not found') ? 404 : 500;
    return NextResponse.json({ ok: false, error: message }, { status });
  }
}

export const POST = withAuth(handler);
