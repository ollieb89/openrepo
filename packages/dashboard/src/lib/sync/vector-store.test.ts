import { expect, test, describe, beforeAll, afterAll } from 'bun:test';
import { initVectorStore } from './vector-store';
import fs from 'fs';
import path from 'path';

describe('Vector Store Initialization', () => {
  const root = process.cwd();
  const dbPath = path.join(root, 'workspace', '.openclaw', 'nexus-sync.db');

  beforeAll(() => {
    // Ensure workspace directory exists
    const dbDir = path.dirname(dbPath);
    if (!fs.existsSync(dbDir)) {
      fs.mkdirSync(dbDir, { recursive: true });
    }
    
    // Clean up existing test database if it exists
    if (fs.existsSync(dbPath)) {
      fs.unlinkSync(dbPath);
    }
  });

  afterAll(() => {
    // Optional: Clean up after tests
    // if (fs.existsSync(dbPath)) {
    //   fs.unlinkSync(dbPath);
    // }
  });

  test('initVectorStore creates the database and the vector_cache table', () => {
    const db = initVectorStore();
    
    // Verify table creation
    const tableInfo = db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='vector_cache';").get() as { name: string };
    
    expect(tableInfo).toBeDefined();
    expect(tableInfo.name).toBe('vector_cache');
    
    // Verify columns
    const columns = db.prepare("PRAGMA table_info(vector_cache);").all() as Array<{ name: string, type: string }>;
    const columnNames = columns.map(c => c.name);
    
    expect(columnNames).toContain('id');
    expect(columnNames).toContain('entity_type');
    expect(columnNames).toContain('content');
    expect(columnNames).toContain('metadata');
    expect(columnNames).toContain('created_at');
    
    db.close();
  });
});
