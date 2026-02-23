import useSWR from 'swr';
import type { Task } from '@/lib/types';

const fetcher = (url: string) => fetch(url).then(res => res.json());

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
