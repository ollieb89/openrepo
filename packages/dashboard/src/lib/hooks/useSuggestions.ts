import useSWR from 'swr';
import { apiJson } from '@/lib/api-client';

interface SuggestionRecord {
  id: string;
  status: string;
  evidence_count: number;
  title?: string;
  summary?: string;
}

export interface SuggestionsResponse {
  version: string;
  last_run: number | null;
  suggestions: SuggestionRecord[];
}

export function useSuggestions(projectId: string | null) {
  return useSWR<SuggestionsResponse>(
    projectId ? `/api/suggestions?project=${encodeURIComponent(projectId)}` : null,
    (url: string) => apiJson<SuggestionsResponse>(url),
    { refreshInterval: 3000, dedupingInterval: 1500, keepPreviousData: true }
  );
}
