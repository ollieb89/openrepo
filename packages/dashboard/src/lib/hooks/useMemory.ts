import useSWR from 'swr';
import type { MemoryListResponse } from '@/lib/types/memory';
import { apiPath } from '@/lib/api-client';

const fetcher = (url: string) => fetch(url).then(res => res.json());

export function useMemory(projectId: string | null, searchQuery: string | null = null) {
  const params = new URLSearchParams();
  if (projectId) params.set('project', projectId);
  if (searchQuery) params.set('search', searchQuery);

  const key = projectId ? apiPath(`/api/memory?${params.toString()}`) : null;

  const { data, error, isLoading, mutate } = useSWR<MemoryListResponse>(
    key,
    fetcher,
    { revalidateOnFocus: false }
  );

  return {
    items: data?.items ?? [],
    total: data?.total ?? 0,
    mode: data?.mode ?? 'browse',
    isLoading,
    error,
    mutate,
  };
}
