import useSWR from 'swr';
import type { Task } from '@/lib/types';
import { apiJson } from '@/lib/api-client';

const fetcher = <T>(url: string): Promise<T> => apiJson<T>(url);

export function useTasks(projectId: string | null) {
  const { data, error, isLoading } = useSWR<{ tasks: Task[] }>(
    projectId ? `/api/tasks?project=${projectId}` : null,
    fetcher,
    { refreshInterval: 3000 }
  );

  return {
    tasks: data?.tasks || [],
    isLoading,
    error,
  };
}
