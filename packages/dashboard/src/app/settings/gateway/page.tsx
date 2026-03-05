'use client';

import DiffViewer from '@/components/config/DiffViewer';

export default function GatewaySettingsPage() {
    return (
        <div className="max-w-6xl mx-auto py-8 px-4">
            <div className="mb-8">
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Gateway Settings</h1>
                <p className="text-gray-500 dark:text-gray-400">
                    Manage the core OpenClaw gateway configuration and deployment settings.
                </p>
            </div>

            <div className="grid grid-cols-1 gap-8">
                {/* Placeholder for actual editor forms */}
                <div className="p-6 bg-white dark:bg-gray-800 rounded-xl border border-dashed border-gray-300 dark:border-gray-600 text-center">
                    <p className="text-gray-500 dark:text-gray-400 italic">
                        Config editor forms for Ports, Bindings, and Auth will be implemented here.
                        Currently, modifications should be made via the API or direct DB edits for staging.
                    </p>
                </div>

                <DiffViewer />
            </div>
        </div>
    );
}
