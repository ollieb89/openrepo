import useSWR from 'swr';
import type { TopologyApiResponse, ChangelogApiResponse, ChangelogEntry } from '@/lib/types/topology';
import { apiJson } from '@/lib/api-client';

const fetcher = <T>(url: string): Promise<T> => apiJson<T>(url);

/**
 * SWR hook for fetching the current topology (approved graph + pending proposals).
 * Refreshes every 30 seconds to pick up new proposal sets or approved corrections.
 */
export function useTopology(projectId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<TopologyApiResponse>(
    projectId ? `/api/topology?project=${projectId}` : null,
    fetcher,
    { refreshInterval: 30000 }
  );

  return {
    topology: data || null,
    isLoading,
    error,
    refresh: mutate,
  };
}

/**
 * SWR hook for fetching the topology correction changelog.
 * Returns sorted changelog entries for the correction timeline and confidence chart.
 */
export function useTopologyChangelog(projectId: string | null) {
  const { data, error, isLoading } = useSWR<ChangelogApiResponse>(
    projectId ? `/api/topology/changelog?project=${projectId}` : null,
    fetcher,
    { refreshInterval: 30000 }
  );

  const changelog: ChangelogEntry[] = data?.changelog || [];

  return {
    changelog,
    isLoading,
    error,
  };
}
