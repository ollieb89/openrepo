import type { LogEntry } from '@/components/LogViewer';

const OVERLAP_WINDOW = 500;

function normalizeLine(line: string): string {
  // Normalize CRLF and trailing CR for comparison only (not mutation)
  return line.replace(/\r\n/g, '\n').replace(/\r$/, '');
  // TODO: strip ANSI codes here if logs contain terminal escape sequences
}

/**
 * Append entries from `supplemental` that are not already at the tail of `live`.
 *
 * Algorithm: find the largest k where the last k lines of `live` match the
 * first k lines of `supplemental` (by normalized content). Append supplemental[k:].
 *
 * Constrained to last OVERLAP_WINDOW lines to avoid O(n²) on large logs.
 * When no overlap is found and supplemental is large (>OVERLAP_WINDOW), appends
 * only the last OVERLAP_WINDOW lines with a synthetic divider to avoid doubling.
 */
export function suffixOverlapMerge(live: LogEntry[], supplemental: LogEntry[]): LogEntry[] {
  if (!supplemental.length) return live;

  const windowSize = Math.min(OVERLAP_WINDOW, live.length);
  const window = live.slice(-windowSize);

  // Find largest k where live[-k:] matches supplemental[0:k]
  let overlapK = 0;
  const maxK = Math.min(windowSize, supplemental.length);
  for (let k = maxK; k > 0; k--) {
    let match = true;
    for (let i = 0; i < k; i++) {
      const liveIdx = window.length - k + i;
      if (normalizeLine(window[liveIdx].line) !== normalizeLine(supplemental[i].line)) {
        match = false;
        break;
      }
    }
    if (match) {
      overlapK = k;
      break;
    }
  }

  const tail = supplemental.slice(overlapK);

  if (!overlapK && supplemental.length > OVERLAP_WINDOW) {
    // No overlap and large supplemental — avoid doubling the entire log
    const divider: LogEntry = {
      line: '\u2014 stored log (partial) \u2014',
      stream: 'stdout',
      timestamp: Date.now(),
    };
    return [...live, divider, ...supplemental.slice(-OVERLAP_WINDOW)];
  }

  return [...live, ...tail];
}
