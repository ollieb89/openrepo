import useSWR from 'swr';
import type { MetricsResponse } from '@/lib/types';

const fetcher = (url: string) => fetch(url).then(res => res.json());

export function useMetrics(projectId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<MetricsResponse>(
    projectId ? `/api/metrics?project=${projectId}` : null,
    fetcher,
    { refreshInterval: 5000 }
  );
  return { metrics: data || null, isLoading, error, refresh: mutate };
}
