'use client';

import React, { useEffect, useState } from 'react';
import Card from '@/components/common/Card';
import { useProject } from '@/context/ProjectContext';
import { Activity, Server, Database, MessageSquare, Zap } from 'lucide-react';
import { apiFetch } from '@/lib/api-client';

interface HealthStatus {
  service: string;
  status: 'healthy' | 'unhealthy' | 'loading';
  details?: string;
  icon: React.ReactNode;
}

export default function EnvironmentPage() {
  const { projectId } = useProject();
  const [openclawRoot, setOpenclawRoot] = useState<string>('Loading...');
  const [statuses, setStatuses] = useState<HealthStatus[]>([
    { service: 'Gateway API', status: 'loading', icon: <Server className="w-5 h-5" /> },
    { service: 'Memory (memU)', status: 'loading', icon: <Database className="w-5 h-5" /> },
    { service: 'Event Bridge', status: 'loading', icon: <Zap className="w-5 h-5" /> },
    { service: 'Jarvis State', status: 'loading', icon: <Activity className="w-5 h-5" /> },
  ]);

  // OPENCLAW_ROOT is exposed as a build-time env constant via next.config.js env block
  useEffect(() => {
    setOpenclawRoot(process.env.OPENCLAW_ROOT || 'Not set');
  }, []);

  useEffect(() => {
    async function checkHealth() {
      // Mocking health checks based on reachable endpoints
      const newStatuses = [...statuses];

      // Check Gateway
      try {
        const res = await apiFetch('/api/health/gateway');
        newStatuses[0].status = res.ok ? 'healthy' : 'unhealthy';
      } catch (e) {
        newStatuses[0].status = 'unhealthy';
      }

      // Check memU
      try {
        const res = await apiFetch('/api/health/memory');
        newStatuses[1].status = res.ok ? 'healthy' : 'unhealthy';
      } catch (e) {
        newStatuses[1].status = 'unhealthy';
      }

      // Check Event Bridge via the events/latest endpoint
      try {
        const res = await apiFetch('/api/events/latest?limit=1');
        newStatuses[2].status = res.ok ? 'healthy' : 'unhealthy';
      } catch (e) {
        newStatuses[2].status = 'unhealthy';
      }

      // Check Jarvis State
      try {
        const res = await apiFetch(`/api/tasks?projectId=${projectId}`);
        newStatuses[3].status = res.ok ? 'healthy' : 'unhealthy';
      } catch (e) {
        newStatuses[3].status = 'unhealthy';
      }

      setStatuses(newStatuses);
    }

    checkHealth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  return (
    <div className="space-y-6">
      <div className="mb-4">
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">Environment Health</h1>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Real-time status of OpenClaw orchestration services
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statuses.map((s) => (
          <Card key={s.service} className="p-4">
            <div className="flex items-center space-x-3">
              <div className={`p-2 rounded-lg ${s.status === 'healthy' ? 'bg-green-100 text-green-600' :
                  s.status === 'unhealthy' ? 'bg-red-100 text-red-600' :
                    'bg-gray-100 text-gray-400'
                }`}>
                {s.icon}
              </div>
              <div>
                <h3 className="text-sm font-medium text-gray-900 dark:text-white">{s.service}</h3>
                <p className={`text-xs font-bold ${s.status === 'healthy' ? 'text-green-500' :
                    s.status === 'unhealthy' ? 'text-red-500' :
                      'text-gray-400'
                  }`}>
                  {s.status.toUpperCase()}
                </p>
              </div>
            </div>
          </Card>
        ))}
      </div>

      <Card className="p-6">
        <h2 className="text-lg font-semibold mb-4">Orchestration Details</h2>
        <div className="space-y-4">
          <div className="grid grid-cols-2 text-sm">
            <span className="text-gray-500">Project Root</span>
            <span className="font-mono text-gray-900 dark:text-gray-100">{openclawRoot}</span>
          </div>
          <div className="grid grid-cols-2 text-sm">
            <span className="text-gray-500">Active Project</span>
            <span className="font-mono text-gray-900 dark:text-gray-100">{projectId}</span>
          </div>
          <div className="grid grid-cols-2 text-sm">
            <span className="text-gray-500">Event Socket</span>
            <span className="font-mono text-gray-900 dark:text-gray-100">
              {(process.env.OPENCLAW_ROOT || '~/.openclaw') + '/run/events.sock'}
            </span>
          </div>
        </div>
      </Card>
    </div>
  );
}
