import { NextRequest } from 'next/server';
import { connectSlackWorkspace, ensureSlackAdapterRegistered } from '@/lib/connectors/slack';

interface ConnectSlackPayload {
  code?: string;
  redirectUri?: string;
  firstSyncWindowDays?: number;
}

export async function POST(request: NextRequest) {
  try {
    ensureSlackAdapterRegistered();

    const body = (await request.json()) as ConnectSlackPayload;
    if (!body.code || !body.redirectUri) {
      return Response.json({ ok: false, error: 'code and redirectUri are required' }, { status: 400 });
    }

    const connector = await connectSlackWorkspace({
      code: body.code,
      redirectUri: body.redirectUri,
      firstSyncWindowDays: body.firstSyncWindowDays,
    });

    return Response.json({ ok: true, connector });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Slack OAuth failed';
    const status = (error as { status?: number })?.status || 500;
    return Response.json({ ok: false, error: message }, { status });
  }
}
