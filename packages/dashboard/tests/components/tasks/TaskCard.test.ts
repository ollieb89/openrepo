import { describe, it, expect } from 'vitest';
import { getTaskCardClassName } from '@/components/tasks/TaskCard';

describe('getTaskCardClassName', () => {
  it('includes ring-2 and ring-blue-400 when isSelected=true', () => {
    const cls = getTaskCardClassName(true);
    expect(cls).toContain('ring-2');
    expect(cls).toContain('ring-blue-400');
  });

  it('does NOT include ring-2 when isSelected=false', () => {
    const cls = getTaskCardClassName(false);
    expect(cls).not.toContain('ring-2');
  });

  it('includes border-gray-200 when isSelected=false', () => {
    const cls = getTaskCardClassName(false);
    expect(cls).toContain('border-gray-200');
  });

  it('defaults to false when prop is not passed (optional prop)', () => {
    // isSelected=false is the default; calling with false should match calling getTaskCardClassName()
    const defaultCls = getTaskCardClassName(false);
    expect(defaultCls).toContain('border-gray-200');
    expect(defaultCls).not.toContain('ring-2');
  });
});
