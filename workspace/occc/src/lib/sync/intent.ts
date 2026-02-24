import * as chrono from 'chrono-node';
import { IntentMetadata } from './types/intent';

/**
 * Parses a natural language query into structured intent metadata.
 * Extracts temporal information and sets up project-based boosting.
 */
export function parseIntent(query: string, activeProjectId?: string): IntentMetadata {
  const results = chrono.parse(query);
  let start: string | null = null;
  let end: string | null = null;

  if (results.length > 0) {
    // We take the first temporal expression found
    const result = results[0];
    
    if (result.start) {
      start = result.start.date().toISOString();
    }
    
    if (result.end) {
      end = result.end.date().toISOString();
    }
  }

  // Default to "Last 7 Days" if no start date was found
  if (!start) {
    const now = new Date();
    const defaultStart = new Date(now);
    defaultStart.setDate(now.getDate() - 7);
    start = defaultStart.toISOString();
  }

  return {
    query,
    timeRange: {
      start,
      end,
    },
    boostedProjectId: activeProjectId || null,
    limit: 50, // Default limit for retrieval
  };
}
