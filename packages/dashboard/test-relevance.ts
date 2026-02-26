import { calculateScore } from './src/lib/sync/relevance';
import { VectorRecord } from './src/lib/sync/vector-store';

const mockDecision: VectorRecord = {
  id: 'DEC-1',
  entity_type: 'decision',
  content: 'We decided to use sqlite-vss for vector search in GH-123.',
  metadata: { created_at: '2024-01-01T10:00:00Z' },
  embedding: [0.1, 0.2, 0.3]
};

const mockIssue: VectorRecord = {
  id: 'GH-123',
  entity_type: 'issue',
  content: 'Implement vector search using sqlite-vss.',
  metadata: { created_at: '2024-01-01T12:00:00Z' },
  embedding: [0.1, 0.2, 0.31]
};

const result = calculateScore(mockDecision, mockIssue);
console.log('Explicit mention + Semantic + Temporal:', result);

const mockIssue2: VectorRecord = {
  id: 'LIN-45',
  entity_type: 'issue',
  content: 'Something unrelated but has keyword api.',
  metadata: { created_at: '2024-01-10T12:00:00Z' },
  embedding: [0.9, -0.1, 0.0]
};

const result2 = calculateScore(mockDecision, mockIssue2);
console.log('Unrelated:', result2);
