'use client';

import { Bot } from 'lucide-react';
import Card from '@/components/common/Card';
import AutonomyStateBadge from './AutonomyStateBadge';
import ConfidenceIndicator from './ConfidenceIndicator';
import SelectedTools from './SelectedTools';
import type { AutonomyInfo } from '@/lib/types/autonomy';

interface AutonomyPanelProps {
  autonomy: AutonomyInfo;
}

export function AutonomyPanel({ autonomy }: AutonomyPanelProps) {
  return (
    <Card className="mt-4">
      <div className="p-4">
        <div className="flex items-center gap-2 mb-4">
          <Bot className="h-4 w-4 text-gray-500" />
          <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
            Autonomy
          </h4>
        </div>
        
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-500 dark:text-gray-400">State</span>
            <AutonomyStateBadge state={autonomy.state} />
          </div>
          
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-500 dark:text-gray-400">Confidence</span>
            <ConfidenceIndicator score={autonomy.confidence_score} />
          </div>
          
          <div className="flex justify-between items-start">
            <span className="text-sm text-gray-500 dark:text-gray-400 pt-0.5">Tools</span>
            <SelectedTools tools={autonomy.selected_tools} />
          </div>
        </div>
      </div>
    </Card>
  );
}

export default AutonomyPanel;
