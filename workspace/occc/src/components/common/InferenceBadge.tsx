import type { PrivacyExecutionMode } from '@/lib/types/privacy';

interface InferenceBadgeProps {
  mode: PrivacyExecutionMode;
  reason: string;
  className?: string;
}

export default function InferenceBadge({ mode, reason, className = '' }: InferenceBadgeProps) {
  const modeLabel = mode === 'remote' ? 'Remote inference' : 'Local inference';
  const modeStyles =
    mode === 'remote'
      ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200 border-amber-200 dark:border-amber-800'
      : 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200 border-emerald-200 dark:border-emerald-800';

  return (
    <div className={`inline-flex items-center gap-2 rounded-md border px-2.5 py-1 text-xs font-medium ${modeStyles} ${className}`}>
      <span>{modeLabel}</span>
      <span className="opacity-70">|</span>
      <span className="max-w-[48ch] truncate" title={reason}>
        {reason}
      </span>
    </div>
  );
}
