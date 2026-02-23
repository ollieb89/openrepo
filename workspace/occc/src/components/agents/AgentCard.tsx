import type { Agent } from '@/lib/types';

const levelStyles: Record<number, { bg: string; label: string }> = {
  1: { bg: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300', label: 'L1' },
  2: { bg: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300', label: 'L2' },
  3: { bg: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300', label: 'L3' },
};

export default function AgentCard({ agent }: { agent: Agent }) {
  const style = levelStyles[agent.level] || levelStyles[3];

  return (
    <div className="p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
      <div className="flex items-center gap-2 mb-2">
        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold ${style.bg}`}>
          {style.label}
        </span>
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white">{agent.name}</h4>
      </div>

      <div className="space-y-1 text-xs">
        <div className="flex items-center gap-1.5">
          <span className="text-gray-400 dark:text-gray-500">ID:</span>
          <span className="font-mono text-gray-600 dark:text-gray-300">{agent.id}</span>
        </div>

        {agent.project && (
          <div className="flex items-center gap-1.5">
            <span className="text-gray-400 dark:text-gray-500">Project:</span>
            <span className="text-gray-600 dark:text-gray-300">{agent.project}</span>
          </div>
        )}

        {agent.reports_to && (
          <div className="flex items-center gap-1.5">
            <span className="text-gray-400 dark:text-gray-500">Reports to:</span>
            <span className="font-mono text-gray-600 dark:text-gray-300">{agent.reports_to}</span>
          </div>
        )}

        {agent.sandbox && (
          <div className="flex items-center gap-1.5">
            <span className="text-gray-400 dark:text-gray-500">Sandbox:</span>
            <span className="text-gray-600 dark:text-gray-300">{agent.sandbox.mode}</span>
          </div>
        )}
      </div>
    </div>
  );
}
