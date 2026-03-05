import { describe, it, expect } from 'vitest';
import { getExpandedIds } from '@/components/mission-control/TaskPulse';

describe('getExpandedIds', () => {
  it('test_expand_logic: normal click clears others and adds taskId', () => {
    const prev = new Set(['task-1', 'task-2']);
    const result = getExpandedIds(prev, 'task-3', false);
    expect(result.has('task-3')).toBe(true);
    expect(result.has('task-1')).toBe(false);
    expect(result.has('task-2')).toBe(false);
    expect(result.size).toBe(1);
  });

  it('test_expand_logic: second normal click on same id clears set', () => {
    const prev = new Set(['task-1']);
    const result = getExpandedIds(prev, 'task-1', false);
    expect(result.size).toBe(0);
    expect(result.has('task-1')).toBe(false);
  });

  it('test_expand_logic: shift-click toggles without clearing other expanded rows', () => {
    const prev = new Set(['task-1', 'task-2']);

    // Shift-add a new task
    const resultAdd = getExpandedIds(prev, 'task-3', true);
    expect(resultAdd.has('task-1')).toBe(true);
    expect(resultAdd.has('task-2')).toBe(true);
    expect(resultAdd.has('task-3')).toBe(true);

    // Shift-remove an existing task
    const resultRemove = getExpandedIds(prev, 'task-1', true);
    expect(resultRemove.has('task-1')).toBe(false);
    expect(resultRemove.has('task-2')).toBe(true);
  });
});
