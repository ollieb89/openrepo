import type { TaskActivityEntry } from '@/lib/types';

interface ActivityLogProps {
  entries: TaskActivityEntry[];
}

export default function ActivityLog({ entries }: ActivityLogProps) {
  if (entries.length === 0) {
    return <p className="text-sm text-gray-500 dark:text-gray-400 p-4">No activity yet</p>;
  }

  return (
    <div className="flow-root p-4">
      <ul className="-mb-8">
        {entries.map((entry, index) => (
          <li key={index}>
            <div className="relative pb-8">
              {index !== entries.length - 1 && (
                <span className="absolute left-2 top-4 -ml-px h-full w-0.5 bg-gray-200 dark:bg-gray-700" />
              )}
              <div className="relative flex items-start space-x-3">
                <div className="relative">
                  <div className="h-4 w-4 rounded-full bg-blue-500 dark:bg-blue-400 ring-4 ring-white dark:ring-gray-800" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
                      {new Date(entry.timestamp * 1000).toLocaleTimeString()}
                    </span>
                    {entry.status && (
                      <span className="text-xs text-gray-400 dark:text-gray-500">
                        [{entry.status}]
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-700 dark:text-gray-300 mt-0.5">
                    {entry.entry}
                  </p>
                </div>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
