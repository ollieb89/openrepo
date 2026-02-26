'use client';

import { 
  Brain, 
  Play, 
  AlertCircle, 
  ShieldAlert, 
  CheckCircle,
  type LucideIcon 
} from 'lucide-react';

export type AutonomyState = 'planning' | 'executing' | 'blocked' | 'escalating' | 'complete';

interface StateConfig {
  color: string;
  icon: LucideIcon;
  label: string;
}

const stateConfig: Record<AutonomyState, StateConfig> = {
  planning: { 
    color: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300', 
    icon: Brain, 
    label: 'Planning' 
  },
  executing: { 
    color: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300', 
    icon: Play, 
    label: 'Executing' 
  },
  blocked: { 
    color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300', 
    icon: AlertCircle, 
    label: 'Blocked' 
  },
  escalating: { 
    color: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300', 
    icon: ShieldAlert, 
    label: 'Escalating' 
  },
  complete: { 
    color: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300', 
    icon: CheckCircle, 
    label: 'Complete' 
  },
};

interface AutonomyStateBadgeProps {
  state: AutonomyState;
}

export function AutonomyStateBadge({ state }: AutonomyStateBadgeProps) {
  const config = stateConfig[state];
  const Icon = config.icon;
  
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${config.color}`}>
      <Icon className="h-3 w-3" />
      {config.label}
    </span>
  );
}

export default AutonomyStateBadge;
