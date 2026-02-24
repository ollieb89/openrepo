import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';
import { IntentMetadata } from './types/intent';
import { calculateScore } from './relevance';

const GET_DB_PATH = () => {
  const root = process.env.OPENCLAW_ROOT || process.cwd();
  return path.join(root, 'workspace', '.openclaw', 'nexus-sync.db');
};

export function initVectorStore() {
  const dbPath = GET_DB_PATH();
  const dbDir = path.dirname(dbPath);
  
  if (!fs.existsSync(dbDir)) {
    fs.mkdirSync(dbDir, { recursive: true });
  }

  const db = new Database(dbPath);
  
  // Note: sqlite-vss needs to be loaded as an extension. 
  // For the plan, we'll assume the extension path is managed via env or relative to workspace.
  // db.loadExtension(path.join(process.cwd(), 'bin', 'vss0'));

  db.exec(`
    CREATE TABLE IF NOT EXISTS vector_cache (
      id TEXT PRIMARY KEY,
      entity_type TEXT NOT NULL, -- 'decision' or 'issue'
      content TEXT NOT NULL,
      metadata JSON,
      embedding JSON,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    -- VSS table for 1024-dim vectors (mxbai-embed-large dimension)
    -- This requires the vss extension to be loaded
    -- CREATE VIRTUAL TABLE IF NOT EXISTS vss_cache USING vss0(
    --   embedding(1024)
    -- );

    CREATE TABLE IF NOT EXISTS link_suggestions (
      id TEXT PRIMARY KEY,
      decision_id TEXT NOT NULL,
      issue_id TEXT NOT NULL,
      score REAL NOT NULL,
      status TEXT DEFAULT 'pending', -- 'pending', 'accepted', 'rejected'
      reasons JSON, -- e.g. ["explicit_mention", "semantic_similarity"]
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(decision_id, issue_id)
    );

    CREATE TABLE IF NOT EXISTS edges (
      source_id TEXT NOT NULL,
      target_id TEXT NOT NULL,
      relationship_type TEXT NOT NULL,
      weight REAL DEFAULT 1.0,
      metadata JSON,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (source_id, target_id, relationship_type),
      FOREIGN KEY (source_id) REFERENCES vector_cache(id),
      FOREIGN KEY (target_id) REFERENCES vector_cache(id)
    );

    CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
    CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
  `);

  return db;
}

export interface VectorRecord {
  id: string;
  entity_type: 'decision' | 'issue';
  content: string;
  metadata: any;
  embedding: number[];
}

/**
 * Upsert a vector record into the cache.
 */
export function upsertVectorRecord(record: VectorRecord) {
  const db = initVectorStore();
  try {
    const stmt = db.prepare(`
      INSERT INTO vector_cache (id, entity_type, content, metadata, embedding)
      VALUES (?, ?, ?, ?, ?)
      ON CONFLICT(id) DO UPDATE SET
        entity_type = excluded.entity_type,
        content = excluded.content,
        metadata = excluded.metadata,
        embedding = excluded.embedding,
        created_at = CURRENT_TIMESTAMP
    `);

    stmt.run(
      record.id,
      record.entity_type,
      record.content,
      JSON.stringify(record.metadata),
      JSON.stringify(record.embedding)
    );
  } finally {
    db.close();
  }
}

/**
 * Get all vector records of a specific type.
 */
export function getVectorRecords(type: 'decision' | 'issue'): VectorRecord[] {
  const db = initVectorStore();
  try {
    const stmt = db.prepare('SELECT * FROM vector_cache WHERE entity_type = ?');
    const rows = stmt.all(type);
    return rows.map((row: any) => ({
      ...row,
      metadata: JSON.parse(row.metadata),
      embedding: JSON.parse(row.embedding)
    }));
  } finally {
    db.close();
  }
}

/**
 * Get a single vector record by ID.
 */
export function getVectorRecord(id: string): VectorRecord | null {
  const db = initVectorStore();
  try {
    const stmt = db.prepare('SELECT * FROM vector_cache WHERE id = ?');
    const row = stmt.get(id) as any;
    if (!row) return null;
    return {
      ...row,
      metadata: JSON.parse(row.metadata),
      embedding: JSON.parse(row.embedding)
    };
  } finally {
    db.close();
  }
}

export interface LinkSuggestion {
  id: string;
  decision_id: string;
  issue_id: string;
  score: number;
  status: 'pending' | 'accepted' | 'rejected';
  reasons: string[];
}

/**
 * Upsert a link suggestion.
 */
export function upsertLinkSuggestion(suggestion: LinkSuggestion) {
  const db = initVectorStore();
  try {
    const stmt = db.prepare(`
      INSERT INTO link_suggestions (id, decision_id, issue_id, score, status, reasons)
      VALUES (?, ?, ?, ?, ?, ?)
      ON CONFLICT(decision_id, issue_id) DO UPDATE SET
        score = excluded.score,
        reasons = excluded.reasons,
        created_at = CURRENT_TIMESTAMP
    `);

    stmt.run(
      suggestion.id,
      suggestion.decision_id,
      suggestion.issue_id,
      suggestion.score,
      suggestion.status,
      JSON.stringify(suggestion.reasons)
    );
  } finally {
    db.close();
  }
}

/**
 * Get all pending link suggestions, joined with vector_cache records for display.
 */
export function getPendingSuggestions() {
  const db = initVectorStore();
  try {
    const stmt = db.prepare(`
      SELECT 
        ls.*,
        d.content as decision_content,
        d.metadata as decision_metadata,
        i.content as issue_content,
        i.metadata as issue_metadata
      FROM link_suggestions ls
      JOIN vector_cache d ON ls.decision_id = d.id
      JOIN vector_cache i ON ls.issue_id = i.id
      WHERE ls.status = 'pending'
      ORDER BY ls.score DESC
    `);
    
    const rows = stmt.all() as any[];
    return rows.map(row => ({
      ...row,
      reasons: JSON.parse(row.reasons),
      decision_metadata: JSON.parse(row.decision_metadata),
      issue_metadata: JSON.parse(row.issue_metadata)
    }));
  } finally {
    db.close();
  }
}

/**
 * Update the status of a link suggestion.
 */
export function updateLinkSuggestionStatus(id: string, status: 'accepted' | 'rejected') {
  const db = initVectorStore();
  try {
    const stmt = db.prepare('UPDATE link_suggestions SET status = ? WHERE id = ?');
    const result = stmt.run(status, id);
    return result.changes > 0;
  } finally {
    db.close();
  }
}

/**
 * Searches for relevant context records based on intent (temporal, project, semantic).
 * Applies a +0.3 boost to records in the active project.
 */
export async function searchContext(intent: IntentMetadata, queryEmbedding?: number[]): Promise<VectorRecord[]> {
  const db = initVectorStore();
  try {
    let sql = 'SELECT * FROM vector_cache WHERE 1=1';
    const params: any[] = [];

    if (intent.timeRange.start) {
      sql += ' AND created_at >= ?';
      params.push(intent.timeRange.start);
    }
    if (intent.timeRange.end) {
      sql += ' AND created_at <= ?';
      params.push(intent.timeRange.end);
    }

    const rows = db.prepare(sql).all(...params) as any[];
    
    const records = rows.map(row => ({
      ...row,
      metadata: JSON.parse(row.metadata),
      embedding: JSON.parse(row.embedding)
    })) as VectorRecord[];

    // Calculate scores and apply boosts
    const scoredRecords = records.map(record => {
      let finalScore = 0;
      
      if (queryEmbedding) {
        // Mock a decision record for calculateScore
        const mockDecision: VectorRecord = {
          id: 'query',
          entity_type: 'decision',
          content: intent.query,
          metadata: {},
          embedding: queryEmbedding
        };
        const { score } = calculateScore(mockDecision, record);
        finalScore = score;
      } else {
        // If no embedding, use a baseline score
        finalScore = 0.5;
      }

      // Apply +0.3 boost for active project
      if (intent.boostedProjectId && record.metadata?.projectId === intent.boostedProjectId) {
        finalScore += 0.3;
      }

      return {
        ...record,
        _score: Math.min(1.0, finalScore)
      } as VectorRecord & { _score: number };
    });

    // Sort by score descending and apply limit
    return scoredRecords
      .sort((a, b) => b._score - a._score)
      .slice(0, intent.limit) as VectorRecord[];

  } finally {
    db.close();
  }
}
