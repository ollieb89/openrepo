'use client';

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import Card from '../common/Card';

export interface TrendPoint {
  date: string;
  completed: number;
  throughput: number;
}

export interface MetricsTrends {
  points: TrendPoint[];
  granularity: 'daily' | 'weekly' | 'monthly';
}

interface TrendLineChartProps {
  data: MetricsTrends | null;
  loading?: boolean;
}

function TrendLineChartSkeleton() {
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
        <div className="w-8 h-4 bg-gray-300 dark:bg-gray-600 rounded-t" />
        <div className="w-8 h-7 bg-gray-300 dark:bg-gray-600 rounded-t" />
        <div className="w-8 h-10 bg-gray-300 dark:bg-gray-600 rounded-t" />
        <div className="w-8 h-6 bg-gray-300 dark:bg-gray-600 rounded-t" />
        <div className="w-8 h-12 bg-gray-300 dark:bg-gray-600 rounded-t" />
      </div>
      <p className="text-sm text-gray-400 dark:text-gray-500">
        No trend data available
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
                  {entry.name}
                </span>
              </div>
              <span className="font-medium text-gray-900 dark:text-white">
                {entry.value.toLocaleString()}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  }
  return null;
}

export function TrendLineChart({ data, loading }: TrendLineChartProps) {
  if (loading) {
    return (
      <Card title="Completion & Throughput" subtitle="Task trends over time">
        <div className="p-4">
          <TrendLineChartSkeleton />
        </div>
      </Card>
    );
  }

  if (!data || !data.points || data.points.length === 0) {
    return (
      <Card title="Completion & Throughput" subtitle="Task trends over time">
        <div className="p-4">
          <EmptyState />
        </div>
      </Card>
    );
  }

  const chartData = data.points;

  return (
    <Card title="Completion & Throughput" subtitle="Task trends over time">
      <div className="p-4">
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
            <XAxis 
              dataKey="date" 
              tick={{ fontSize: 11, fill: '#6b7280' }}
              tickLine={false}
              axisLine={{ stroke: '#e5e7eb' }}
            />
            <YAxis 
              yAxisId="left"
              tick={{ fontSize: 11, fill: '#6b7280' }}
              tickLine={false}
              axisLine={false}
              allowDecimals={false}
            />
            <YAxis 
              yAxisId="right"
              orientation="right"
              tick={{ fontSize: 11, fill: '#6b7280' }}
              tickLine={false}
              axisLine={false}
              allowDecimals={false}
            />
            <Tooltip content={<CustomTooltip />} />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="completed"
              name="Completed"
              stroke="#10b981"
              strokeWidth={2}
              dot={{ fill: '#10b981', strokeWidth: 0, r: 3 }}
              activeDot={{ r: 5, stroke: '#10b981', strokeWidth: 2, fill: '#fff' }}
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="throughput"
              name="Throughput"
              stroke="#3b82f6"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={{ fill: '#3b82f6', strokeWidth: 0, r: 3 }}
              activeDot={{ r: 5, stroke: '#3b82f6', strokeWidth: 2, fill: '#fff' }}
            />
          </LineChart>
        </ResponsiveContainer>
        
        {/* Legend */}
        <div className="flex flex-wrap justify-center gap-4 mt-4 text-xs">
          <div className="flex items-center gap-1.5">
            <div className="flex items-center gap-1">
              <div className="w-3 h-0.5 bg-green-500" />
              <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
            </div>
            <span className="text-gray-600 dark:text-gray-400">Completed</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="flex items-center gap-1">
              <div className="w-3 h-0.5 bg-blue-500 border-dashed" style={{ borderTop: '1px dashed #3b82f6', height: 0 }} />
              <div className="w-1.5 h-1.5 rounded-full bg-blue-500" />
            </div>
            <span className="text-gray-600 dark:text-gray-400">Throughput</span>
          </div>
        </div>
      </div>
    </Card>
  );
}

export default TrendLineChart;
