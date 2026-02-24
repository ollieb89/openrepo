import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';

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
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    -- VSS table for 1024-dim vectors (mxbai-embed-large dimension)
    -- This requires the vss extension to be loaded
    -- CREATE VIRTUAL TABLE IF NOT EXISTS vss_cache USING vss0(
    --   embedding(1024)
    -- );
  `);

  return db;
}
