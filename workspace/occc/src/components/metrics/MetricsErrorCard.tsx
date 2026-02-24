interface Props {
  onRetry: () => void;
}

export default function MetricsErrorCard({ onRetry }: Props) {
  return (
    <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 flex items-center justify-between">
      <p className="text-sm text-red-700 dark:text-red-300">
        Could not load metrics.
      </p>
      <button
        onClick={onRetry}
        className="ml-4 px-3 py-1.5 text-sm font-medium rounded-md bg-red-100 dark:bg-red-800/40 text-red-700 dark:text-red-300 hover:bg-red-200 dark:hover:bg-red-800/60 transition-colors"
      >
        Retry
      </button>
    </div>
  );
}
