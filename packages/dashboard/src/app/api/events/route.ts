import { NextRequest } from 'next/server';
import { connect } from 'node:net';
import { join } from 'node:path';
import { homedir } from 'node:os';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  const ocRoot = process.env.OPENCLAW_ROOT || join(homedir(), '.openclaw');
  const socketPath = process.env.OPENCLAW_EVENTS_SOCK || join(ocRoot, 'run', 'events.sock');
  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    start(controller) {
      const client = connect(socketPath);

      client.on('connect', () => {
        console.log(`[SSE Bridge] Connected to ${socketPath}`);
        controller.enqueue(encoder.encode('event: connected\ndata: {"status":"ok"}\n\n'));
      });

      client.on('data', (data) => {
        const lines = data.toString().split('\n').filter(Boolean);
        for (const line of lines) {
          controller.enqueue(encoder.encode(`event: message\ndata: ${line}\n\n`));
        }
      });

      client.on('error', (err) => {
        console.error('[SSE Bridge] Socket error:', err.message);
        controller.enqueue(encoder.encode(`event: error\ndata: {"message":"${err.message}"}\n\n`));
        // Don't close yet, let it try to reconnect or handle gracefully
      });

      client.on('close', () => {
        console.log('[SSE Bridge] Socket closed');
        try {
          controller.close();
        } catch (e) {
          // Ignore if already closed
        }
      });

      // Cleanup on request cancel
      request.signal.addEventListener('abort', () => {
        console.log('[SSE Bridge] Client aborted, closing socket');
        client.destroy();
      });
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      'Connection': 'keep-alive',
    },
  });
}
