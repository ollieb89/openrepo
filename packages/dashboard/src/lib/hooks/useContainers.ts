import useSWR from 'swr';
import type { Container } from '@/lib/types';
import { apiJson } from '@/lib/api-client';

const fetcher = <T>(url: string): Promise<T> =>
  apiJson<T>(url, { method: 'POST' });

export function useContainers() {
  const { data, error, isLoading } = useSWR<{ containers: Container[] }>(
    '/api/swarm/stream',
    fetcher,
    { refreshInterval: 5000 }
  );

  return {
    containers: data?.containers || [],
    isLoading,
    error,
  };
}
