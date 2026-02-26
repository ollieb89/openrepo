import type { MemoryItem } from '@/lib/types/memory';

interface MemoryStatBarProps {
  items: MemoryItem[];
}

export default function MemoryStatBar({ items }: MemoryStatBarProps) {
  const total = items.length;

  const byAgent = items.reduce<Record<string, number>>((acc, item) => {
    const key = item.agent_type ?? 'unknown';
    acc[key] = (acc[key] ?? 0) + 1;
    return acc;
  }, {});

  const agentEntries = Object.entries(byAgent).filter(([, count]) => count > 0);

  return (
    <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400 py-2 px-1">
      <span className="font-medium text-gray-700 dark:text-gray-300">Memory</span>
      <span className="text-gray-400 dark:text-gray-600">|</span>
      <span>{total} items</span>
      {agentEntries.length > 0 && (
        <>
          <span className="text-gray-400 dark:text-gray-600">|</span>
          <span className="flex items-center gap-2">
            {agentEntries.map(([agent, count]) => (
              <span key={agent}>
                <span className="font-mono text-xs">{agent}</span>
                <span className="text-gray-400 dark:text-gray-500">: {count}</span>
              </span>
            ))}
          </span>
        </>
      )}
    </div>
  );
}
