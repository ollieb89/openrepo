import { NextResponse } from 'next/server';
import { runIncrementalSync } from '@/lib/sync/engine';
import { withAuth } from '@/lib/auth-middleware';

async function handler(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const result = await runIncrementalSync({ connectorId: id });
    return NextResponse.json({ ok: true, result });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to run sync';
    const status = message.includes('not found') ? 404 : 500;
    return NextResponse.json({ ok: false, error: message }, { status });
  }
}

export const POST = withAuth(handler);
