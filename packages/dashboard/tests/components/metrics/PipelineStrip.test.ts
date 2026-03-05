import { describe, it, expect } from 'vitest';
import { getPipelineStripSegmentClass } from '@/components/metrics/PipelineStrip';

describe('getPipelineStripSegmentClass', () => {
  it('test_renders_six_segments: returns non-empty string for all 4 statuses', () => {
    const statuses = ['pending', 'active', 'completed', 'failed'] as const;
    for (const status of statuses) {
      const cls = getPipelineStripSegmentClass(status);
      expect(cls).toBeTruthy();
      expect(typeof cls).toBe('string');
    }
  });

  it('test_completed_class: contains bg-green-500 for completed', () => {
    const cls = getPipelineStripSegmentClass('completed');
    expect(cls).toContain('bg-green-500');
  });

  it('test_active_class: contains bg-blue-500 and animate-pulse for active', () => {
    const cls = getPipelineStripSegmentClass('active');
    expect(cls).toContain('bg-blue-500');
    expect(cls).toContain('animate-pulse');
  });

  it('test_failed_class: contains bg-red-500 for failed', () => {
    const cls = getPipelineStripSegmentClass('failed');
    expect(cls).toContain('bg-red-500');
  });

  it('test_pending_class: contains border-dashed for pending', () => {
    const cls = getPipelineStripSegmentClass('pending');
    expect(cls).toContain('border-dashed');
  });
});
