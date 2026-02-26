'use client';

import type { Agent, Task } from '@/lib/types';
import { useAgents } from '@/lib/hooks/useAgents';
import { useTasks } from '@/lib/hooks/useTasks';
import { useProject } from '@/context/ProjectContext';
import AgentCard from './AgentCard';

const ACTIVE_STATUSES = new Set(['in_progress', 'starting', 'testing']);
const TERMINAL_STATUSES = new Set(['completed', 'failed', 'rejected']);

function getAgentStatus(
  agent: Agent,
  activeTasks: Task[],
  hasNonTerminal: boolean
): 'idle' | 'busy' | 'offline' {
  if (agent.level === 1) return 'idle';
  if (agent.level === 2) return hasNonTerminal ? 'busy' : 'idle';
  // L3 or unknown
  return activeTasks.length > 0 ? 'busy' : 'idle';
}

function AgentNode({
  agent,
  allAgents,
  statusMap,
  depth = 0,
}: {
  agent: Agent;
  allAgents: Agent[];
  statusMap: Record<string, 'idle' | 'busy' | 'offline'>;
  depth?: number;
}) {
  const children = allAgents.filter(a => a.reports_to === agent.id);
  const status = statusMap[agent.id] ?? 'offline';

  return (
    <div className={depth > 0 ? 'ml-8 mt-3' : ''}>
      {depth > 0 && (
        <div className="relative -ml-4 mb-2">
          <div className="absolute left-0 top-0 w-4 h-4 border-l-2 border-b-2 border-gray-300 dark:border-gray-600 rounded-bl" />
        </div>
      )}
      <AgentCard agent={agent} status={status} />
      {children.length > 0 && (
        <div className="border-l-2 border-gray-200 dark:border-gray-700 ml-4 pl-0">
          {children.map(child => (
            <AgentNode
              key={child.id}
              agent={child}
              allAgents={allAgents}
              statusMap={statusMap}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function AgentTreeInner({ projectId }: { projectId: string | null }) {
  const { agents, isLoading } = useAgents(projectId);
  const { tasks } = useTasks(projectId);

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

  const activeTasks = tasks.filter(t => ACTIVE_STATUSES.has(t.status));
  const hasNonTerminal = tasks.some(t => !TERMINAL_STATUSES.has(t.status));

  const globalAgents = agents.filter(a => !a.project);
  const projectAgents = agents.filter(a => a.project === projectId);

  // Precompute status for every visible agent
  const statusMap: Record<string, 'idle' | 'busy' | 'offline'> = {};
  for (const agent of agents) {
    statusMap[agent.id] = getAgentStatus(agent, activeTasks, hasNonTerminal);
  }

  const globalRoots = globalAgents.filter(a => !a.reports_to);
  const projectRoots = projectAgents.filter(a => !a.reports_to);

  return (
    <div className="space-y-6">
      {/* Global section */}
      {globalAgents.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <span className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 rounded-full text-xs font-semibold text-gray-600 dark:text-gray-300">
              Global
            </span>
          </div>
          <div className="space-y-6">
            {globalRoots.map(root => (
              <AgentNode
                key={root.id}
                agent={root}
                allAgents={agents}
                statusMap={statusMap}
              />
            ))}
          </div>
        </div>
      )}

      {/* Project section */}
      <div>
        <div className="flex items-center gap-2 mb-3 mt-6">
          <span className="px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 rounded-full text-xs font-semibold text-blue-700 dark:text-blue-300">
            Project
          </span>
        </div>
        {projectAgents.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400 py-4">
            No agents assigned to this project
          </p>
        ) : (
          <div className="space-y-6">
            {projectRoots.map(root => (
              <AgentNode
                key={root.id}
                agent={root}
                allAgents={agents}
                statusMap={statusMap}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function AgentTree() {
  const { projectId } = useProject();
  // Key on projectId forces full remount (and useState reset) when project switches
  return <AgentTreeInner key={projectId ?? '__none__'} projectId={projectId} />;
}
