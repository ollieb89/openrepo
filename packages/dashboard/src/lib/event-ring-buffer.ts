/**
 * Shared in-process ring buffer for SSE event replay.
 * Imported by both /api/events (SSE writer) and /api/events/latest (REST reader).
 * Module-scope singleton — same instance as long as Next.js keeps the module loaded.
 */
export const RING_BUFFER_SIZE = 100;

export const ringBuffer: { id: number; data: string }[] = [];
let globalEventId = 0;

export function addToRingBuffer(data: string): number {
  const id = ++globalEventId;
  ringBuffer.push({ id, data });
  if (ringBuffer.length > RING_BUFFER_SIZE) {
    ringBuffer.shift();
  }
  return id;
}
