import useSWR from 'swr';
import type { Container } from '@/lib/types';

const fetcher = (url: string) =>
  fetch(url, { method: 'POST' }).then(res => res.json());

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
