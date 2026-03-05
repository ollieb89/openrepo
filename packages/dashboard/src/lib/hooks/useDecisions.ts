import useSWR from 'swr';
import type { Decision } from '@/lib/types/decisions';
import { apiJson } from '@/lib/api-client';

export function useDecisions(projectId: string | null) {
  return useSWR<Decision[]>(
    projectId ? `/api/decisions?projectId=${encodeURIComponent(projectId)}` : null,
    (url: string) => apiJson<Decision[]>(url),
    { refreshInterval: 3000, dedupingInterval: 1500, keepPreviousData: true }
  );
}
