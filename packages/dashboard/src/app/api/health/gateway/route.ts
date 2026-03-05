import { NextResponse } from 'next/server';
import { readOpenClawConfig } from '@/lib/openclaw';

export async function GET() {
  try {
    const config = await readOpenClawConfig();
    const gatewayPort = (config.gateway as any)?.port || 18789;
    const url = `http://localhost:${gatewayPort}/health`;

    const res = await fetch(url, { signal: AbortSignal.timeout(2000) });
    
    if (res.ok) {
      return NextResponse.json({ status: 'ok', port: gatewayPort });
    }
    
    // Check if it's the UI assets issue
    const body = await res.text().catch(() => '');
    if (body.includes('ui:build') || body.includes('Control UI assets')) {
      return NextResponse.json({ 
        status: 'needs_ui_build', 
        port: gatewayPort,
        message: 'Gateway running but Control UI assets not built. Run: pnpm ui:build',
        hint: 'API functionality still works - only the Control UI is unavailable'
      }, { status: 200 }); // Return 200 so UI doesn't show error
    }
    
    return NextResponse.json({ status: 'unhealthy', port: gatewayPort }, { status: 503 });
  } catch (error) {
    return NextResponse.json({ 
      status: 'offline', 
      error: (error as Error).message,
      hint: 'Gateway may not be running. Check: lsof -i :18789'
    }, { status: 503 });
  }
}
