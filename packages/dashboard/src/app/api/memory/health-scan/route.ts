import { NextRequest, NextResponse } from 'next/server';
import { readOpenClawConfig } from '@/lib/openclaw';
import { withAuth } from '@/lib/auth-middleware';

async function getMemuUrl(): Promise<string> {
  const config = await readOpenClawConfig();
  const memory = config.memory as Record<string, string> | undefined;
  return memory?.memu_api_url ?? 'http://localhost:18791';
}

async function handler(request: NextRequest) {
  try {
    const memuUrl = await getMemuUrl();
    const body = await request.json();
    const res = await fetch(`${memuUrl}/memories/health-scan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      return NextResponse.json({ error: 'Health scan failed' }, { status: res.status });
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error running health scan:', error);
    return NextResponse.json({ error: 'Failed to run health scan' }, { status: 500 });
  }
}

export const POST = withAuth(handler);
