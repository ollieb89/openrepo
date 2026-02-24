import {
  getConnectorState,
  listSyncProgressEntries,
  saveSyncProgressByKey,
  updateConnectorHealth,
  upsertConnectorState,
} from '../connectors/store';
import { loadCheckpoint, saveCheckpoint } from './checkpoints';
import { saveSyncRecords } from './storage';
import { processNewRecords } from './summarizer';
import { classifyConnectorHealth } from './health';
import type {
  ConnectorCheckpoint,
  ConnectorCursorPayload,
  ConnectorProgressCounters,
  ConnectorSourceScope,
  ConnectorState,
  SyncProgressSnapshot,
  SyncStage,
} from '../types/connectors';

export interface SyncRecord {
  id: string;
  payload: Record<string, unknown>;
}

export interface SyncBatch {
  records: SyncRecord[];
  scanned?: number;
  changed?: number;
  nextCursor: ConnectorCursorPayload;
  retryAttempts?: number;
}

export interface ConnectorSyncAdapter {
  listSources(connector: ConnectorState): Promise<ConnectorSourceScope[]>;
  scanChanges(input: {
    connector: ConnectorState;
    source: ConnectorSourceScope;
    checkpoint: ConnectorCheckpoint | null;
  }): AsyncIterable<SyncBatch> | Promise<SyncBatch[]>;
  upsertRecords(input: {
    connector: ConnectorState;
    source: ConnectorSourceScope;
    records: SyncRecord[];
  }): Promise<number>;
}

export interface IncrementalSyncRunResult {
  connectorId: string;
  status: 'completed';
  startedAt: string;
  completedAt: string;
  sourceResults: Array<{
    sourceId: string;
    counters: ConnectorProgressCounters;
    checkpoint: ConnectorCheckpoint | null;
  }>;
}

const adapterRegistry = new Map<string, ConnectorSyncAdapter>();

export function registerConnectorSyncAdapter(provider: string, adapter: ConnectorSyncAdapter): void {
  adapterRegistry.set(provider, adapter);
}

export function clearConnectorSyncAdaptersForTests(): void {
  adapterRegistry.clear();
}

export async function listConnectorProgress(connectorId?: string): Promise<SyncProgressSnapshot[]> {
  return listSyncProgressEntries(connectorId);
}

function extractHttpStatus(error: unknown): number | null {
  if (!error || typeof error !== 'object') {
    return null;
  }

  const maybeStatus = (error as { status?: unknown; statusCode?: unknown }).status;
  if (typeof maybeStatus === 'number') {
    return maybeStatus;
  }

  const maybeStatusCode = (error as { statusCode?: unknown }).statusCode;
  if (typeof maybeStatusCode === 'number') {
    return maybeStatusCode;
  }

  return null;
}

async function* toAsyncIterable<T>(
  batches: AsyncIterable<T> | Promise<T[]>
): AsyncIterable<T> {
  if (Symbol.asyncIterator in Object(batches)) {
    for await (const batch of batches as AsyncIterable<T>) {
      yield batch;
    }
    return;
  }

  const resolved = await (batches as Promise<T[]>);
  for (const item of resolved) {
    yield item;
  }
}

function buildProgressKey(connectorId: string, sourceId: string): string {
  return `${connectorId}::${sourceId}`;
}

function safeErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return 'Sync failed for unknown reason';
}

async function emitProgressSnapshot(input: {
  connectorId: string;
  sourceId: string;
  counters: ConnectorProgressCounters;
  stage: SyncStage;
  retries: number;
  startedAtMs: number;
}): Promise<SyncProgressSnapshot> {
  const now = new Date().toISOString();
  const elapsedSeconds = Math.max((Date.now() - input.startedAtMs) / 1000, 0.001);
  const throughputPerSecond = Number((input.counters.upserted / elapsedSeconds).toFixed(2));
  const snapshot: SyncProgressSnapshot = {
    connectorId: input.connectorId,
    sourceId: input.sourceId,
    stage: input.stage,
    counters: { ...input.counters },
    throughputPerSecond,
    retry: {
      attempts: input.retries,
      lastRetryAt: input.retries > 0 ? now : null,
    },
    updatedAt: now,
  };

  await saveSyncProgressByKey(buildProgressKey(input.connectorId, input.sourceId), snapshot);
  return snapshot;
}

export async function runIncrementalSync(input: {
  connectorId: string;
  adapter?: ConnectorSyncAdapter;
}): Promise<IncrementalSyncRunResult> {
  const startedAt = new Date().toISOString();
  const startedAtMs = Date.now();

  const connector = await getConnectorState(input.connectorId);
  if (!connector) {
    throw new Error(`Connector not found: ${input.connectorId}`);
  }

  const adapter = input.adapter || adapterRegistry.get(connector.provider);
  if (!adapter) {
    throw new Error(`No sync adapter registered for provider: ${connector.provider}`);
  }

  await updateConnectorHealth(connector.id, { status: 'syncing' });

  let sources = connector.sources;
  if (sources.length === 0) {
    sources = await adapter.listSources(connector);
    await upsertConnectorState({
      ...connector,
      sources,
      status: 'syncing',
    });
  }

  const sourceResults: IncrementalSyncRunResult['sourceResults'] = [];

  try {
    for (const source of sources) {
      const counters: ConnectorProgressCounters = { scanned: 0, changed: 0, upserted: 0 };
      let retries = 0;

      await emitProgressSnapshot({
        connectorId: connector.id,
        sourceId: source.sourceId,
        counters,
        stage: 'loading_checkpoint',
        retries,
        startedAtMs,
      });

      const checkpoint = await loadCheckpoint(connector.id, source.sourceId);
      await emitProgressSnapshot({
        connectorId: connector.id,
        sourceId: source.sourceId,
        counters,
        stage: 'scanning',
        retries,
        startedAtMs,
      });

      for await (const batch of toAsyncIterable(adapter.scanChanges({ connector, source, checkpoint }))) {
        counters.scanned += batch.scanned ?? batch.records.length;
        counters.changed += batch.changed ?? batch.records.length;
        retries += batch.retryAttempts ?? 0;

        await emitProgressSnapshot({
          connectorId: connector.id,
          sourceId: source.sourceId,
          counters,
          stage: 'persisting',
          retries,
          startedAtMs,
        });

        const upserted = await adapter.upsertRecords({
          connector,
          source,
          records: batch.records,
        });
        counters.upserted += upserted;

        // Persist records locally for summarization (Phase 3)
        await saveSyncRecords(connector.id, source.sourceId, batch.records);

        await emitProgressSnapshot({
          connectorId: connector.id,
          sourceId: source.sourceId,
          counters,
          stage: 'saving_checkpoint',
          retries,
          startedAtMs,
        });

        await saveCheckpoint({
          connectorId: connector.id,
          sourceId: source.sourceId,
          cursor: batch.nextCursor,
        });

        await emitProgressSnapshot({
          connectorId: connector.id,
          sourceId: source.sourceId,
          counters,
          stage: 'scanning',
          retries,
          startedAtMs,
        });
      }

      const finalCheckpoint = await loadCheckpoint(connector.id, source.sourceId);

      await emitProgressSnapshot({
        connectorId: connector.id,
        sourceId: source.sourceId,
        counters,
        stage: 'completed',
        retries,
        startedAtMs,
      });

      sourceResults.push({
        sourceId: source.sourceId,
        counters,
        checkpoint: finalCheckpoint,
      });

      // Trigger local decision summarization (Phase 3)
      // This runs background extraction using Ollama/Phi-3
      processNewRecords(connector.id, source.sourceId).catch(err => {
        console.error(`[Engine] Failed to trigger summarization for ${source.sourceId}:`, err);
      });
    }

    await updateConnectorHealth(connector.id, {
      status: 'connected',
      lastSyncedAt: new Date().toISOString(),
    });

    return {
      connectorId: connector.id,
      status: 'completed',
      startedAt,
      completedAt: new Date().toISOString(),
      sourceResults,
    };
  } catch (error) {
    const status = classifyConnectorHealth({
      httpStatus: extractHttpStatus(error),
      error,
    });

    await updateConnectorHealth(connector.id, {
      status,
      lastError: safeErrorMessage(error),
    });

    throw error;
  }
}
