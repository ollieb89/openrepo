export interface VectorRecord {
  id: string;
  entity_type: 'decision' | 'issue';
  content: string;
  metadata: any;
  embedding: number[];
}

export interface LinkSuggestion {
  id: string;
  decision_id: string;
  issue_id: string;
  score: number;
  status: 'pending' | 'accepted' | 'rejected';
  reasons: string[];
}
