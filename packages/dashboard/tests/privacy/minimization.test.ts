import { describe, expect, it } from 'vitest';
import { minimizePersistenceRecord } from '../../src/lib/privacy/minimization';

const FIXED_DATE = new Date('2026-02-24T00:00:00.000Z');

describe('privacy minimization', () => {
  it('rejects raw content fields by default', () => {
    expect(() =>
      minimizePersistenceRecord({
        sourceId: 'source-1',
        threadId: 'thread-1',
        connector: 'slack',
        entityType: 'message',
        body: 'sensitive raw message',
      })
    ).toThrow('Raw content field');
  });

  it('can strip raw content fields while preserving allowlisted metadata', () => {
    const result = minimizePersistenceRecord(
      {
        sourceId: 'source-1',
        threadId: 'thread-1',
        connector: 'slack',
        entityType: 'message',
        body: 'sensitive raw message',
        ignored: 'drop-me',
        provenance: {
          sourceLink: 'https://example.com/thread/1',
        },
      },
      {
        rawContentMode: 'strip',
        now: () => FIXED_DATE,
      }
    );

    expect(result).toEqual({
      sourceId: 'source-1',
      threadId: 'thread-1',
      timestamp: '2026-02-24T00:00:00.000Z',
      connector: 'slack',
      entityType: 'message',
      provenance: {
        sourceLink: 'https://example.com/thread/1',
        timestamp: '2026-02-24T00:00:00.000Z',
        connectorLabel: 'slack',
      },
    });
  });

  it('applies provenance defaults required for trust signals', () => {
    const result = minimizePersistenceRecord(
      {
        sourceId: 'src-77',
        connector: 'linear',
        entityType: 'issue',
      },
      { now: () => FIXED_DATE }
    );

    expect(result.provenance.sourceLink).toBe('openclaw://source/src-77');
    expect(result.provenance.timestamp).toBe('2026-02-24T00:00:00.000Z');
    expect(result.provenance.connectorLabel).toBe('linear');
  });

  it('rejects nested raw content keys', () => {
    expect(() =>
      minimizePersistenceRecord({
        sourceId: 'source-1',
        connector: 'slack',
        entityType: 'message',
        nested: {
          content: 'secret',
        },
      })
    ).toThrow('nested.content');
  });
});
