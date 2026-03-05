'use client';

import { useMemo, useState } from 'react';
import useSWR from 'swr';
import type { PrivacyExecutionMode } from '@/lib/types/privacy';
import type { PrivacyAuditEvent } from '@/lib/privacy/audit-log';
import { apiJson, apiFetch } from '@/lib/api-client';

interface PrivacySettings {
  projectId: string;
  remoteInferenceEnabled: boolean;
  updatedAt: string | null;
}

export interface PrivacyEventFilters {
  mode: 'all' | PrivacyExecutionMode;
  reason: string;
  connector: string;
  from: string;
  to: string;
}

const fetcher = async <T>(url: string): Promise<T> => {
  return apiJson<T>(url);
};

function toIsoFromInput(value: string): string {
  if (!value) return '';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '' : date.toISOString();
}

export function usePrivacy(projectId: string | null) {
  const [filters, setFilters] = useState<PrivacyEventFilters>({
    mode: 'all',
    reason: '',
    connector: '',
    from: '',
    to: '',
  });

  const settingsUrl = projectId
    ? `/api/privacy/settings?projectId=${encodeURIComponent(projectId)}`
    : null;

  const eventsUrl = useMemo(() => {
    if (!projectId) {
      return null;
    }

    const params = new URLSearchParams({ projectId });

    if (filters.mode !== 'all') {
      params.set('mode', filters.mode);
    }

    if (filters.reason.trim()) {
      params.set('reason', filters.reason.trim());
    }

    if (filters.connector.trim()) {
      params.set('connector', filters.connector.trim());
    }

    const fromIso = toIsoFromInput(filters.from);
    const toIso = toIsoFromInput(filters.to);

    if (fromIso) {
      params.set('from', fromIso);
    }

    if (toIso) {
      params.set('to', toIso);
    }

    return `/api/privacy/events?${params.toString()}`;
  }, [filters, projectId]);

  const settingsSWR = useSWR<{ projectId: string; remoteInferenceEnabled: boolean; updatedAt: string | null }>(
    settingsUrl,
    fetcher,
    { revalidateOnFocus: false }
  );

  const eventsSWR = useSWR<{ events: PrivacyAuditEvent[] }>(eventsUrl, fetcher, {
    revalidateOnFocus: false,
  });

  async function setRemoteConsent(enabled: boolean): Promise<void> {
    if (!projectId) return;

    await apiFetch('/api/privacy/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ projectId, remoteInferenceEnabled: enabled }),
    });

    await settingsSWR.mutate();
  }

  async function revokeConsent(): Promise<void> {
    if (!projectId) return;

    await apiFetch('/api/privacy/settings', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ projectId }),
    });

    await settingsSWR.mutate();
  }

  return {
    settings: (settingsSWR.data ?? null) as PrivacySettings | null,
    events: eventsSWR.data?.events ?? [],
    filters,
    setFilters,
    isLoadingSettings: settingsSWR.isLoading,
    isLoadingEvents: eventsSWR.isLoading,
    error: settingsSWR.error ?? eventsSWR.error,
    refreshEvents: eventsSWR.mutate,
    setRemoteConsent,
    revokeConsent,
  };
}
