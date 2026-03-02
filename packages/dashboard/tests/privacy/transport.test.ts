import { describe, expect, it, vi } from 'vitest';
import { createRemoteTransport } from '../../src/lib/privacy/transport';

describe('remote transport', () => {
  it('rejects insecure http endpoints', () => {
    expect(() =>
      createRemoteTransport({ endpoint: 'http://example.com/infer' })
    ).toThrow('HTTPS');
  });

  it('rejects disabled TLS certificate verification', () => {
    expect(() =>
      createRemoteTransport({
        endpoint: 'https://example.com/infer',
        tls: { rejectUnauthorized: false },
      })
    ).toThrow('Insecure TLS');
  });

  it('allows secure https transport and performs requests', async () => {
    const originalFetch = globalThis.fetch;
    const fetchMock = vi.fn(async () =>
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      })
    );
    globalThis.fetch = fetchMock as typeof fetch;

    try {
      const transport = createRemoteTransport({
        endpoint: 'https://example.com/infer',
      });

      const result = await transport.invoke({ message: 'hello' });
      expect(result).toEqual({ ok: true });
      expect(fetchMock).toHaveBeenCalledTimes(1);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });
});
