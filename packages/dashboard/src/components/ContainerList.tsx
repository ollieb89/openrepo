'use client';

import { useContainers } from '@/lib/hooks/useContainers';

interface ContainerListProps {
  onSelectContainer: (containerId: string) => void;
  selectedContainerId?: string;
}

export default function ContainerList({ onSelectContainer, selectedContainerId }: ContainerListProps) {
  const { containers, isLoading, error } = useContainers();

  if (isLoading) return <div className="p-4 text-gray-500 dark:text-gray-400">Loading containers...</div>;
  if (error) return <div className="p-4 text-red-500">Error loading containers</div>;

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800">
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-sm font-semibold text-gray-900 dark:text-white">OpenClaw Containers</h2>
        <p className="text-xs text-gray-500 dark:text-gray-400">{containers.length} containers found</p>
      </div>

      <div className="divide-y divide-gray-200 dark:divide-gray-700">
        {containers.length === 0 ? (
          <div className="p-4 text-sm text-gray-500 dark:text-gray-400">No containers running</div>
        ) : (
          containers.map((container) => (
            <div
              key={container.id}
              className={`p-4 cursor-pointer transition-colors ${
                selectedContainerId === container.id
                  ? 'bg-blue-50 dark:bg-blue-900/20'
                  : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'
              }`}
              onClick={() => onSelectContainer(container.id)}
            >
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="text-sm font-medium text-gray-900 dark:text-white">
                    {container.name.replace(/^\//, '')}
                  </h3>
                  {container.image && (
                    <p className="text-xs text-gray-500 dark:text-gray-400">{container.image}</p>
                  )}
                  <p className="text-xs text-gray-400 dark:text-gray-500">{container.status}</p>
                </div>
                <div className="text-right">
                  {container.created != null && (
                    <p className="text-xs text-gray-400 dark:text-gray-500">
                      {new Date(container.created * 1000).toLocaleString()}
                    </p>
                  )}
                  {container.labels?.['openclaw.agent'] && (
                    <span className="text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300 px-2 py-0.5 rounded mt-1 inline-block">
                      {container.labels['openclaw.agent']}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
