'use client';

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

interface Props {
  data: { id: string; durationS: number }[];
}

export default function CompletionBarChart({ data }: Props) {
  if (data.length === 0) {
    return (
      <div className="border-2 border-dashed border-gray-200 dark:border-gray-700 rounded-lg h-48 flex flex-col items-center justify-center gap-3 px-4">
        {/* Placeholder bar chart outline */}
        <div className="flex items-end gap-1 h-12 opacity-30">
          <div className="w-4 h-4 bg-gray-300 dark:bg-gray-600 rounded-t" />
          <div className="w-4 h-7 bg-gray-300 dark:bg-gray-600 rounded-t" />
          <div className="w-4 h-10 bg-gray-300 dark:bg-gray-600 rounded-t" />
          <div className="w-4 h-6 bg-gray-300 dark:bg-gray-600 rounded-t" />
          <div className="w-4 h-12 bg-gray-300 dark:bg-gray-600 rounded-t" />
          <div className="w-4 h-8 bg-gray-300 dark:bg-gray-600 rounded-t" />
        </div>
        <p className="text-sm text-center text-gray-400 dark:text-gray-500">
          No tasks completed yet. Spawn a specialist to see metrics.
        </p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <XAxis
          dataKey="id"
          tickFormatter={id => id.slice(-6)}
          tick={{ fontSize: 10 }}
          interval="preserveStartEnd"
        />
        <YAxis unit="s" tick={{ fontSize: 10 }} width={36} />
        <Tooltip
          formatter={(value: number | undefined) => [`${value ?? 0}s`, 'Duration']}
          labelFormatter={label => `Task …${String(label).slice(-6)}`}
        />
        <Bar dataKey="durationS" fill="#3b82f6" radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
