import { runIncrementalSync } from '@/lib/sync/engine';

export async function POST(
  _request: Request,
  { params }: { params: { id: string } }
) {
  try {
    const result = await runIncrementalSync({ connectorId: params.id });
    return Response.json({ ok: true, result });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to run sync';
    const status = message.includes('not found') ? 404 : 500;
    return Response.json({ ok: false, error: message }, { status });
  }
}
