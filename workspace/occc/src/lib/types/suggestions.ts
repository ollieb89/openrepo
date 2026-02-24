export interface EvidenceExample {
  task_id: string;
  excerpt: string;
}

export interface Suggestion {
  id: string;
  status: 'pending' | 'accepted' | 'rejected';
  created_at: number;          // Unix timestamp
  pattern_description: string;
  evidence_count: number;
  evidence_examples: EvidenceExample[];
  diff_text: string;
  rejected_at: number | null;
  rejection_reason: string | null;
  suppressed_until_count: number | null;
  accepted_at: number | null;
}

export interface SuggestionsData {
  version: string;
  last_run: string | null;     // ISO timestamp or null
  suggestions: Suggestion[];
}
