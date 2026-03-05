import Database from 'better-sqlite3';
import path from 'path';
import os from 'os';

const OPENCLAW_ROOT = process.env.OPENCLAW_ROOT || path.join(os.homedir(), '.openclaw');
const DB_PATH = path.join(OPENCLAW_ROOT, 'openclaw_config.db');

// Database instance singleton
let dbInstance: Database.Database | null = null;

export function getDb(): Database.Database {
    if (!dbInstance) {
        dbInstance = new Database(DB_PATH, { verbose: console.log });
    }
    return dbInstance;
}

export type GatewaySetting = {
    key: string;
    value: string;
};

export type AuditLogEntry = {
    id: string;
    request_id?: string;
    timestamp: string;
    actor: string;
    action: string;
    target: string;
    before_json?: string;
    after_json?: string;
    diff_summary?: string;
    status: string;
    message?: string;
    config_hash?: string;
};

export type AgentEntry = {
    id: string;
    name: string;
    path: string;
    level: number;
    model_id?: string;
    provider_id?: string;
    enabled: number;
    last_indexed: string;
    metadata_json?: string;
};
