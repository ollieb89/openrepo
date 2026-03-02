import { NextRequest, NextResponse } from 'next/server';
import { streamContainerLogs, listSwarmContainers } from '@/lib/docker';
import { validateToken, isAuthRequired, createUnauthorizedResponse } from '@/lib/auth';
import { withAuth } from '@/lib/auth-middleware';

export async function GET(request: NextRequest) {
  // Check authentication
  if (isAuthRequired()) {
    const authHeader = request.headers.get('Authorization');
    const customTokenHeader = request.headers.get('X-OpenClaw-Token');
    const queryToken = new URL(request.url).searchParams.get('_token');

    if (!validateToken(authHeader || undefined, customTokenHeader || undefined, queryToken || undefined)) {
      return createUnauthorizedResponse();
    }
  }

  const { searchParams } = new URL(request.url);
  const containerId = searchParams.get('containerId');

  if (!containerId) {
    return new Response('Container ID is required', { status: 400 });
  }

  // Set up Server-Sent Events
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    start(controller) {
      const abortController = new AbortController();

      async function streamLogs() {
        try {
          await streamContainerLogs(
            containerId!, // Type assertion since we checked above
            (logLine) => {
              const data = `data: ${JSON.stringify({ line: logLine, timestamp: Date.now() })}\n\n`;
              controller.enqueue(encoder.encode(data));
            },
            abortController.signal
          );
        } catch (error) {
          console.error('Stream error:', error);
          controller.close();
        }
      }

      streamLogs();

      // Clean up on disconnect
      request.signal.addEventListener('abort', () => {
        abortController.abort();
        controller.close();
      });
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  });
}

async function postHandler(request: NextRequest) {
  try {
    const containers = await listSwarmContainers();
    
    return NextResponse.json({
      containers: containers.map(c => ({
        id: c.Id,
        name: c.Names[0],
        status: c.Status,
        image: c.Image,
        created: c.Created,
        labels: c.Labels,
      })),
    });
  } catch (error) {
    console.error('Error listing containers:', error);
    return NextResponse.json(
      { error: 'Failed to list containers' },
      { status: 500 }
    );
  }
}

export const POST = withAuth(postHandler);
