'use client';

import { AlertTriangle } from 'lucide-react';

interface ConfidenceIndicatorProps {
  score: number;
  threshold?: number;
  showTooltip?: boolean;
}

export function ConfidenceIndicator({ 
  score, 
  threshold = 0.4,
  showTooltip = true 
}: ConfidenceIndicatorProps) {
  const percentage = Math.round(score * 100);
  const isLow = score < threshold;
  
  return (
    <div className="flex items-center gap-2" title={showTooltip ? `Threshold: ${Math.round(threshold * 100)}%` : undefined}>
      <div className="w-24 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div 
          className={`h-full rounded-full transition-all duration-300 ${
            isLow ? 'bg-red-500' : 'bg-green-500'
          }`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className={`text-sm font-medium ${isLow ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
        {percentage}%
      </span>
      {isLow && <AlertTriangle className="h-4 w-4 text-red-500" />}
    </div>
  );
}

export default ConfidenceIndicator;
