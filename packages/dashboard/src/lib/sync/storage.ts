import fs from 'fs';
import path from 'path';
import os from 'os';
import { redactSensitiveData } from '../redaction';
import type { SyncRecord } from './engine';
import type { Decision } from '../types/decisions';

const GET_RECORDS_ROOT = () => {
  const root = process.env.OPENCLAW_ROOT || path.join(os.homedir(), '.openclaw');
  return path.join(root, 'workspace', '.openclaw', 'records');
};

/**
 * Saves a batch of sync records to the local filesystem after applying redaction.
 * Performs an upsert based on record ID.
 */
export async function saveSyncRecords(
  connectorId: string,
  sourceId: string,
  records: SyncRecord[]
): Promise<void> {
  if (records.length === 0) return;

  const filePath = path.join(GET_RECORDS_ROOT(), connectorId, `${sourceId}.json`);
  const fileDir = path.dirname(filePath);
  if (!fs.existsSync(fileDir)) {
    fs.mkdirSync(fileDir, { recursive: true });
  }

  // Load existing records if any
  let existingRecords: SyncRecord[] = [];
  if (fs.existsSync(filePath)) {
    try {
      const content = fs.readFileSync(filePath, 'utf8');
      existingRecords = JSON.parse(content);
    } catch (e) {
      console.error(`Failed to load existing records from ${filePath}:`, e);
    }
  }

  // Redact new records
  const redactedRecords = records.map(record => {
    const newPayload = { ...record.payload };
    if (typeof newPayload.text === 'string') {
      newPayload.text = redactSensitiveData(newPayload.text);
    }
    // Also redact raw text if it exists
    if (newPayload.raw && typeof (newPayload.raw as any).text === 'string') {
      (newPayload.raw as any).text = redactSensitiveData((newPayload.raw as any).text);
    }
    
    return {
      ...record,
      payload: newPayload
    };
  });

  // Simple merge by ID (upsert)
  const recordMap = new Map<string, SyncRecord>();
  existingRecords.forEach(r => recordMap.set(r.id, r));
  redactedRecords.forEach(r => recordMap.set(r.id, r));

  const mergedRecords = Array.from(recordMap.values());

  fs.writeFileSync(filePath, JSON.stringify(mergedRecords, null, 2));
}

/**
 * Loads sync records for a given connector and source.
 */
export async function loadSyncRecords(
  connectorId: string,
  sourceId: string
): Promise<SyncRecord[]> {
  const filePath = path.join(GET_RECORDS_ROOT(), connectorId, `${sourceId}.json`);
  if (!fs.existsSync(filePath)) {
    return [];
  }

  try {
    const content = fs.readFileSync(filePath, 'utf8');
    return JSON.parse(content);
  } catch (e) {
    console.error(`Failed to load records from ${filePath}:`, e);
    return [];
  }
}

/**
 * Saves a batch of decisions to the local filesystem.
 * Mapped by connectorId (project-level).
 */
export async function saveDecisions(
  connectorId: string,
  decisions: Decision[]
): Promise<void> {
  if (decisions.length === 0) return;

  const decisionsDir = path.join(GET_RECORDS_ROOT(), 'decisions');
  if (!fs.existsSync(decisionsDir)) {
    fs.mkdirSync(decisionsDir, { recursive: true });
  }

  const filePath = path.join(decisionsDir, `${connectorId}.json`);

  // Load existing decisions if any
  let existing: Decision[] = [];
  if (fs.existsSync(filePath)) {
    try {
      const content = fs.readFileSync(filePath, 'utf8');
      existing = JSON.parse(content);
    } catch (e) {
      console.error(`Failed to load decisions from ${filePath}:`, e);
    }
  }

  // Merge by decision ID
  const map = new Map<string, Decision>();
  existing.forEach(d => map.set(d.id, d));
  decisions.forEach(d => map.set(d.id, d));

  fs.writeFileSync(filePath, JSON.stringify(Array.from(map.values()), null, 2));
}

/**
 * Loads decisions for a given connector.
 */
export async function loadDecisions(
  connectorId: string
): Promise<Decision[]> {
  const filePath = path.join(GET_RECORDS_ROOT(), 'decisions', `${connectorId}.json`);
  if (!fs.existsSync(filePath)) {
    return [];
  }

  try {
    const content = fs.readFileSync(filePath, 'utf8');
    return JSON.parse(content);
  } catch (e) {
    console.error(`Failed to load decisions from ${filePath}:`, e);
    return [];
  }
}
