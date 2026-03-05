import { NextRequest, NextResponse } from 'next/server';
import { getDb } from '@/lib/db';
import { withAuth } from '@/lib/auth-middleware';
import { readOpenClawConfig } from '@/lib/openclaw';

async function handler(request: NextRequest): Promise<NextResponse> {
    try {
        const db = getDb();
        const rows = db.prepare('SELECT key, value FROM gateway_settings').all() as { key: string; value: string }[];

        const stagedGateway: Record<string, any> = {};
        for (const row of rows) {
            try {
                stagedGateway[row.key] = JSON.parse(row.value);
            } catch {
                stagedGateway[row.key] = row.value;
            }
        }

        // Load actual config from openclaw.json for comparison
        const liveConfig = await readOpenClawConfig();
        const liveGateway = (liveConfig.gateway as Record<string, any>) || {};

        return NextResponse.json({
            staged: stagedGateway,
            live: liveGateway,
        });
    } catch (error) {
        console.error('Error fetching staged config:', error);
        return NextResponse.json({ error: 'Failed to fetch staged config' }, { status: 500 });
    }
}

export const GET = withAuth(handler);
