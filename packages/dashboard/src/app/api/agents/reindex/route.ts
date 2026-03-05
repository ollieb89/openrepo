import { NextRequest, NextResponse } from 'next/server';
import { getDb } from '@/lib/db';
import { withAuth } from '@/lib/auth-middleware';
import { withWriteLock } from '@/lib/safety';
import path from 'path';
import fs from 'fs/promises';
import os from 'os';
import crypto from 'crypto';

const OPENCLAW_ROOT = process.env.OPENCLAW_ROOT || path.join(os.homedir(), '.openclaw');
const AGENTS_DIR = path.join(OPENCLAW_ROOT, 'agents');

async function handler(request: NextRequest): Promise<NextResponse> {
    const requestId = crypto.randomUUID();
    try {
        const db = getDb();

        // Ensure agents directory exists
        try {
            await fs.access(AGENTS_DIR);
        } catch {
            return NextResponse.json({ error: 'Agents directory not found' }, { status: 404 });
        }

        const entries = await fs.readdir(AGENTS_DIR, { withFileTypes: true });
        const discovered = [];

        for (const entry of entries) {
            if (!entry.isDirectory()) continue;

            const agentId = entry.name;
            const manifestPath = path.join(AGENTS_DIR, agentId, 'agent.json');

            try {
                const raw = await fs.readFile(manifestPath, 'utf-8');
                const manifest = JSON.parse(raw);

                // Normalize slug: [a-z0-9-_]
                const normalizedId = agentId.toLowerCase().replace(/[^a-z0-9-_]/g, '-');

                db.prepare(`
          INSERT OR REPLACE INTO agents (id, name, path, level, model_id, provider_id, enabled, last_indexed, metadata_json)
          VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
        `).run(
                    normalizedId,
                    manifest.name || agentId,
                    path.relative(OPENCLAW_ROOT, path.join(AGENTS_DIR, agentId)),
                    manifest.level || 1,
                    manifest.model?.id || null,
                    manifest.model?.provider || null,
                    1,
                    JSON.stringify(manifest)
                );

                discovered.push(normalizedId);
            } catch (e) {
                // Skip agents with missing or invalid manifest
                console.warn(`[reindex] Failed to index agent at ${agentId}:`, e);
            }
        }

        // Record in audit log
        db.prepare(`
      INSERT INTO audit_log (id, request_id, actor, action, target, diff_summary, status)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `).run(
            crypto.randomUUID(),
            requestId,
            'system',
            'reindex',
            'agents',
            `Re-indexed agents from filesystem. Discovered ${discovered.length} agents.`,
            'success'
        );

        return NextResponse.json({
            success: true,
            requestId,
            count: discovered.length,
            agents: discovered
        });
    } catch (error: any) {
        console.error('Error re-indexing agents:', error);
        return NextResponse.json({ error: 'Failed to re-index agents', message: error.message }, { status: 500 });
    }
}

export const POST = withAuth(withWriteLock(handler));
