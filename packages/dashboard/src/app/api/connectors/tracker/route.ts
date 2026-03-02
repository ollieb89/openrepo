import { NextRequest, NextResponse } from 'next/server';
import { getConnectorState, upsertConnectorState } from '@/lib/connectors/store';
import {
  buildTrackerSources,
  readTrackerConnectorConfig,
  type TrackerProvider,
} from '@/lib/connectors/tracker';
import { listCheckpointsForConnector } from '@/lib/sync/checkpoints';
import { listConnectorProgress } from '@/lib/sync/engine';
import { withAuth } from '@/lib/auth-middleware';

const TRACKER_CONNECTOR_ID = 'connector-tracker';

interface TrackerConfigRequest {
  provider: TrackerProvider;
  config: Record<string, unknown>;
  enabled?: boolean;
}

function validateRequest(input: unknown): TrackerConfigRequest {
  if (!input || typeof input !== 'object' || Array.isArray(input)) {
    throw new Error('Invalid request body');
  }

  const provider = (input as { provider?: unknown }).provider;
  const config = (input as { config?: unknown }).config;
  const enabledInput = (input as { enabled?: unknown }).enabled;
  const enabled = typeof enabledInput === 'boolean' ? enabledInput : undefined;

  if (provider !== 'github' && provider !== 'linear') {
    throw new Error('Unsupported tracker provider');
  }

  if (!config || typeof config !== 'object' || Array.isArray(config)) {
    throw new Error('Tracker config must be an object');
  }

  if (enabled != null && typeof enabled !== 'boolean') {
    throw new Error('enabled must be a boolean');
  }

  return {
    provider,
    config: config as Record<string, unknown>,
    enabled,
  };
}

async function loadTrackerConnectorPayload() {
  const connector = await getConnectorState(TRACKER_CONNECTOR_ID);
  if (!connector) {
    return {
      connector: null,
      checkpoints: [],
      progress: [],
      reauthRequired: false,
    };
  }

  const [checkpoints, progress] = await Promise.all([
    listCheckpointsForConnector(connector.id),
    listConnectorProgress(connector.id),
  ]);

  return {
    connector,
    checkpoints,
    progress,
    reauthRequired: connector.status === 'auth_expired',
  };
}

async function getHandler() {
  try {
    const payload = await loadTrackerConnectorPayload();
    return NextResponse.json(payload);
  } catch (error) {
    console.error('Error loading tracker connector:', error);
    return NextResponse.json({ error: 'Failed to load tracker connector' }, { status: 500 });
  }
}

async function postHandler(request: NextRequest) {
  try {
    const body = validateRequest(await request.json());

    const now = new Date().toISOString();
    const connectorCandidate = {
      id: TRACKER_CONNECTOR_ID,
      provider: body.provider,
      sources: [],
      status: 'connected' as const,
      enabled: body.enabled ?? true,
      metadata: {
        config: body.config,
      },
      createdAt: now,
      updatedAt: now,
    };

    const config = readTrackerConnectorConfig(connectorCandidate);
    const sources = buildTrackerSources(config);

    const saved = await upsertConnectorState({
      ...connectorCandidate,
      sources,
      lastError: undefined,
    });

    return NextResponse.json({ ok: true, connector: saved });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to configure tracker connector';
    return NextResponse.json({ ok: false, error: message }, { status: 400 });
  }
}

export const GET = withAuth(getHandler);
export const POST = withAuth(postHandler);
