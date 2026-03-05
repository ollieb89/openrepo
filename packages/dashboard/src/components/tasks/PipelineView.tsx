'use client';

import React from 'react';
import { CheckCircle2, Circle, Clock, AlertCircle, ArrowRight } from 'lucide-react';
import type { TaskStatus } from '@/lib/types';

interface StepProps {
  label: string;
  status: 'complete' | 'active' | 'pending' | 'failed';
  description?: string;
  compact?: boolean;
}

function Step({ label, status, description, compact = false }: StepProps) {
  const icons = {
    complete: <CheckCircle2 className={compact ? 'w-4 h-4 text-green-500' : 'w-6 h-6 text-green-500'} />,
    active: <Clock className={compact ? 'w-4 h-4 text-blue-500 animate-pulse' : 'w-6 h-6 text-blue-500 animate-pulse'} />,
    pending: <Circle className={compact ? 'w-4 h-4 text-gray-300' : 'w-6 h-6 text-gray-300'} />,
    failed: <AlertCircle className={compact ? 'w-4 h-4 text-red-500' : 'w-6 h-6 text-red-500'} />,
  };

  const textColors = {
    complete: 'text-green-700 dark:text-green-400',
    active: 'text-blue-700 dark:text-blue-400 font-semibold',
    pending: 'text-gray-500 dark:text-gray-400',
    failed: 'text-red-700 dark:text-red-400',
  };

  if (compact) {
    return (
      <div className="flex items-center gap-2 py-1">
        {icons[status]}
        <span className={`text-xs ${textColors[status]}`}>{label}</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center flex-1 min-w-[120px]">
      <div className="mb-2">{icons[status]}</div>
      <span className={`text-xs uppercase tracking-wider ${textColors[status]}`}>{label}</span>
      {description && <span className="text-[10px] text-gray-400 mt-1">{description}</span>}
    </div>
  );
}

interface PipelineProps {
  status: TaskStatus;
  compact?: boolean;
}

export default function PipelineView({ status, compact = false }: PipelineProps) {
  const getStepStatus = (step: string): 'complete' | 'active' | 'pending' | 'failed' => {
    const sequence = ['directive', 'routing', 'executing', 'review', 'merge'];
    const currentIndex = sequence.indexOf(
      status === 'pending' ? 'directive' :
      status === 'starting' ? 'routing' :
      status === 'in_progress' ? 'executing' :
      status === 'testing' ? 'review' :
      status === 'completed' ? 'merge' :
      status === 'failed' || status === 'rejected' ? 'failed' : 'directive'
    );

    const stepIndex = sequence.indexOf(step);

    if (status === 'failed' || status === 'rejected') {
      if (stepIndex < currentIndex) return 'complete';
      if (stepIndex === currentIndex) return 'failed';
      return 'pending';
    }

    if (stepIndex < currentIndex) return 'complete';
    if (stepIndex === currentIndex) return 'active';
    return 'pending';
  };

  const steps: { key: string; label: string }[] = [
    { key: 'directive', label: 'L1 Directive' },
    { key: 'routing', label: 'L2 Routing' },
    { key: 'executing', label: 'L3 Execution' },
    { key: 'review', label: 'Review' },
    { key: 'merge', label: 'Final Merge' },
  ];

  if (compact) {
    return (
      <div className="px-3 py-2 bg-gray-900 border-b border-gray-800">
        {steps.map(s => (
          <Step key={s.key} label={s.label} status={getStepStatus(s.key)} compact />
        ))}
      </div>
    );
  }

  return (
    <div className="flex items-center justify-between w-full py-4 px-2 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-100 dark:border-gray-700">
      <Step label="L1 Directive" status={getStepStatus('directive')} />
      <ArrowRight className="w-4 h-4 text-gray-300 shrink-0" />
      <Step label="L2 Routing" status={getStepStatus('routing')} />
      <ArrowRight className="w-4 h-4 text-gray-300 shrink-0" />
      <Step label="L3 Execution" status={getStepStatus('executing')} />
      <ArrowRight className="w-4 h-4 text-gray-300 shrink-0" />
      <Step label="Review" status={getStepStatus('review')} />
      <ArrowRight className="w-4 h-4 text-gray-300 shrink-0" />
      <Step label="Final Merge" status={getStepStatus('merge')} />
    </div>
  );
}
