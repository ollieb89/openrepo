interface Props {
  lifecycle: { pending: number; active: number; completed: number; failed: number };
}

const CARDS = [
  {
    key: 'pending' as const,
    label: 'Pending',
    bg: 'bg-yellow-50 dark:bg-yellow-900/20',
    text: 'text-yellow-600 dark:text-yellow-400',
  },
  {
    key: 'active' as const,
    label: 'Active',
    bg: 'bg-blue-50 dark:bg-blue-900/20',
    text: 'text-blue-600 dark:text-blue-400',
  },
  {
    key: 'completed' as const,
    label: 'Completed',
    bg: 'bg-green-50 dark:bg-green-900/20',
    text: 'text-green-600 dark:text-green-400',
  },
  {
    key: 'failed' as const,
    label: 'Failed',
    bg: 'bg-red-50 dark:bg-red-900/20',
    text: 'text-red-600 dark:text-red-400',
  },
];

export default function LifecycleStatCards({ lifecycle }: Props) {
  return (
    <div className="flex gap-3">
      {CARDS.map(({ key, label, bg, text }) => (
        <div key={key} className={`flex-1 px-3 py-2 rounded-lg ${bg}`}>
          <p className={`text-xl font-bold ${text}`}>{lifecycle[key]}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
        </div>
      ))}
    </div>
  );
}
