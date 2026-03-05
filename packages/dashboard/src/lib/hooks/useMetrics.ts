import useSWR from 'swr';
import type { MetricsResponse } from '@/lib/types';

import { apiJson } from '@/lib/api-client';

const fetcher = <T>(url: string): Promise<T> => apiJson<T>(url);

export function useMetrics(projectId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<MetricsResponse>(
    projectId ? `/api/metrics?project=${projectId}` : null,
    fetcher,
    { refreshInterval: 5000 }
  );
  return { metrics: data || null, isLoading, error, refresh: mutate };
}
