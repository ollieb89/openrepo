'use client';

import { useState } from 'react';
import { RefreshCw, ChevronDown, ChevronUp, WifiOff } from 'lucide-react';
import Card from '@/components/common/Card';
import { useCourseCorrections } from '@/hooks/useAutonomyEvents';

interface CourseCorrectionHistoryProps {
  taskId: string;
}

function formatTime(timestamp: number): string {
  return new Date(timestamp * 1000).toLocaleString();
}

export function CourseCorrectionHistory({ taskId }: CourseCorrectionHistoryProps) {
  const { corrections } = useCourseCorrections(taskId);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  
  if (corrections.length === 0) return null;

  const toggleExpanded = (index: number) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  return (
    <Card className="mt-4">
      <div className="p-4">
        <div className="flex items-center gap-2 mb-4">
          <RefreshCw className="h-4 w-4 text-gray-500" />
          <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
            Course Corrections ({corrections.length})
          </h4>
        </div>
        
        <div className="space-y-2">
          {corrections.map((corr, i) => {
            const isExpanded = expanded.has(i);
            
            return (
              <div 
                key={i} 
                className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden"
              >
                <button
                  onClick={() => toggleExpanded(i)}
                  className="w-full flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="text-xs text-gray-400 flex-shrink-0">
                      {formatTime(corr.timestamp)}
                    </span>
                    <span className="text-sm text-gray-700 dark:text-gray-300 truncate">
                      Step &quot;{corr.failed_step.action}&quot; failed
                    </span>
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 flex-shrink-0">
                      {corr.recovery_steps.length} recovery steps
                    </span>
                  </div>
                  {isExpanded ? (
                    <ChevronUp className="h-4 w-4 text-gray-400 flex-shrink-0" />
                  ) : (
                    <ChevronDown className="h-4 w-4 text-gray-400 flex-shrink-0" />
                  )}
                </button>
                
                {isExpanded && (
                  <div className="p-3 bg-white dark:bg-gray-900">
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
                      Failed action: <span className="text-gray-700 dark:text-gray-300">{corr.failed_step.action}</span>
                    </p>
                    <p className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                      Recovery plan:
                    </p>
                    <ol className="list-decimal list-inside text-sm space-y-1">
                      {corr.recovery_steps.map((step, j) => (
                        <li key={j} className="text-gray-700 dark:text-gray-300">
                          {step.action}
                        </li>
                      ))}
                    </ol>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </Card>
  );
}

export default CourseCorrectionHistory;
