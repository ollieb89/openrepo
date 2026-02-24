'use client';

import PrivacyCenter from '@/components/privacy/PrivacyCenter';
import { useProject } from '@/context/ProjectContext';

export default function PrivacySettingsPage() {
  const { projectId } = useProject();

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">Privacy Settings</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Manage consent for remote inference and inspect privacy audit events.
        </p>
      </div>
      <PrivacyCenter projectId={projectId} />
    </div>
  );
}
