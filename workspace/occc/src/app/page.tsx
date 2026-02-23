'use client';

import { useState } from 'react';
import ContainerList from '@/components/ContainerList';
import LogViewer from '@/components/LogViewer';

export default function Home() {
  const [selectedContainerId, setSelectedContainerId] = useState<string | undefined>();

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="container mx-auto p-6">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">OCCC Dashboard</h1>
          <p className="text-gray-600">OpenClaw Control Center - Monitor your AI swarm</p>
        </header>

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
    </main>
  );
}
