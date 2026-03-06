import { NextRequest, NextResponse } from 'next/server';
import { ringBuffer } from '@/lib/event-ring-buffer';
import { withAuth } from '@/lib/auth-middleware';

export const dynamic = 'force-dynamic';

export interface LiveEventLatest {
  id: number;
  type: string;
  project_id?: string;
  task_id?: string;
  message?: string;
  ts: number;
}

async function handler(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const rawLimit = parseInt(searchParams.get('limit') ?? '50', 10);
  const limit = Number.isFinite(rawLimit) ? Math.min(200, Math.max(1, rawLimit)) : 50;

  const slice = ringBuffer.slice(-limit);
  const events: LiveEventLatest[] = [];

  for (const entry of slice) {
    try {
      const parsed = JSON.parse(entry.data);
      events.push({
        id: entry.id,
        type: parsed.type ?? 'unknown',
        project_id: parsed.project_id,
        task_id: parsed.task_id,
        message: parsed.message ?? parsed.description,
        // Use original event timestamp if present; fall back to approximate server-receipt time
        ts: typeof parsed.ts === 'number' ? parsed.ts : Date.now(),
      });
    } catch {
      // skip malformed entries
    }
  }

  return NextResponse.json({ events });
}

export const GET = withAuth(handler);
