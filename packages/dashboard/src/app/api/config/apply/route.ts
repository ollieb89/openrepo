import { NextRequest, NextResponse } from 'next/server';
import { getDb } from '@/lib/db';
import { withAuth } from '@/lib/auth-middleware';
import { withWriteLock } from '@/lib/safety';
import path from 'path';
import fs from 'fs/promises';
import { spawn } from 'child_process';
import os from 'os';
import crypto from 'crypto';

const OPENCLAW_ROOT = process.env.OPENCLAW_ROOT || path.join(os.homedir(), '.openclaw');
const CONFIG_PATH = path.join(OPENCLAW_ROOT, 'openclaw.json');
const BACKUP_PATH = path.join(OPENCLAW_ROOT, 'openclaw.json.bak');
const HISTORY_DIR = path.join(OPENCLAW_ROOT, 'openclaw.history');
const ORCHESTRATION_DIR = path.join(OPENCLAW_ROOT, 'packages', 'orchestration');

async function handler(request: NextRequest): Promise<NextResponse> {
    const requestId = crypto.randomUUID();
    try {
        // 1. Ensure history directory exists
        await fs.mkdir(HISTORY_DIR, { recursive: true });

        // 2. Backup existing config if it exists
        try {
            await fs.copyFile(CONFIG_PATH, BACKUP_PATH);
        } catch (e) {
            // Ignore if file doesn't exist
        }

        // 3. Generate new config using Python script
        // We use the Python script to ensure logic parity
        const generateConfig = () => new Promise<string>((resolve, reject) => {
            const pythonProcess = spawn('python', ['src/openclaw/config_generator.py', 'generate'], {
                cwd: ORCHESTRATION_DIR,
                env: { ...process.env, PYTHONPATH: 'src' }
            });

            let stdout = '';
            let stderr = '';

            pythonProcess.stdout.on('data', (data) => stdout += data);
            pythonProcess.stderr.on('data', (data) => stderr += data);

            pythonProcess.on('close', (code) => {
                if (code === 0) resolve(stdout);
                else reject(new Error(`Python process exited with code ${code}: ${stderr}`));
            });
        });

        await generateConfig();

        // 4. Verification & Hash calculation
        const generatedContent = await fs.readFile(CONFIG_PATH, 'utf-8');
        const hash = crypto.createHash('sha256').update(generatedContent).digest('hex');

        // 5. Save to history
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const historyPath = path.join(HISTORY_DIR, `openclaw.${timestamp}.${hash.substring(0, 8)}.json`);
        await fs.writeFile(historyPath, generatedContent);

        // 6. Record in audit log
        const db = getDb();
        db.prepare(`
      INSERT INTO audit_log (id, request_id, actor, action, target, after_json, diff_summary, status, config_hash)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
            crypto.randomUUID(),
            requestId,
            'user',
            'apply',
            'openclaw.json',
            generatedContent,
            'Applied staged configuration to openclaw.json',
            'success',
            hash
        );

        return NextResponse.json({
            success: true,
            requestId,
            hash,
            timestamp
        });
    } catch (error: any) {
        console.error('Error applying config:', error);

        // Log failure
        try {
            const db = getDb();
            db.prepare(`
        INSERT INTO audit_log (id, request_id, actor, action, target, status, message)
        VALUES (?, ?, ?, ?, ?, ?, ?)
      `).run(
                crypto.randomUUID(),
                requestId,
                'user',
                'apply',
                'openclaw.json',
                'failure',
                error.message || 'Unknown error during apply'
            );
        } catch (dbError) {
            console.error('Failed to log audit entry for failure:', dbError);
        }

        return NextResponse.json({ error: 'Failed to apply configuration', message: error.message }, { status: 500 });
    }
}

export const POST = withAuth(withWriteLock(handler));
