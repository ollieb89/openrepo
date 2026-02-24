import { getVectorRecord, getVectorRecords, upsertLinkSuggestion } from './vector-store';
import { calculateScore } from './relevance';

const SUGGESTION_THRESHOLD = 0.6;

/**
 * Generates link suggestions for a given decision ID.
 * Identifies the most relevant issues and persists them as suggestions.
 */
export async function generateSuggestions(decisionId: string) {
  try {
    const decision = getVectorRecord(decisionId);
    if (!decision || decision.entity_type !== 'decision') {
      console.warn(`[Suggestions] Decision ${decisionId} not found in vector cache.`);
      return;
    }

    // 1. Get all issues for comparison
    // In a large dataset, we would use a vector search query here.
    // For now, we load all and filter in memory.
    const issues = getVectorRecords('issue');

    if (issues.length === 0) {
      console.log('[Suggestions] No issues found in cache to link against.');
      return;
    }

    let suggestionsCount = 0;

    for (const issue of issues) {
      const { score, reasons } = calculateScore(decision, issue);

      if (score >= SUGGESTION_THRESHOLD) {
        upsertLinkSuggestion({
          id: crypto.randomUUID(),
          decision_id: decisionId,
          issue_id: issue.id,
          score,
          status: 'pending',
          reasons,
        });
        suggestionsCount++;
      }
    }

    if (suggestionsCount > 0) {
      console.log(`[Suggestions] Generated ${suggestionsCount} suggestions for decision ${decisionId}`);
    }
  } catch (error) {
    console.error(`[Suggestions] Failed to generate suggestions for decision ${decisionId}:`, error);
  }
}
