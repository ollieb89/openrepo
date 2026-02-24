import type {
  PersistedMetadataInput,
  PersistedMetadataRecord,
  PersistenceRawContentMode,
} from '@/lib/types/privacy';

export const PERSISTENCE_ALLOWLIST = [
  'sourceId',
  'threadId',
  'timestamp',
  'connector',
  'entityType',
  'provenance',
] as const;

const RAW_CONTENT_KEYS = new Set([
  'body',
  'content',
  'raw',
  'rawbody',
  'rawcontent',
  'text',
  'markdown',
  'html',
  'payload',
  'fulltext',
]);

const DEFAULT_RAW_CONTENT_MODE: PersistenceRawContentMode = 'reject';

interface MinimizePersistenceOptions {
  rawContentMode?: PersistenceRawContentMode;
  now?: () => Date;
}

function normalizeKey(key: string): string {
  return key.toLowerCase().replace(/[^a-z0-9]/g, '');
}

function findRawContentPath(value: unknown, currentPath = ''): string | null {
  if (Array.isArray(value)) {
    for (let i = 0; i < value.length; i += 1) {
      const path = findRawContentPath(value[i], `${currentPath}[${i}]`);
      if (path) return path;
    }
    return null;
  }

  if (!value || typeof value !== 'object') {
    return null;
  }

  for (const [key, child] of Object.entries(value)) {
    const keyPath = currentPath ? `${currentPath}.${key}` : key;
    if (RAW_CONTENT_KEYS.has(normalizeKey(key))) {
      return keyPath;
    }

    const nested = findRawContentPath(child, keyPath);
    if (nested) return nested;
  }

  return null;
}

function getRequiredString(value: unknown, fieldName: string): string {
  if (typeof value !== 'string' || value.trim() === '') {
    throw new Error(`Persisted metadata requires a non-empty "${fieldName}" field.`);
  }
  return value;
}

function getTimestamp(value: unknown, now: () => Date): string {
  if (value === undefined) {
    return now().toISOString();
  }

  if (typeof value !== 'string' || value.trim() === '') {
    throw new Error('Persisted metadata requires "timestamp" to be an ISO string when provided.');
  }

  return value;
}

function getThreadId(value: unknown): string | undefined {
  if (value === undefined) return undefined;
  if (typeof value !== 'string' || value.trim() === '') {
    throw new Error('Persisted metadata requires "threadId" to be a non-empty string when provided.');
  }
  return value;
}

export function minimizePersistenceRecord(
  input: PersistedMetadataInput,
  options: MinimizePersistenceOptions = {}
): PersistedMetadataRecord {
  const rawContentMode = options.rawContentMode ?? DEFAULT_RAW_CONTENT_MODE;
  const now = options.now ?? (() => new Date());

  const rawPath = findRawContentPath(input);
  if (rawPath && rawContentMode === 'reject') {
    throw new Error(`Raw content field "${rawPath}" is not allowed in persisted records.`);
  }

  const sourceId = getRequiredString(input.sourceId, 'sourceId');
  const connector = getRequiredString(input.connector, 'connector');
  const entityType = getRequiredString(input.entityType, 'entityType');
  const timestamp = getTimestamp(input.timestamp, now);
  const threadId = getThreadId(input.threadId);

  const provenance = input.provenance ?? {};
  const sourceLink =
    typeof provenance.sourceLink === 'string' && provenance.sourceLink.trim() !== ''
      ? provenance.sourceLink
      : `openclaw://source/${encodeURIComponent(sourceId)}`;
  const provenanceTimestamp =
    typeof provenance.timestamp === 'string' && provenance.timestamp.trim() !== ''
      ? provenance.timestamp
      : timestamp;
  const connectorLabel =
    typeof provenance.connectorLabel === 'string' && provenance.connectorLabel.trim() !== ''
      ? provenance.connectorLabel
      : connector;

  const minimized: PersistedMetadataRecord = {
    sourceId,
    timestamp,
    connector,
    entityType,
    provenance: {
      sourceLink,
      timestamp: provenanceTimestamp,
      connectorLabel,
    },
  };

  if (threadId) {
    minimized.threadId = threadId;
  }

  return minimized;
}
