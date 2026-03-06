import { NextRequest, NextResponse } from 'next/server';
import { parseIntent } from '@/lib/sync/intent';
import { searchContext } from '@/lib/sync/vector-store';
import { synthesizeTimeline } from '@/lib/sync/synthesis';
import { generateEmbedding } from '@/lib/ollama';
import { withAuth } from '@/lib/auth-middleware';

export const dynamic = 'force-dynamic';

async function handler(req: NextRequest) {
  try {
    const { query, activeProjectId } = await req.json();

    // 1. Parse Intent
    const intent = parseIntent(query, activeProjectId);

    // 2. Generate Query Embedding
    const queryEmbedding = await generateEmbedding(intent.query);

    // 3. Search Context
    const records = await searchContext(intent, queryEmbedding);

    // 4. Synthesize
    const { stream, confidence, context } = await synthesizeTimeline(query, records);

    if (confidence === 'low') {
      return NextResponse.json({
        confidence: 'low',
        suggestions: context.slice(0, 3).map(r => ({
          id: r.id,
          content: r.content.substring(0, 100) + '...',
          type: r.entity_type
        }))
      });
    }

    // 5. Stream response
    const encoder = new TextEncoder();
    const readableStream = new ReadableStream({
      async start(controller) {
        // Send initial metadata
        const metadata = JSON.stringify({ 
          type: 'metadata', 
          context: context.map(r => ({ id: r.id, type: r.entity_type })) 
        });
        controller.enqueue(encoder.encode(metadata + '\n'));

        for await (const token of stream) {
          const chunk = JSON.stringify({ type: 'token', token });
          controller.enqueue(encoder.encode(chunk + '\n'));
        }
        controller.close();
      }
    });

    return new Response(readableStream, {
      headers: {
        'Content-Type': 'application/x-ndjson',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });

  } catch (error) {
    console.error('[CatchUp] API Error:', error);
    const msg = error instanceof Error ? error.message : String(error);
    // Ollama / embedding service unavailable — surface as 503 so callers can retry
    if (
      msg.includes('not available') ||
      msg.includes('ECONNREFUSED') ||
      msg.includes('fetch failed')
    ) {
      return NextResponse.json({ error: 'engine_offline' }, { status: 503 });
    }
    return NextResponse.json({ error: 'Failed to process catch-up query' }, { status: 500 });
  }
}

export const POST = withAuth(handler);
