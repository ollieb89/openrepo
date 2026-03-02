import useSWR from 'swr';
import type { Project } from '@/lib/types';
import { apiPath } from '@/lib/api-client';

const fetcher = (url: string) => fetch(url).then(res => res.json());

export function useProjects() {
  const { data, error, isLoading } = useSWR<{ projects: Project[]; activeId: string }>(
    apiPath('/api/projects'),
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
