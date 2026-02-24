
import { initVectorStore, upsertVectorRecord, searchContext, VectorRecord } from './src/lib/sync/vector-store';
import { addEdge } from './src/lib/sync/graph';
import { IntentMetadata } from './src/lib/sync/types/intent';

async function test() {
  console.log('Setting up test data...');
  const db = initVectorStore();
  
  // Clear tables for clean test
  db.prepare('DELETE FROM edges').run();
  db.prepare('DELETE FROM vector_cache').run();

  const recordA: VectorRecord = {
    id: 'A',
    entity_type: 'decision',
    content: 'Semantic match for query',
    metadata: { projectId: 'P1', created_at: '2026-02-24T10:00:00Z' },
    embedding: new Array(1024).fill(0).map((_, i) => i === 0 ? 1 : 0)
  };

  const recordB: VectorRecord = {
    id: 'B',
    entity_type: 'issue',
    content: 'Graph neighbor of A, but no semantic match',
    metadata: { projectId: 'P2', created_at: '2026-02-20T10:00:00Z' },
    embedding: new Array(1024).fill(0).map((_, i) => i === 1 ? 1 : 0)
  };

  const recordC: VectorRecord = {
    id: 'C',
    entity_type: 'decision',
    content: 'Unrelated record',
    metadata: { projectId: 'P3' },
    embedding: new Array(1024).fill(0).map((_, i) => i === 2 ? 1 : 0)
  };

  // Explicitly set created_at in the database since upsertVectorRecord uses CURRENT_TIMESTAMP by default
  // Wait, I should check if upsertVectorRecord allows overriding created_at.
  // It doesn't in the current implementation. I'll modify it or manually update the DB.
  
  upsertVectorRecord(recordA);
  upsertVectorRecord(recordB);
  upsertVectorRecord(recordC);

  // Manually update created_at for testing temporal filters
  db.prepare("UPDATE vector_cache SET created_at = '2026-02-24 10:00:00' WHERE id = 'A'").run();
  db.prepare("UPDATE vector_cache SET created_at = '2026-02-20 10:00:00' WHERE id = 'B'").run();

  console.log('Adding edge A -> B');
  addEdge('A', 'B', 'related_to');

  const intent: any = {
    query: 'Semantic match',
    timeRange: {
      start: '2026-02-23T00:00:00Z' // Should include A, exclude B
    },
    limit: 10,
    boostedProjectId: 'P1'
  };

  // We need a query embedding that matches A but not B
  const queryEmbedding = new Array(1024).fill(0).map((_, i) => i === 0 ? 1 : 0);

  console.log('Running searchContext...');
  const results = await searchContext(intent, queryEmbedding);

  console.log('Results:');
  results.forEach((r: any) => {
    console.log(`- ${r.id}: score=${r._score}, content="${r.content}"`);
  });

  const foundB = results.find(r => r.id === 'B');
  if (foundB) {
    console.log('SUCCESS: Record B found in results via graph expansion');
    if ((foundB as any)._score > 0.3) {
        console.log('SUCCESS: Record B has a boosted score');
    }
  } else {
    console.log('FAILURE: Record B NOT found in results');
  }

  db.close();
}

test().catch(console.error);
