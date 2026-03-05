'use client';

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import Card from '../common/Card';

export interface AgentMetrics {
  agent_id: string;
  tasks_completed: number;
  tasks_failed: number;
  median_cycle_time_ms: number;
  completion_rate: number;
}

interface AgentLeaderboardProps {
  agents: AgentMetrics[];
  loading?: boolean;
}

function formatDuration(ms: number): string {
  const minutes = Math.floor(ms / 60000);
  const hours = Math.floor(minutes / 60);
  if (hours > 0) {
    return `${hours}h ${minutes % 60}m`;
  }
  return `${minutes}m`;
}

function AgentLeaderboardSkeleton() {
  return (
    <div className="animate-pulse space-y-3">
      {/* Placeholder rows for agents */}
      {[1, 2, 3, 4, 5].map(i => (
        <div key={i} className="flex items-center gap-3">
          {/* Agent name placeholder */}
          <div className="w-24 h-4 bg-gray-200 dark:bg-gray-700 rounded" />
          {/* Bar placeholder */}
          <div 
            className="h-6 bg-gray-200 dark:bg-gray-700 rounded" 
            style={{ width: `${60 + Math.random() * 30}%` }}
          />
        </div>
      ))}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="h-48 flex flex-col items-center justify-center gap-3 px-4">
      {/* Placeholder bar chart outline */}
      <div className="flex items-end gap-1 h-12 opacity-30">
        <div className="w-4 h-4 bg-gray-300 dark:bg-gray-600 rounded-t" />
        <div className="w-4 h-7 bg-gray-300 dark:bg-gray-600 rounded-t" />
        <div className="w-4 h-10 bg-gray-300 dark:bg-gray-600 rounded-t" />
        <div className="w-4 h-6 bg-gray-300 dark:bg-gray-600 rounded-t" />
        <div className="w-4 h-12 bg-gray-300 dark:bg-gray-600 rounded-t" />
      </div>
      <p className="text-sm text-center text-gray-400 dark:text-gray-500">
        No agent data available
      </p>
    </div>
  );
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    value: number;
    payload: AgentMetrics;
  }>;
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (active && payload && payload.length > 0) {
    const agent = payload[0].payload;
    return (
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3 text-sm">
        <p className="font-semibold text-gray-900 dark:text-white mb-1">
          {agent.agent_id}
        </p>
        <div className="space-y-1 text-gray-600 dark:text-gray-400">
          <p>Tasks completed: <span className="font-medium text-gray-900 dark:text-white">{agent.tasks_completed}</span></p>
          <p>Tasks failed: <span className="font-medium text-red-600">{agent.tasks_failed}</span></p>
          <p>Median cycle time: <span className="font-medium text-gray-900 dark:text-white">{formatDuration(agent.median_cycle_time_ms)}</span></p>
          <p>Completion rate: <span className="font-medium text-gray-900 dark:text-white">{(agent.completion_rate * 100).toFixed(0)}%</span></p>
        </div>
      </div>
    );
  }
  return null;
}

export function AgentLeaderboard({ agents, loading }: AgentLeaderboardProps) {
  // Sort agents by tasks_completed descending
  const sortedAgents = [...agents].sort((a, b) => b.tasks_completed - a.tasks_completed);

  return (
    <Card title="Agent Leaderboard">
      <div className="p-4">
        {loading ? (
          <AgentLeaderboardSkeleton />
        ) : sortedAgents.length === 0 ? (
          <EmptyState />
        ) : (
          <ResponsiveContainer width="100%" height={sortedAgents.length * 40 + 40}>
            <BarChart
              layout="vertical"
              data={sortedAgents}
              margin={{ top: 8, right: 80, left: 0, bottom: 8 }}
              barSize={20}
            >
              <XAxis 
                type="number" 
                tick={{ fontSize: 11 }}
                tickLine={false}
                axisLine={{ stroke: '#e5e7eb' }}
              />
              <YAxis
                type="category"
                dataKey="agent_id"
                width={100}
                tick={{ fontSize: 11, fill: '#374151' }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: '#f3f4f6' }} />
              <Bar 
                dataKey="tasks_completed" 
                fill="#3b82f6"
                radius={[0, 4, 4, 0]}
              >
                {sortedAgents.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill="#3b82f6" />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
        
        {/* Secondary info: median cycle time display */}
        {!loading && sortedAgents.length > 0 && (
          <div className="mt-4 pt-3 border-t border-gray-100 dark:border-gray-700">
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">Median cycle time by agent:</p>
            <div className="flex flex-wrap gap-2">
              {sortedAgents.slice(0, 5).map(agent => (
                <span 
                  key={agent.agent_id}
                  className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300"
                >
                  <span className="font-medium truncate max-w-[80px]">{agent.agent_id}</span>
                  <span className="mx-1 text-gray-400">·</span>
                  <span className="text-gray-500">{formatDuration(agent.median_cycle_time_ms)}</span>
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}

export default AgentLeaderboard;
