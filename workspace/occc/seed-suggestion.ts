import { upsertLinkSuggestion, LinkSuggestion } from './src/lib/sync/vector-store';

const suggestion: LinkSuggestion = {
  id: 'test-s1',
  decision_id: 'test-d1',
  issue_id: 'test-i1',
  score: 0.85,
  status: 'pending',
  reasons: ['semantic_similarity']
};

try {
  upsertLinkSuggestion(suggestion);
  console.log('Seed suggestion created');
} catch (error) {
  console.error('Failed to seed suggestion:', error);
}
