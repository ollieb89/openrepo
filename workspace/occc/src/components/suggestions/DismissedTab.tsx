'use client';

import type { Suggestion } from '@/lib/types/suggestions';

interface DismissedTabProps {
  suggestions: Suggestion[];
}

function formatTimestamp(ts: number | null): string {
  if (!ts) return '';
  try {
    const date = new Date(ts * 1000);
    return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
  } catch {
    return '';
  }
}

export default function DismissedTab({ suggestions }: DismissedTabProps) {
  if (suggestions.length === 0) {
    return (
      <p className="text-gray-400 dark:text-gray-500 text-sm py-8 text-center">No dismissed suggestions.</p>
    );
  }

  return (
    <ul className="space-y-2">
      {suggestions.map(s => (
        <li key={s.id} className="text-sm text-gray-500 dark:text-gray-400 flex flex-wrap gap-1">
          <span>{s.pattern_description}</span>
          <span className="text-gray-300 dark:text-gray-600">—</span>
          <span>{s.rejection_reason ?? 'No reason provided'}</span>
          {s.rejected_at && (
            <>
              <span className="text-gray-300 dark:text-gray-600">—</span>
              <span>{formatTimestamp(s.rejected_at)}</span>
            </>
          )}
        </li>
      ))}
    </ul>
  );
}
