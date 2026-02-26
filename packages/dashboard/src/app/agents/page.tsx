'use client';

import AgentTree from '@/components/agents/AgentTree';

export default function AgentsPage() {
  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">Agent Hierarchy</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          L1 strategic orchestrators, L2 project managers, and L3 specialist executors
        </p>
      </div>
      <AgentTree />
    </div>
  );
}
