'use client';

import AttentionQueue from '@/components/mission-control/AttentionQueue';
import LiveEventFeed from '@/components/mission-control/LiveEventFeed';
import SwarmStatusPanel from '@/components/mission-control/SwarmStatusPanel';
import TaskPulse from '@/components/mission-control/TaskPulse';
import { AlertSection } from '@/components/mission-control/AlertSection';

export default function MissionControlPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">Mission Control</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">Swarm status at a glance</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column: attention + task pulse */}
        <div className="space-y-6">
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-3">
              Attention Queue
            </h3>
            <AttentionQueue />
          </div>

          <TaskPulse />
        </div>

        {/* Middle column: live events */}
        <div>
          <LiveEventFeed />
        </div>

        {/* Right column: swarm status + alerts */}
        <div className="space-y-6">
          <SwarmStatusPanel />
          <AlertSection />
        </div>
      </div>
    </div>
  );
}
