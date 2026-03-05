import type { JSX } from 'react';

interface MetricCardProps {
  title: string;
  value: number;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string; // e.g., "+5%"
  format?: 'percent' | 'number' | 'duration';
  loading?: boolean;
}

function formatValue(value: number, format?: MetricCardProps['format']): string {
  switch (format) {
    case 'percent':
      return `${Math.round(value * 100)}%`;
    case 'duration':
      return formatDuration(value);
    case 'number':
    default:
      return value.toLocaleString();
  }
}

function formatDuration(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (days > 0) {
    return `${days}d ${hours % 24}h`;
  }
  if (hours > 0) {
    return `${hours}h ${minutes % 60}m`;
  }
  if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`;
  }
  return `${seconds}s`;
}

// Determine if "up" trend is good or bad based on metric type
function isPositiveTrend(title: string, trend: 'up' | 'down' | 'neutral'): boolean {
  const lowerTitle = title.toLowerCase();
  
  // Metrics where up is good
  const upIsGood = ['completion', 'success', 'throughput', 'productivity'];
  // Metrics where down is good
  const downIsGood = ['failure', 'error', 'cycle time', 'latency', 'backlog'];
  
  const isUpGoodMetric = upIsGood.some(keyword => lowerTitle.includes(keyword));
  const isDownGoodMetric = downIsGood.some(keyword => lowerTitle.includes(keyword));
  
  if (isUpGoodMetric) {
    return trend === 'up';
  }
  if (isDownGoodMetric) {
    return trend === 'down';
  }
  
  // Default: up is neutral/positive
  return trend === 'up';
}

function getTrendColorClasses(title: string, trend: 'up' | 'down' | 'neutral'): string {
  if (trend === 'neutral') {
    return 'text-gray-500 dark:text-gray-400';
  }
  
  const isPositive = isPositiveTrend(title, trend);
  
  if (isPositive) {
    return 'text-green-600 dark:text-green-400';
  }
  return 'text-red-600 dark:text-red-400';
}

function getTrendArrow(trend: 'up' | 'down' | 'neutral'): string {
  switch (trend) {
    case 'up':
      return '↑';
    case 'down':
      return '↓';
    case 'neutral':
    default:
      return '→';
  }
}

export function MetricCard({
  title,
  value,
  trend,
  trendValue,
  format,
  loading = false,
}: MetricCardProps) {
  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4 animate-pulse">
        {/* Title skeleton */}
        <div className="h-4 w-24 bg-gray-200 dark:bg-gray-700 rounded mb-2" />
        {/* Value skeleton */}
        <div className="h-8 w-20 bg-gray-200 dark:bg-gray-700 rounded mb-2" />
        {/* Trend skeleton */}
        <div className="h-4 w-16 bg-gray-200 dark:bg-gray-700 rounded" />
      </div>
    );
  }

  const formattedValue = formatValue(value, format);
  const trendColorClass = trend ? getTrendColorClasses(title, trend) : '';
  const trendArrow = trend ? getTrendArrow(trend) : '';

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
      {/* Title */}
      <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
        {title}
      </p>
      
      {/* Value */}
      <p className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-2">
        {formattedValue}
      </p>
      
      {/* Trend indicator */}
      {trend && trendValue && (
        <div className={`flex items-center gap-1 text-sm font-medium ${trendColorClass}`}>
          <span aria-hidden="true">{trendArrow}</span>
          <span>{trendValue}</span>
        </div>
      )}
      
      {/* Placeholder for alignment when no trend */}
      {!trend && <div className="h-5" />}
    </div>
  );
}

export default MetricCard;
