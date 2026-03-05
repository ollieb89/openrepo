import { NextResponse } from 'next/server';
import { withAuth } from '@/lib/auth-middleware';
import { readOpenClawConfig } from '@/lib/openclaw';
import path from 'path';
import os from 'os';

const OPENCLAW_ROOT = process.env.OPENCLAW_ROOT || path.join(os.homedir(), '.openclaw');

async function checkGatewayHealth(): Promise<{ 
  healthy: boolean; 
  running?: boolean;
  needsUiBuild?: boolean;
  latency?: number; 
  error?: string 
}> {
  const start = Date.now();
  try {
    const config = await readOpenClawConfig();
    const gatewayPort = (config.gateway as any)?.port || 18789;
    const url = `http://localhost:${gatewayPort}/health`;

    const res = await fetch(url, { signal: AbortSignal.timeout(2000) });
    const latency = Date.now() - start;
    
    if (res.ok) {
      return { healthy: true, running: true, latency };
    }
    
    // Check if it's the UI assets issue (503 with specific message)
    if (res.status === 503) {
      const body = await res.text();
      if (body.includes('ui:build') || body.includes('Control UI assets')) {
        return { 
          healthy: false, 
          running: true,
          needsUiBuild: true,
          latency, 
          error: 'Control UI assets not built. Run: pnpm ui:build' 
        };
      }
    }
    
    return { healthy: false, running: true, latency, error: `HTTP ${res.status}` };
  } catch (error) {
    return { healthy: false, running: false, error: (error as Error).message };
  }
}

async function checkMemoryHealth(): Promise<{ healthy: boolean; latency?: number; error?: string }> {
  const start = Date.now();
  try {
    let baseUrl = 'http://localhost:18791';
    
    try {
      const raw = await fetch(`file://${OPENCLAW_ROOT}/openclaw.json`).then(r => r.text()).catch(() => '{}');
      const config = JSON.parse(raw);
      baseUrl = config.memory?.memu_api_url || baseUrl;
    } catch {
      // Use default
    }

    const res = await fetch(`${baseUrl}/health`, { signal: AbortSignal.timeout(2000) });
    const latency = Date.now() - start;
    
    if (res.ok) {
      return { healthy: true, latency };
    }
    return { healthy: false, latency, error: `HTTP ${res.status}` };
  } catch (error) {
    return { healthy: false, error: (error as Error).message };
  }
}

async function checkEventBridge(): Promise<{ healthy: boolean; error?: string }> {
  try {
    const socketPath = process.env.OPENCLAW_EVENTS_SOCK || path.join(OPENCLAW_ROOT, 'run', 'events.sock');
    const fs = await import('fs/promises');
    
    try {
      await fs.access(socketPath);
      return { healthy: true };
    } catch {
      return { healthy: false, error: 'Socket not found' };
    }
  } catch (error) {
    return { healthy: false, error: (error as Error).message };
  }
}

async function handler() {
  const startTime = Date.now();
  
  const [gateway, memory, eventBridge] = await Promise.all([
    checkGatewayHealth(),
    checkMemoryHealth(),
    checkEventBridge(),
  ]);

  const allHealthy = gateway.healthy && memory.healthy && eventBridge.healthy;
  const gatewayStatus = gateway.healthy ? 'healthy' : 
                        gateway.needsUiBuild ? 'needs_ui_build' : 
                        gateway.running ? 'unhealthy' : 'offline';
  
  const response = {
    status: allHealthy ? 'healthy' : 'degraded',
    timestamp: new Date().toISOString(),
    latency_ms: Date.now() - startTime,
    services: {
      gateway: {
        status: gatewayStatus,
        running: gateway.running,
        needs_ui_build: gateway.needsUiBuild,
        latency_ms: gateway.latency,
        error: gateway.error,
      },
      memory: {
        status: memory.healthy ? 'healthy' : 'unhealthy',
        latency_ms: memory.latency,
        error: memory.error,
      },
      event_bridge: {
        status: eventBridge.healthy ? 'healthy' : 'unhealthy',
        error: eventBridge.error,
      },
    },
  };

  return NextResponse.json(response, {
    status: allHealthy ? 200 : 200, // Return 200 even if degraded, for UI to show status
  });
}

export const GET = withAuth(handler);
