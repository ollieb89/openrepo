'use client';

import type { Agent } from '@/lib/types';
import { useAgents } from '@/lib/hooks/useAgents';
import { useProject } from '@/context/ProjectContext';
import AgentCard from './AgentCard';

function AgentNode({ agent, allAgents, depth = 0 }: { agent: Agent; allAgents: Agent[]; depth?: number }) {
  const children = allAgents.filter(a => a.reports_to === agent.id);

  return (
    <div className={depth > 0 ? 'ml-8 mt-3' : ''}>
      {depth > 0 && (
        <div className="relative -ml-4 mb-2">
          <div className="absolute left-0 top-0 w-4 h-4 border-l-2 border-b-2 border-gray-300 dark:border-gray-600 rounded-bl" />
        </div>
      )}
      <AgentCard agent={agent} />
      {children.length > 0 && (
        <div className="border-l-2 border-gray-200 dark:border-gray-700 ml-4 pl-0">
          {children.map(child => (
            <AgentNode key={child.id} agent={child} allAgents={allAgents} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function AgentTree() {
  const { projectId } = useProject();
  const { agents, isLoading } = useAgents(projectId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500 dark:text-gray-400">
        Loading agents...
      </div>
    );
  }

  if (agents.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500 dark:text-gray-400">
        <p>No agents configured</p>
      </div>
    );
  }

  const roots = agents.filter(a => !a.reports_to);

  return (
    <div className="space-y-6">
      {roots.map(root => (
        <AgentNode key={root.id} agent={root} allAgents={agents} />
      ))}
    </div>
  );
}
