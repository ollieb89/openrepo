export interface IntentMetadata {
  query: string;
  timeRange: {
    start: string | null; // ISO Date
    end: string | null;   // ISO Date
  };
  boostedProjectId: string | null;
  limit: number; // Default based on look-back
}
