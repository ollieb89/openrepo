import { describe, it, expect } from 'vitest';
import { filterPipelines } from '@/app/api/pipeline/route';

// Minimal PipelineItem stub for testing the pure filter function
const makePipeline = (taskId: string) => ({
  taskId,
  projectId: 'test-project',
  stages: [],
  status: 'pending' as const,
});

const samplePipelines = Array.from({ length: 25 }, (_, i) =>
  makePipeline(`task-${i + 1}`)
);

describe('filterPipelines', () => {
  it('test_taskid_filter_returns_single: returns array of length 1 with matching taskId', () => {
    const result = filterPipelines(samplePipelines as any, 'task-5');
    expect(result).toHaveLength(1);
    expect(result[0].taskId).toBe('task-5');
  });

  it('test_no_filter_returns_all_up_to_20: returns up to 20 items when taskId is undefined', () => {
    const result = filterPipelines(samplePipelines as any, undefined);
    expect(result).toHaveLength(20);
  });
});
