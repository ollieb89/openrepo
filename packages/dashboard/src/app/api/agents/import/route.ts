import { NextRequest, NextResponse } from 'next/server';
import { getDb } from '@/lib/db';
import { withAuth } from '@/lib/auth-middleware';
import { withWriteLock } from '@/lib/safety';
import path from 'path';
import fs from 'fs/promises';
import os from 'os';
import crypto from 'crypto';
import { spawn } from 'child_process';

const OPENCLAW_ROOT = process.env.OPENCLAW_ROOT || path.join(os.homedir(), '.openclaw');
const AGENTS_DIR = path.join(OPENCLAW_ROOT, 'agents');

async function handler(request: NextRequest): Promise<NextResponse> {
    const requestId = crypto.randomUUID();
    const tempDir = path.join(os.tmpdir(), `oc-import-${requestId}`);

    try {
        const formData = await request.formData();
        const file = formData.get('file') as File;

        if (!file) {
            return NextResponse.json({ error: 'No file uploaded' }, { status: 400 });
        }

        await fs.mkdir(tempDir, { recursive: true });
        const tempFilePath = path.join(tempDir, file.name);
        const buffer = Buffer.from(await file.arrayBuffer());
        await fs.writeFile(tempFilePath, buffer);

        let agentId: string;
        let manifest: any;

        if (file.name.endsWith('.json')) {
            // Manifest-only import
            manifest = JSON.parse(buffer.toString());
            agentId = manifest.id || file.name.replace('.json', '');
            const agentDir = path.join(AGENTS_DIR, agentId);

            await fs.mkdir(agentDir, { recursive: true });
            await fs.writeFile(path.join(agentDir, 'agent.json'), buffer);
        } else if (file.name.endsWith('.zip')) {
            // ZIP import
            const unzipDir = path.join(tempDir, 'unzipped');
            await fs.mkdir(unzipDir, { recursive: true });

            await new Promise((resolve, reject) => {
                const unzip = spawn('unzip', [tempFilePath, '-d', unzipDir]);
                unzip.on('close', (code) => code === 0 ? resolve(null) : reject(new Error('Unzip failed')));
            });

            // Find agent.json
            const files = await fs.readdir(unzipDir);
            // Handles both direct files and nested folder in zip
            let sourceDir = unzipDir;
            if (files.length === 1 && (await fs.stat(path.join(unzipDir, files[0]))).isDirectory()) {
                sourceDir = path.join(unzipDir, files[0]);
            }

            const manifestPath = path.join(sourceDir, 'agent.json');
            try {
                const raw = await fs.readFile(manifestPath, 'utf-8');
                manifest = JSON.parse(raw);
                agentId = manifest.id || path.basename(sourceDir);
            } catch (e) {
                throw new Error('Invalid agent: agent.json missing or corrupt');
            }

            const agentDir = path.join(AGENTS_DIR, agentId);
            // Safety: reject symlinks
            // (Simple check: readdir and stat each file if needed, but for v1 we'll move the whole dir)
            await fs.mkdir(AGENTS_DIR, { recursive: true });
            try {
                await fs.access(agentDir);
                return NextResponse.json({ error: `Agent ${agentId} already exists` }, { status: 409 });
            } catch { }

            await fs.rename(sourceDir, agentDir);
        } else {
            return NextResponse.json({ error: 'Unsupported file type' }, { status: 400 });
        }

        // Index in database
        const db = getDb();
        db.prepare(`
      INSERT OR REPLACE INTO agents (id, name, path, level, model_id, provider_id, enabled, last_indexed, metadata_json)
      VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
    `).run(
            agentId,
            manifest.name || agentId,
            path.relative(OPENCLAW_ROOT, path.join(AGENTS_DIR, agentId)),
            manifest.level || 1,
            manifest.model?.id || null,
            manifest.model?.provider || null,
            1,
            JSON.stringify(manifest)
        );

        // Audit log
        db.prepare(`
      INSERT INTO audit_log (id, request_id, actor, action, target, diff_summary, status)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `).run(
            crypto.randomUUID(),
            requestId,
            'user',
            'agent_import',
            `agent:${agentId}`,
            `Imported agent: ${agentId} from ${file.name}`,
            'success'
        );

        return NextResponse.json({ success: true, agentId, requestId });
    } catch (error: any) {
        console.error('Import error:', error);
        return NextResponse.json({ error: 'Import failed', message: error.message }, { status: 500 });
    } finally {
        await fs.rm(tempDir, { recursive: true, force: true }).catch(() => { });
    }
}

export const POST = withAuth(withWriteLock(handler));
