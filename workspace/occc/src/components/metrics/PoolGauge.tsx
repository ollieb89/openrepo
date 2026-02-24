'use client';

import {
  RadialBarChart,
  RadialBar,
  PolarAngleAxis,
  ResponsiveContainer,
} from 'recharts';

interface Props {
  pct: number;
  active: number;
  max: number;
}

export default function PoolGauge({ pct, active, max }: Props) {
  const color = pct >= 80 ? '#ef4444' : pct >= 50 ? '#f59e0b' : '#22c55e';
  const data = [{ value: pct, fill: color }];

  return (
    <div className="flex flex-col items-center">
      <ResponsiveContainer width="100%" height={160}>
        <RadialBarChart
          innerRadius="60%"
          outerRadius="90%"
          data={data}
          startAngle={90}
          endAngle={-270}
        >
          <PolarAngleAxis
            type="number"
            domain={[0, 100]}
            angleAxisId={0}
            tick={false}
          />
          <RadialBar
            dataKey="value"
            angleAxisId={0}
            background={{ fill: '#e5e7eb' }}
            cornerRadius={4}
          />
        </RadialBarChart>
      </ResponsiveContainer>
      <div className="text-center -mt-4">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {active}/{max} active
        </p>
        <p className="text-xl font-bold" style={{ color }}>
          {pct}%
        </p>
      </div>
    </div>
  );
}
