/**
 * Docker API Client Wrapper
 *
 * Provides container discovery and log streaming with automatic redaction.
 * Handles Docker multiplexed stream format and graceful error handling.
 */

import Docker from 'dockerode';
import { redactSensitiveData } from './redaction';

// Docker client initialization with socket path override support
const docker = new Docker({
  socketPath: process.env.DOCKER_SOCKET || '/var/run/docker.sock',
});

// Flag to track if Docker socket is available
let dockerAvailable = true;

/**
 * Check if Docker is available, with graceful fallback
 */
async function checkDockerAvailability(): Promise<boolean> {
  if (!dockerAvailable) return false;

  try {
    await docker.ping();
    return true;
  } catch (error) {
    console.warn('[Docker] Docker socket not available:', error);
    dockerAvailable = false;
    return false;
  }
}

/**
 * Find container by label filter
 */
export async function getContainerByLabel(
  label: string,
  value: string
): Promise<Docker.ContainerInfo | null> {
  if (!(await checkDockerAvailability())) return null;

  try {
    const containers = await docker.listContainers({
      filters: {
        label: [`${label}=${value}`],
      },
    });

    return containers[0] || null;
  } catch (error) {
    console.error('[Docker] Error finding container by label:', error);
    return null;
  }
}

/**
 * Find container by name pattern (partial match)
 */
export async function getContainerByName(
  name: string
): Promise<Docker.ContainerInfo | null> {
  if (!(await checkDockerAvailability())) return null;

  try {
    const containers = await docker.listContainers();

    // Look for exact match first, then partial match
    const exactMatch = containers.find((c) =>
      c.Names.some((n) => n === `/${name}` || n === name)
    );
    if (exactMatch) return exactMatch;

    // Partial match (contains)
    const partialMatch = containers.find((c) =>
      c.Names.some((n) => n.includes(name) || n.includes(name.replace(/-/g, '_')))
    );
    return partialMatch || null;
  } catch (error) {
    console.error('[Docker] Error finding container by name:', error);
    return null;
  }
}

/**
 * List all OpenClaw managed containers
 */
export async function listSwarmContainers(): Promise<Docker.ContainerInfo[]> {
  if (!(await checkDockerAvailability())) return [];

  try {
    // Label-only filter: openclaw.managed=true is the single source of truth
    // spawn.py now sets this label on all managed containers (Phase 9: INT-03)
    return await docker.listContainers({
      filters: {
        label: ['openclaw.managed=true'],
      },
    });
  } catch (error) {
    console.error('[Docker] Error listing swarm containers:', error);
    return [];
  }
}

/**
 * Parse Docker multiplexed stream data into individual log lines.
 * Docker multiplexed format: 8-byte header [stream type, padding, length] + payload
 */
function parseDockerStreamChunk(chunk: Buffer): string[] {
  const lines: string[] = [];
  let offset = 0;

  while (offset < chunk.length) {
    // Check if we have enough bytes for header
    if (offset + 8 > chunk.length) break;

    // Parse header: [stream type, padding (3 bytes), length (4 bytes)]
    // stream type: 0 = stdin, 1 = stdout, 2 = stderr
    const length = chunk.readUInt32BE(offset + 4);

    // Check if we have enough bytes for payload
    if (offset + 8 + length > chunk.length) break;

    // Extract payload
    const payload = chunk.slice(offset + 8, offset + 8 + length);
    const line = payload.toString('utf8').trim();
    if (line) {
      lines.push(line);
    }

    offset += 8 + length;
  }

  // If no structured data was parsed, treat entire chunk as text
  if (lines.length === 0 && chunk.length > 0) {
    const text = chunk.toString('utf8').trim();
    if (text) {
      // Split by newlines in case multiple lines in raw text
      text.split('\n').forEach((line) => {
        const trimmed = line.trim();
        if (trimmed) lines.push(trimmed);
      });
    }
  }

  return lines;
}

class DockerLogStreamParser {
  private buffer: Buffer = Buffer.alloc(0);
  private textRemainder = '';

  private looksLikeMultiplexedHeader(buf: Buffer, startOffset: number): boolean {
    if (startOffset + 8 > buf.length) return false;
    const streamType = buf[startOffset];
    return (
      (streamType === 0 || streamType === 1 || streamType === 2) &&
      buf[startOffset + 1] === 0 &&
      buf[startOffset + 2] === 0 &&
      buf[startOffset + 3] === 0
    );
  }

  push(chunk: Buffer): string[] {
    if (!chunk || chunk.length === 0) return [];
    this.buffer = this.buffer.length > 0 ? Buffer.concat([this.buffer, chunk]) : chunk;

    const out: string[] = [];

    // If it doesn't look multiplexed, treat as plain text stream.
    if (!this.looksLikeMultiplexedHeader(this.buffer, 0)) {
      const text = this.buffer.toString('utf8');
      this.buffer = Buffer.alloc(0);

      const combined = this.textRemainder + text;
      const parts = combined.split('\n');
      this.textRemainder = parts.pop() ?? '';

      for (const part of parts) {
        const trimmed = part.trim();
        if (trimmed) out.push(trimmed);
      }

      return out;
    }

    let offset = 0;
    while (true) {
      if (offset + 8 > this.buffer.length) break;
      if (!this.looksLikeMultiplexedHeader(this.buffer, offset)) break;

      const length = this.buffer.readUInt32BE(offset + 4);
      const frameEnd = offset + 8 + length;
      if (frameEnd > this.buffer.length) break;

      const payload = this.buffer.slice(offset + 8, frameEnd);
      const text = payload.toString('utf8');
      const combined = this.textRemainder + text;
      const parts = combined.split('\n');
      this.textRemainder = parts.pop() ?? '';

      for (const part of parts) {
        const trimmed = part.trim();
        if (trimmed) out.push(trimmed);
      }

      offset = frameEnd;
    }

    // Preserve remainder bytes for next chunk.
    this.buffer = offset > 0 ? this.buffer.slice(offset) : this.buffer;

    return out;
  }
}

/**
 * Stream container logs with automatic redaction.
 *
 * @param containerId - Docker container ID
 * @param onLog - Callback for each log line (already redacted)
 * @param signal - AbortSignal for cleanup
 * @param options - Optional settings (tail lines)
 */
export async function streamContainerLogs(
  containerId: string,
  onLog: (line: string) => void,
  signal: AbortSignal,
  options?: { tail?: number }
): Promise<void> {
  if (!(await checkDockerAvailability())) {
    throw new Error('Docker socket not available');
  }

  const container = docker.getContainer(containerId);

  try {
    const stream = await container.logs({
      follow: true,
      stdout: true,
      stderr: true,
      timestamps: true,
      tail: options?.tail || 100,
    });

    const parser = new DockerLogStreamParser();

    // Handle abort signal
    const cleanup = () => {
      try {
        // Destroy the stream to stop log streaming
        (stream as unknown as { destroy?: () => void }).destroy?.();
      } catch {
        // Ignore cleanup errors
      }
    };

    signal.addEventListener('abort', cleanup);

    // Process stream data
    stream.on('data', (chunk: Buffer) => {
      if (signal.aborted) return;

      try {
        const lines = parser.push(chunk);

        for (const line of lines) {
          // Apply redaction before sending to client
          const redactedLine = redactSensitiveData(line);
          onLog(redactedLine);
        }
      } catch (error) {
        console.error('[Docker] Error parsing log chunk:', error);
      }
    });

    stream.on('error', (error: Error) => {
      console.error('[Docker] Stream error:', error);
      cleanup();
    });

    stream.on('end', () => {
      console.log('[Docker] Log stream ended for container:', containerId);
    });

    // Wait for abort signal
    await new Promise<void>((resolve) => {
      signal.addEventListener('abort', () => {
        resolve();
      });
    });
  } catch (error) {
    console.error('[Docker] Error streaming container logs:', error);
    throw error;
  }
}

export { docker };
