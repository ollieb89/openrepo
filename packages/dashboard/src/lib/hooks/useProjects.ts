import useSWR from 'swr';
import type { Project } from '@/lib/types';
import { apiJson } from '@/lib/api-client';

const fetcher = <T>(url: string): Promise<T> => apiJson<T>(url);

export function useProjects() {
  const { data, error, isLoading } = useSWR<{ projects: Project[]; activeId: string }>(
    '/api/projects',
    fetcher,
    { revalidateOnFocus: false }
  );

  return {
    projects: data?.projects || [],
    activeId: data?.activeId || null,
    isLoading,
    error,
  };
}
