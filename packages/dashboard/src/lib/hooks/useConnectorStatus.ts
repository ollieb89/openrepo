'use client';

import { useMemo, useState } from 'react';
import useSWR from 'swr';
import type { ConnectorHealthStatus, ConnectorSourceScope, ConnectorState } from '@/lib/types/connectors';
import { apiPath } from '@/lib/api-client';

const SLACK_CONNECTOR_ID = 'connector-slack-primary';

interface ConnectorDetailResponse {
  connector: ConnectorState;
}

interface SlackChannelScopeResponse {
  connected: boolean;
  channels: ConnectorSourceScope[];
  selectedChannelIds: string[];
  firstSyncWindowDays: number;
}

const fetcher = async (url: string) => {
  const response = await fetch(url);
  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
  return response.json();
};

function statusHelp(status: ConnectorHealthStatus | 'disconnected'): string {
  if (status === 'rate_limited') {
    return 'Slack is rate-limited. Wait a minute, then retry Sync now.';
  }

  if (status === 'auth_expired') {
    return 'Slack authorization expired. Reconnect workspace with a new OAuth code.';
  }

  if (status === 'syncing') {
    return 'Sync in progress.';
  }

  if (status === 'connected') {
    return 'Workspace connected and ready.';
  }

  return 'Workspace disconnected.';
}

export function useConnectorStatus() {
  const [isMutating, setIsMutating] = useState(false);

  const connectorSWR = useSWR<ConnectorDetailResponse | null>(
    apiPath(`/api/connectors?id=${encodeURIComponent(SLACK_CONNECTOR_ID)}`),
    fetcher,
    {
      refreshInterval: 5000,
      revalidateOnFocus: false,
    }
  );

  const channelsSWR = useSWR<SlackChannelScopeResponse | null>(apiPath('/api/connectors/slack/channels'), fetcher, {
    refreshInterval: 5000,
    revalidateOnFocus: false,
  });

  const connector = connectorSWR.data?.connector || null;
  const status: ConnectorHealthStatus | 'disconnected' = connector?.status || 'disconnected';
  const channels = channelsSWR.data?.channels || [];
  const selectedChannelIds = channelsSWR.data?.selectedChannelIds || [];
  const firstSyncWindowDays = channelsSWR.data?.firstSyncWindowDays || 30;

  const lastSyncedAt = connector?.lastSyncedAt || null;
  const lastError = connector?.lastError || null;

  const hint = useMemo(() => {
    if (lastError && (status === 'rate_limited' || status === 'auth_expired' || status === 'error')) {
      return `${statusHelp(status)} (${lastError})`;
    }

    if (status === 'error' && lastError) {
      return `Connector error: ${lastError}`;
    }

    return statusHelp(status);
  }, [lastError, status]);

  async function connectSlack(input: { code: string; redirectUri: string; firstSyncWindowDays: number }) {
    setIsMutating(true);
    try {
      const response = await fetch(apiPath('/api/connectors/slack/oauth'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(input),
      });

      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || 'Failed to connect Slack');
      }

      await Promise.all([connectorSWR.mutate(), channelsSWR.mutate()]);
    } finally {
      setIsMutating(false);
    }
  }

  async function saveChannelScope(input: { selectedChannelIds: string[]; firstSyncWindowDays: number }) {
    setIsMutating(true);
    try {
      const response = await fetch(apiPath('/api/connectors/slack/channels'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(input),
      });

      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || 'Failed to save Slack channel scope');
      }

      await Promise.all([connectorSWR.mutate(), channelsSWR.mutate()]);
    } finally {
      setIsMutating(false);
    }
  }

  async function syncNow(firstWindowDays?: number) {
    setIsMutating(true);
    try {
      const response = await fetch(apiPath('/api/connectors/slack/sync'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ firstSyncWindowDays: firstWindowDays }),
      });

      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || 'Slack sync failed');
      }

      await connectorSWR.mutate();
      return payload.result;
    } finally {
      setIsMutating(false);
    }
  }

  return {
    connector,
    status,
    channels,
    selectedChannelIds,
    firstSyncWindowDays,
    lastSyncedAt,
    hint,
    isLoading: connectorSWR.isLoading || channelsSWR.isLoading,
    isMutating,
    error: connectorSWR.error || channelsSWR.error || null,
    connectSlack,
    saveChannelScope,
    syncNow,
    refresh: async () => {
      await Promise.all([connectorSWR.mutate(), channelsSWR.mutate()]);
    },
  };
}
