import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';

const GET_DB_PATH = () => {
  const root = process.env.OPENCLAW_ROOT || process.cwd();
  return path.join(root, 'workspace', '.openclaw', 'nexus-sync.db');
};

function getDb() {
  const dbPath = GET_DB_PATH();
  return new Database(dbPath);
}

/**
 * Inserts a new edge or updates an existing one if it already exists.
 */
export function addEdge(sourceId: string, targetId: string, relationshipType: string, weight: number = 1.0, metadata: any = {}) {
  const db = getDb();
  try {
    const stmt = db.prepare(`
      INSERT INTO edges (source_id, target_id, relationship_type, weight, metadata)
      VALUES (?, ?, ?, ?, ?)
      ON CONFLICT(source_id, target_id, relationship_type) DO UPDATE SET
        weight = excluded.weight,
        metadata = excluded.metadata,
        created_at = CURRENT_TIMESTAMP
    `);

    stmt.run(
      sourceId,
      targetId,
      relationshipType,
      weight,
      JSON.stringify(metadata)
    );
  } finally {
    db.close();
  }
}

/**
 * Returns all direct neighbors for a given node (both as source and target).
 */
export function getNeighbors(nodeId: string) {
  const db = getDb();
  try {
    const stmt = db.prepare(`
      SELECT 
        e.*,
        v.content as neighbor_content,
        v.entity_type as neighbor_entity_type,
        v.metadata as neighbor_metadata,
        'out' as direction
      FROM edges e
      JOIN vector_cache v ON e.target_id = v.id
      WHERE e.source_id = ?
      
      UNION ALL
      
      SELECT 
        e.*,
        v.content as neighbor_content,
        v.entity_type as neighbor_entity_type,
        v.metadata as neighbor_metadata,
        'in' as direction
      FROM edges e
      JOIN vector_cache v ON e.source_id = v.id
      WHERE e.target_id = ?
    `);

    const rows = stmt.all(nodeId, nodeId) as any[];
    return rows.map(row => ({
      ...row,
      metadata: JSON.parse(row.metadata),
      neighbor_metadata: JSON.parse(row.neighbor_metadata)
    }));
  } finally {
    db.close();
  }
}
