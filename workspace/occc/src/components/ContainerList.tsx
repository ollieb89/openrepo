'use client';

import { useState, useEffect } from 'react';

interface Container {
  id: string;
  name: string;
  status: string;
  image: string;
  created: number;
  labels: Record<string, string>;
}

interface ContainerListProps {
  onSelectContainer: (containerId: string) => void;
  selectedContainerId?: string;
}

export default function ContainerList({ onSelectContainer, selectedContainerId }: ContainerListProps) {
  const [containers, setContainers] = useState<Container[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchContainers() {
      try {
        const response = await fetch('/api/swarm/stream', { method: 'POST' });
        if (!response.ok) throw new Error('Failed to fetch containers');
        
        const data = await response.json();
        setContainers(data.containers || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    }

    fetchContainers();
    const interval = setInterval(fetchContainers, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div className="p-4">Loading containers...</div>;
  if (error) return <div className="p-4 text-red-500">Error: {error}</div>;

  return (
    <div className="border rounded-lg">
      <div className="p-4 border-b">
        <h2 className="text-lg font-semibold">OpenClaw Containers</h2>
        <p className="text-sm text-gray-600">{containers.length} containers found</p>
      </div>
      
      <div className="divide-y">
        {containers.length === 0 ? (
          <div className="p-4 text-gray-500">No containers found</div>
        ) : (
          containers.map((container) => (
            <div
              key={container.id}
              className={`p-4 cursor-pointer hover:bg-gray-50 ${selectedContainerId === container.id ? 'bg-blue-50' : ''}`}
              onClick={() => onSelectContainer(container.id)}
            >
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-medium">{container.name.replace(/^\//, '')}</h3>
                  <p className="text-sm text-gray-600">{container.image}</p>
                  <p className="text-sm text-gray-500">{container.status}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-gray-500">
                    {new Date(container.created * 1000).toLocaleString()}
                  </p>
                  {container.labels['openclaw.agent'] && (
                    <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
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
