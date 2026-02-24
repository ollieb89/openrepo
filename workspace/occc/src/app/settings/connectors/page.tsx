'use client';

import SlackConnectorCard from '@/components/connectors/SlackConnectorCard';
import SyncDashboard from '@/components/connectors/SyncDashboard';
import TrackerConnectorCard from '@/components/connectors/TrackerConnectorCard';
import SyncToast from '@/components/common/SyncToast';

export default function ConnectorsSettingsPage() {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">Connector Settings</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Manage workspace connectivity, source scope, and incremental sync controls.
        </p>
      </div>
      <SyncToast />
      <SyncDashboard />
      <div id="slack-connector">
        <SlackConnectorCard />
      </div>
      <div id="tracker-connector">
        <TrackerConnectorCard />
      </div>
    </div>
  );
}
