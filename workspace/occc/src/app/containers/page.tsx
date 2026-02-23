'use client';

import { useState } from 'react';
import ContainerList from '@/components/ContainerList';
import LogViewer from '@/components/LogViewer';

export default function ContainersPage() {
  const [selectedContainerId, setSelectedContainerId] = useState<string | undefined>();

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">Containers</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Monitor L3 specialist Docker containers and stream logs
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <ContainerList
            onSelectContainer={setSelectedContainerId}
            selectedContainerId={selectedContainerId}
          />
        </div>
        <div className="lg:col-span-2">
          <LogViewer containerId={selectedContainerId} />
        </div>
      </div>
    </div>
  );
}
