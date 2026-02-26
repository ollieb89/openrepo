import { generateEmbedding } from '../ollama';
import { upsertVectorRecord } from './vector-store';

/**
 * Indexes an entity into the vector cache.
 * Generates an embedding and stores it in the vector_cache table.
 * 
 * @param id The unique identifier for the entity.
 * @param type The type of entity ('decision' or 'issue').
 * @param content The text content to be vectorized.
 * @param metadata Additional metadata for the entity.
 */
export async function indexEntity(
  id: string,
  type: 'decision' | 'issue',
  content: string,
  metadata: any
) {
  try {
    // 1. Generate embedding using mxbai-embed-large (as configured in ollama.ts)
    const embedding = await generateEmbedding(content);

    // 2. Store in vector_cache via vector-store.ts
    // Note: upsertVectorRecord handles the ON CONFLICT logic.
    upsertVectorRecord({
      id,
      entity_type: type,
      content,
      metadata,
      embedding,
    });
  } catch (error) {
    console.error(`[Indexer] Failed to index entity ${type}:${id}:`, error);
    throw error;
  }
}
