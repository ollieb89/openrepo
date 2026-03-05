import useSWR from 'swr';
import type { Task } from '@/lib/types';
import { apiJson } from '@/lib/api-client';

export function useEscalatingTasks(projectId: string | null) {
  return useSWR<{ tasks: Task[] }>(
    projectId ? `/api/tasks?state=escalating&project=${encodeURIComponent(projectId)}` : null,
    (url: string) => apiJson<{ tasks: Task[] }>(url),
    { refreshInterval: 3000, dedupingInterval: 1500, keepPreviousData: true }
  );
}
