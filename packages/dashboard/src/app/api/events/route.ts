import { NextRequest } from 'next/server';
import { connect } from 'node:net';
import { join } from 'node:path';
import { homedir } from 'node:os';

export const dynamic = 'force-dynamic';

// In-memory ring buffer for SSE reconnection replay (last 100 events)
const RING_BUFFER_SIZE = 100;
const ringBuffer: { id: number; data: string }[] = [];
let globalEventId = 0;

function addToRingBuffer(data: string): number {
  const id = ++globalEventId;
  ringBuffer.push({ id, data });
  if (ringBuffer.length > RING_BUFFER_SIZE) {
    ringBuffer.shift();
  }
  return id;
}

export async function GET(request: NextRequest) {
  const ocRoot = process.env.OPENCLAW_ROOT || join(homedir(), '.openclaw');
  const socketPath = process.env.OPENCLAW_EVENTS_SOCK || join(ocRoot, 'run', 'events.sock');
  const encoder = new TextEncoder();

  // Last-Event-ID for reconnection replay
  const lastEventIdHeader = request.headers.get('Last-Event-ID');
  const lastEventId = lastEventIdHeader ? parseInt(lastEventIdHeader, 10) : null;

  const stream = new ReadableStream({
    start(controller) {
      let heartbeatInterval: ReturnType<typeof setInterval> | null = null;

      // Replay buffered events if client is reconnecting
      if (lastEventId !== null && !isNaN(lastEventId)) {
        const missed = ringBuffer.filter(e => e.id > lastEventId);
        for (const e of missed) {
          controller.enqueue(encoder.encode(`id: ${e.id}\nevent: message\ndata: ${e.data}\n\n`));
        }
      }

      const client = connect(socketPath);

      client.on('connect', () => {
        console.log(`[SSE Bridge] Connected to ${socketPath}`);
        controller.enqueue(encoder.encode('event: connected\ndata: {"status":"ok"}\n\n'));

        // Start 30-second heartbeat ping interval
        heartbeatInterval = setInterval(() => {
          try {
            controller.enqueue(encoder.encode(': ping\n\n'));
          } catch (e) {
            // Controller closed — clean up
            if (heartbeatInterval) {
              clearInterval(heartbeatInterval);
              heartbeatInterval = null;
            }
          }
        }, 30_000);
      });

      client.on('data', (data) => {
        const lines = data.toString().split('\n').filter(Boolean);
        for (const line of lines) {
          try {
            const parsed = JSON.parse(line);
            if (parsed.type === 'heartbeat') {
              // Forward Python-side heartbeat as SSE comment to avoid polluting event stream
              controller.enqueue(encoder.encode(': ping\n\n'));
              continue;
            }
          } catch (e) {
            // Not JSON — forward as-is
          }
          const id = addToRingBuffer(line);
          controller.enqueue(encoder.encode(`id: ${id}\nevent: message\ndata: ${line}\n\n`));
        }
      });

      client.on('error', (err) => {
        console.error('[SSE Bridge] Socket error:', err.message);
        controller.enqueue(encoder.encode(`event: error\ndata: {"message":"${err.message}"}\n\n`));
        // Don't close yet, let it try to reconnect or handle gracefully
      });

      client.on('close', () => {
        console.log('[SSE Bridge] Socket closed');
        if (heartbeatInterval) {
          clearInterval(heartbeatInterval);
          heartbeatInterval = null;
        }
        try {
          controller.close();
        } catch (e) {
          // Ignore if already closed
        }
      });

      // Cleanup on request cancel
      request.signal.addEventListener('abort', () => {
        console.log('[SSE Bridge] Client aborted, closing socket');
        if (heartbeatInterval) {
          clearInterval(heartbeatInterval);
          heartbeatInterval = null;
        }
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
