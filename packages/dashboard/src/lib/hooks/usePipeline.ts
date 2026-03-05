import useSWR from 'swr';
import { apiJson } from '@/lib/api-client';

export function usePipeline(projectId: string | null, taskId?: string) {
  const key = projectId
    ? `/api/pipeline?project=${projectId}${taskId ? `&taskId=${taskId}` : ''}`
    : null;
  const { data, error, isLoading } = useSWR(key, (url: string) => apiJson(url), {
    refreshInterval: taskId ? 5000 : 10000,
    revalidateOnFocus: false,
  });
  return {
    pipelines: (data as any)?.pipelines ?? [],
    isLoading,
    error,
  };
}
