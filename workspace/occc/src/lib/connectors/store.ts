import fs from 'fs/promises';
import path from 'path';
import type { ConnectorCheckpoint, ConnectorState, SyncProgressSnapshot } from '@/lib/types/connectors';

interface ConnectorRuntimeStore {
  connectors: Record<string, ConnectorState>;
  checkpoints: Record<string, ConnectorCheckpoint>;
  progress: Record<string, SyncProgressSnapshot>;
}

const OPENCLAW_ROOT = process.env.OPENCLAW_ROOT || '/home/ollie/.openclaw';
const DEFAULT_STORE_PATH = path.join(
  OPENCLAW_ROOT,
  'workspace',
  '.openclaw',
  'connectors',
  'runtime-store.json'
);
let writeQueue: Promise<void> = Promise.resolve();

function resolveStorePath(): string {
  return process.env.CONNECTOR_RUNTIME_STORE_PATH || DEFAULT_STORE_PATH;
}

function defaultStore(): ConnectorRuntimeStore {
  return {
    connectors: {},
    checkpoints: {},
    progress: {},
  };
}

async function readStoreFile(): Promise<ConnectorRuntimeStore> {
  try {
    const raw = await fs.readFile(resolveStorePath(), 'utf-8');
    const parsed = JSON.parse(raw) as Partial<ConnectorRuntimeStore>;

    return {
      connectors: parsed.connectors || {},
      checkpoints: parsed.checkpoints || {},
      progress: parsed.progress || {},
    };
  } catch {
    return defaultStore();
  }
}

async function writeStoreFile(store: ConnectorRuntimeStore): Promise<void> {
  const storePath = resolveStorePath();
  await fs.mkdir(path.dirname(storePath), { recursive: true });
  await fs.writeFile(storePath, JSON.stringify(store, null, 2), 'utf-8');
}

function queueWrite<T>(action: () => Promise<T>): Promise<T> {
  const next = writeQueue.then(action);
  writeQueue = next.then(
    () => undefined,
    () => undefined
  );
  return next;
}

export async function listConnectorStates(): Promise<ConnectorState[]> {
  const store = await readStoreFile();
  return Object.values(store.connectors);
}

export async function getConnectorState(connectorId: string): Promise<ConnectorState | null> {
  const store = await readStoreFile();
  return store.connectors[connectorId] || null;
}

export async function upsertConnectorState(
  input: Omit<ConnectorState, 'createdAt' | 'updatedAt'> & { createdAt?: string; updatedAt?: string }
): Promise<ConnectorState> {
  return queueWrite(async () => {
    const now = new Date().toISOString();
    const store = await readStoreFile();
    const current = store.connectors[input.id];

    const next: ConnectorState = {
      ...input,
      createdAt: current?.createdAt || input.createdAt || now,
      updatedAt: input.updatedAt || now,
    };

    store.connectors[input.id] = next;
    await writeStoreFile(store);
    return next;
  });
}

export async function updateConnectorHealth(
  connectorId: string,
  updates: {
    status: ConnectorState['status'];
    lastError?: string;
    lastSyncedAt?: string;
  }
): Promise<ConnectorState | null> {
  return queueWrite(async () => {
    const now = new Date().toISOString();
    const store = await readStoreFile();
    const current = store.connectors[connectorId];

    if (!current) {
      return null;
    }

    const next: ConnectorState = {
      ...current,
      status: updates.status,
      lastError: updates.lastError,
      lastSyncedAt: updates.lastSyncedAt || current.lastSyncedAt,
      updatedAt: now,
    };

    store.connectors[connectorId] = next;
    await writeStoreFile(store);
    return next;
  });
}

export async function getCheckpointByKey(key: string): Promise<ConnectorCheckpoint | null> {
  const store = await readStoreFile();
  return store.checkpoints[key] || null;
}

export async function saveCheckpointByKey(
  key: string,
  checkpoint: ConnectorCheckpoint
): Promise<ConnectorCheckpoint> {
  return queueWrite(async () => {
    const store = await readStoreFile();
    store.checkpoints[key] = checkpoint;
    await writeStoreFile(store);
    return checkpoint;
  });
}

export async function listCheckpointEntries(): Promise<ConnectorCheckpoint[]> {
  const store = await readStoreFile();
  return Object.values(store.checkpoints);
}

export async function getSyncProgressByKey(key: string): Promise<SyncProgressSnapshot | null> {
  const store = await readStoreFile();
  return store.progress[key] || null;
}

export async function saveSyncProgressByKey(
  key: string,
  progress: SyncProgressSnapshot
): Promise<SyncProgressSnapshot> {
  return queueWrite(async () => {
    const store = await readStoreFile();
    store.progress[key] = progress;
    await writeStoreFile(store);
    return progress;
  });
}

export async function listSyncProgressEntries(connectorId?: string): Promise<SyncProgressSnapshot[]> {
  const store = await readStoreFile();
  const entries = Object.values(store.progress);
  if (!connectorId) {
    return entries;
  }
  return entries.filter(entry => entry.connectorId === connectorId);
}

export async function clearConnectorRuntimeStoreForTests(): Promise<void> {
  await queueWrite(async () => {
    try {
      await fs.unlink(resolveStorePath());
    } catch {
      // no-op for missing file
    }
  });
}
