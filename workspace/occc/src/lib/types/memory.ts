export interface MemoryItem {
  id: string;
  content?: string;
  category?: string;
  agent_type?: string;
  type?: string;
  created_at?: string | number;
  user_id?: string;
  metadata?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface MemoryListResponse {
  items: MemoryItem[];
  total: number;
  projectId: string;
  mode: 'browse' | 'search';
}
