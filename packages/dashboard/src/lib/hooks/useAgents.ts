import useSWR from 'swr';
import type { Agent } from '@/lib/types';
import { apiJson } from '@/lib/api-client';

const fetcher = <T>(url: string): Promise<T> => apiJson<T>(url);

export function useAgents(projectId: string | null) {
  const { data, error, isLoading } = useSWR<{ agents: Agent[] }>(
    '/api/agents',
    fetcher,
    { revalidateOnFocus: false }
  );

  // Filter: show agents that belong to this project or have no project (global agents)
  const agents = (data?.agents || []).filter(
    a => !a.project || a.project === projectId
  );

  return {
    agents,
    isLoading,
    error,
  };
}
