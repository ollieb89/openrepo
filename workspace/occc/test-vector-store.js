const Database = require('better-sqlite3');
const path = require('path');
const fs = require('fs');

const GET_DB_PATH = () => {
  const root = process.env.OPENCLAW_ROOT || process.cwd();
  return path.join(root, 'workspace', '.openclaw', 'nexus-sync.db');
};

const dbPath = GET_DB_PATH();
const dbDir = path.dirname(dbPath);

if (!fs.existsSync(dbDir)) {
  fs.mkdirSync(dbDir, { recursive: true });
}

if (fs.existsSync(dbPath)) {
  fs.unlinkSync(dbPath);
}

const db = new Database(dbPath);

db.exec(`
  CREATE TABLE IF NOT EXISTS vector_cache (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  );
`);

const tableInfo = db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='vector_cache';").get();
if (tableInfo && tableInfo.name === 'vector_cache') {
  console.log('SUCCESS: Table vector_cache exists');
} else {
  console.error('FAILURE: Table vector_cache does not exist');
  process.exit(1);
}

const columns = db.prepare("PRAGMA table_info(vector_cache);").all();
const columnNames = columns.map(c => c.name);
['id', 'entity_type', 'content', 'metadata', 'created_at'].forEach(col => {
  if (columnNames.includes(col)) {
    console.log(`SUCCESS: Column ${col} exists`);
  } else {
    console.error(`FAILURE: Column ${col} missing`);
    process.exit(1);
  }
});

db.close();
