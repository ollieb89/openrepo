'use client';

export interface HealthFlag {
  memory_id: string;
  flag_type: 'stale' | 'conflict';
  score: number;
  recommendation: string;
  conflict_with?: string;
}

interface HealthTabProps {
  flags: Map<string, HealthFlag>;
  onRunScan: () => void;
  scanRunning: boolean;
  onOpenConflict: (flag: HealthFlag) => void;
  onDismissFlag: (memoryId: string) => void;
  onOpenSettings: () => void;
}

const pillClass = 'inline-block rounded-full px-2 py-0.5 text-xs font-medium';

function FlagTypeBadge({ flagType }: { flagType: 'stale' | 'conflict' }) {
  if (flagType === 'stale') {
    return (
      <span className={`${pillClass} bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300`}>
        stale
      </span>
    );
  }
  return (
    <span className={`${pillClass} bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300`}>
      conflict
    </span>
  );
}

export default function HealthTab({
  flags,
  onRunScan,
  scanRunning,
  onOpenConflict,
  onDismissFlag,
  onOpenSettings,
}: HealthTabProps) {
  const flagArray = Array.from(flags.values()).sort((a, b) => b.score - a.score);
  const staleCount = flagArray.filter(f => f.flag_type === 'stale').length;
  const conflictCount = flagArray.filter(f => f.flag_type === 'conflict').length;

  return (
    <div className="space-y-4">
      {/* Summary bar */}
      <div className="flex items-center gap-3 flex-wrap">
        {staleCount > 0 && (
          <span className={`${pillClass} bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300`}>
            {staleCount} stale
          </span>
        )}
        {conflictCount > 0 && (
          <span className={`${pillClass} bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300`}>
            {conflictCount} conflict{conflictCount !== 1 ? 's' : ''}
          </span>
        )}
        {staleCount === 0 && conflictCount === 0 && (
          <span className="text-sm text-gray-500 dark:text-gray-400">No flags</span>
        )}

        <div className="ml-auto flex items-center gap-2">
          <button
            type="button"
            onClick={onOpenSettings}
            className="rounded-md p-1.5 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            title="Scan settings"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>

          <button
            type="button"
            onClick={onRunScan}
            disabled={scanRunning}
            className="flex items-center gap-1.5 rounded-md bg-blue-600 hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed px-3 py-1.5 text-sm font-medium text-white transition-colors"
          >
            {scanRunning ? (
              <>
                <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Scanning...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Run Scan
              </>
            )}
          </button>
        </div>
      </div>

      {/* Flag list */}
      {flagArray.length === 0 ? (
        <div className="flex items-center justify-center py-12 text-sm text-gray-400 dark:text-gray-500">
          No health issues found. Run a scan to check.
        </div>
      ) : (
        <div className="space-y-2">
          {flagArray.map(flag => (
            <div
              key={flag.memory_id}
              className="flex items-start gap-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-3"
            >
              <div className="flex-1 min-w-0 space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-mono text-xs text-gray-600 dark:text-gray-400 truncate max-w-[200px]">
                    {flag.memory_id}
                  </span>
                  <FlagTypeBadge flagType={flag.flag_type} />
                  <span className="text-xs text-gray-400 dark:text-gray-500">
                    score: {flag.score.toFixed(2)}
                  </span>
                </div>
                <p className="text-sm text-gray-700 dark:text-gray-300">
                  {flag.recommendation}
                </p>
                {flag.conflict_with && (
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Conflicts with: <span className="font-mono">{flag.conflict_with}</span>
                  </p>
                )}
              </div>
              <div className="shrink-0">
                {flag.flag_type === 'conflict' ? (
                  <button
                    type="button"
                    onClick={() => onOpenConflict(flag)}
                    className="rounded px-2.5 py-1 text-xs font-medium text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                  >
                    View Conflict
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => onDismissFlag(flag.memory_id)}
                    className="rounded px-2.5 py-1 text-xs font-medium text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                  >
                    Dismiss
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
