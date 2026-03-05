import useSWR from 'swr';
import { useEffect } from 'react';
import type { Task } from '@/lib/types';
import { apiJson } from '@/lib/api-client';
import { useEvents } from '@/hooks/useEvents';

const fetcher = <T>(url: string): Promise<T> => apiJson<T>(url);

export function useTasks(projectId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<{ tasks: Task[] }>(
    projectId ? `/api/tasks?project=${projectId}` : null,
    fetcher,
    { refreshInterval: 3000 }
  );

  const { lastEvent } = useEvents(projectId ?? undefined);

  useEffect(() => {
    if (!lastEvent) return;
    if (lastEvent.type.startsWith('task.')) mutate();
  }, [lastEvent, mutate]);

  return {
    tasks: data?.tasks || [],
    isLoading,
    error,
  };
}
