'use client';

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import Card from '../common/Card';

export interface StatusDistributionPoint {
  date: string;
  completed: number;
  failed: number;
  pending: number;
  in_progress: number;
}

interface StatusDistributionChartProps {
  data: StatusDistributionPoint[];
  loading?: boolean;
}

function StatusDistributionChartSkeleton() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="h-48 bg-gray-200 dark:bg-gray-700 rounded" />
    </div>
  );
}

function EmptyState() {
  return (
    <div className="h-48 flex flex-col items-center justify-center gap-3">
      <div className="flex items-end gap-1 h-12 opacity-30">
        <div className="w-6 h-4 bg-gray-300 dark:bg-gray-600 rounded-t" />
        <div className="w-6 h-7 bg-gray-300 dark:bg-gray-600 rounded-t" />
        <div className="w-6 h-10 bg-gray-300 dark:bg-gray-600 rounded-t" />
        <div className="w-6 h-6 bg-gray-300 dark:bg-gray-600 rounded-t" />
        <div className="w-6 h-12 bg-gray-300 dark:bg-gray-600 rounded-t" />
      </div>
      <p className="text-sm text-gray-400 dark:text-gray-500">
        No status distribution data available
      </p>
    </div>
  );
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    value: number;
    name: string;
    color: string;
  }>;
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (active && payload && payload.length) {
    const total = payload.reduce((sum, entry) => sum + (entry.value || 0), 0);
    
    return (
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3 text-sm">
        <p className="font-semibold text-gray-900 dark:text-white mb-2">{label}</p>
        <div className="space-y-1">
          {payload.map((entry, index) => (
            <div key={index} className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <div 
                  className="w-3 h-3 rounded-full" 
                  style={{ backgroundColor: entry.color }}
                />
                <span className="text-gray-600 dark:text-gray-400 capitalize">
                  {entry.name.replace('_', ' ')}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-medium text-gray-900 dark:text-white">
                  {entry.value}
                </span>
                {total > 0 && (
                  <span className="text-xs text-gray-400">
                    ({Math.round((entry.value / total) * 100)}%)
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
        <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-700">
          <div className="flex justify-between text-xs text-gray-500">
            <span>Total</span>
            <span className="font-medium text-gray-900 dark:text-white">{total}</span>
          </div>
        </div>
      </div>
    );
  }
  return null;
}

export function StatusDistributionChart({ data, loading }: StatusDistributionChartProps) {
  if (loading) {
    return (
      <Card title="Status Distribution" subtitle="Task status over time">
        <div className="p-4">
          <StatusDistributionChartSkeleton />
        </div>
      </Card>
    );
  }

  if (!data || data.length === 0) {
    return (
      <Card title="Status Distribution" subtitle="Task status over time">
        <div className="p-4">
          <EmptyState />
        </div>
      </Card>
    );
  }

  return (
    <Card title="Status Distribution" subtitle="Task status over time">
      <div className="p-4">
        <ResponsiveContainer width="100%" height={250}>
          <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="colorCompleted" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="colorInProgress" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="colorPending" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#f59e0b" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="colorFailed" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
            <XAxis 
              dataKey="date" 
              tick={{ fontSize: 11, fill: '#6b7280' }}
              tickLine={false}
              axisLine={{ stroke: '#e5e7eb' }}
            />
            <YAxis 
              tick={{ fontSize: 11, fill: '#6b7280' }}
              tickLine={false}
              axisLine={false}
              allowDecimals={false}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey="completed"
              name="completed"
              stackId="1"
              stroke="#10b981"
              fill="url(#colorCompleted)"
              strokeWidth={2}
            />
            <Area
              type="monotone"
              dataKey="in_progress"
              name="in progress"
              stackId="1"
              stroke="#3b82f6"
              fill="url(#colorInProgress)"
              strokeWidth={2}
            />
            <Area
              type="monotone"
              dataKey="pending"
              name="pending"
              stackId="1"
              stroke="#f59e0b"
              fill="url(#colorPending)"
              strokeWidth={2}
            />
            <Area
              type="monotone"
              dataKey="failed"
              name="failed"
              stackId="1"
              stroke="#ef4444"
              fill="url(#colorFailed)"
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
        
        {/* Legend */}
        <div className="flex flex-wrap justify-center gap-4 mt-4 text-xs">
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-full bg-green-500" />
            <span className="text-gray-600 dark:text-gray-400">Completed</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-full bg-blue-500" />
            <span className="text-gray-600 dark:text-gray-400">In Progress</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-full bg-amber-500" />
            <span className="text-gray-600 dark:text-gray-400">Pending</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-full bg-red-500" />
            <span className="text-gray-600 dark:text-gray-400">Failed</span>
          </div>
        </div>
      </div>
    </Card>
  );
}

export default StatusDistributionChart;
