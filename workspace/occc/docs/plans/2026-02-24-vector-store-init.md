# Vector Store Initialization (TypeScript & Ollama) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Establish the foundation for semantic search by creating the Ollama embedding service and setting up the initial SQLite-VSS database structure.

**Architecture:** Use `ollama.embeddings()` to generate vectors and `better-sqlite3` with a manually loaded `sqlite-vss` extension for local persistence and similarity search.

**Tech Stack:** `ollama-js`, `better-sqlite3`, `sqlite-vss` (pre-compiled extension).

---

### Task 1: Extend Ollama Bridge for Embeddings

**Files:**
- Modify: `src/lib/ollama.ts`
- Test: `src/lib/ollama.test.ts`

**Step 1: Update `src/lib/ollama.ts` to include `generateEmbedding`**

```typescript
/**
 * Generate a vector embedding for a string using a local model.
 */
export async function generateEmbedding(text: string): Promise<number[]> {
  if (!(await isOllamaAvailable())) {
    throw new Error('Ollama service is not available');
  }

  try {
    const response = await ollama.embeddings({
      model: 'mxbai-embed-large', // Recommended for high quality local embeddings
      prompt: text,
    });

    return response.embedding;
  } catch (error) {
    console.error('[Ollama] Error generating embedding:', error);
    throw error;
  }
}
```

**Step 2: Update tests and verify**

Run: `bun test src/lib/ollama.test.ts`
Expected: PASS

**Step 3: Commit**

```bash
git add src/lib/ollama.ts
git commit -m "feat(04-01): add generateEmbedding to ollama bridge"
```

---

### Task 2: SQLite-VSS Database Initialization

**Files:**
- Create: `src/lib/sync/vector-store.ts`
- Create: `src/lib/sync/vector-store.test.ts`

**Step 1: Install `better-sqlite3` and identify `sqlite-vss` loading path**

Run: `bun add better-sqlite3`

**Step 2: Implement the Vector Store service**

```typescript
import Database from 'better-sqlite3';
import path from 'path';

const GET_DB_PATH = () => {
  const root = process.env.OPENCLAW_ROOT || process.cwd();
  return path.join(root, 'workspace', '.openclaw', 'nexus-sync.db');
};

export function initVectorStore() {
  const db = new Database(GET_DB_PATH());
  
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
```

**Step 3: Commit**

```bash
git add src/lib/sync/vector-store.ts
git commit -m "feat(04-01): initialize vector store database schema"
```
