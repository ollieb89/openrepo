import { NextRequest, NextResponse } from 'next/server';
import { getDb } from '@/lib/db';
import { withAuth } from '@/lib/auth-middleware';
import { withWriteLock } from '@/lib/safety';
import { z } from 'zod';
import { randomUUID } from 'node:crypto';

const GatewayPatchSchema = z.record(z.any());

async function handler(request: NextRequest): Promise<NextResponse> {
    try {
        const body = await request.json();
        const validated = GatewayPatchSchema.parse(body);
        const db = getDb();

        const requestId = randomUUID();

        // We'll use a transaction for safety
        const update = db.transaction((patch: Record<string, any>) => {
            for (const [key, value] of Object.entries(patch)) {
                const valueStr = typeof value === 'object' ? JSON.stringify(value) : String(value);

                // Get old value for audit log
                const oldRow = db.prepare('SELECT value FROM gateway_settings WHERE key = ?').get(key) as { value: string } | undefined;

                db.prepare('INSERT OR REPLACE INTO gateway_settings (key, value) VALUES (?, ?)')
                    .run(key, valueStr);

                // Record in audit log
                db.prepare(`
          INSERT INTO audit_log (id, request_id, actor, action, target, before_json, after_json, diff_summary, status)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        `).run(
                    randomUUID(),
                    requestId,
                    'user', // TODO: get from auth
                    'update_staged',
                    `gateway:${key}`,
                    oldRow?.value || null,
                    valueStr,
                    `Updated gateway setting: ${key}`,
                    'success'
                );
            }
        });

        update(validated);

        return NextResponse.json({ success: true, requestId });
    } catch (error) {
        if (error instanceof z.ZodError) {
            return NextResponse.json({ error: 'Invalid payload', details: error.errors }, { status: 400 });
        }
        console.error('Error updating staged config:', error);
        return NextResponse.json({ error: 'Failed to update staged config' }, { status: 500 });
    }
}

export const PATCH = withAuth(withWriteLock(handler));
