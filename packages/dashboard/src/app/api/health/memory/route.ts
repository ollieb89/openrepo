import { NextResponse } from 'next/server';

// Need to add getMemuConfig to openclaw.ts or just read it here
import fs from 'fs/promises';
import path from 'path';
import os from 'os';

const OPENCLAW_ROOT = process.env.OPENCLAW_ROOT || path.join(os.homedir(), '.openclaw');

async function getMemuUrl() {
  try {
    const raw = await fs.readFile(path.join(OPENCLAW_ROOT, 'openclaw.json'), 'utf-8');
    const config = JSON.parse(raw);
    return config.memory?.memu_api_url || 'http://localhost:18791';
  } catch {
    return 'http://localhost:18791';
  }
}

export async function GET() {
  try {
    const baseUrl = await getMemuUrl();
    const url = `${baseUrl}/health`;

    const res = await fetch(url, { signal: AbortSignal.timeout(2000) });
    if (res.ok) {
      return NextResponse.json({ status: 'ok' });
    }
    return NextResponse.json({ status: 'unhealthy' }, { status: 503 });
  } catch (error) {
    return NextResponse.json({ status: 'unhealthy', error: (error as Error).message }, { status: 503 });
  }
}
