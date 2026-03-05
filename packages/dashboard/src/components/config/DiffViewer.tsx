'use client';

import { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { Save, RefreshCw, AlertCircle, CheckCircle2, History } from 'lucide-react';
import Card from '@/components/common/Card';
import { apiJson } from '@/lib/api-client';

interface StagedConfig {
    staged: Record<string, any>;
    live: Record<string, any>;
}

export default function DiffViewer() {
    const [data, setData] = useState<StagedConfig | null>(null);
    const [loading, setLoading] = useState(true);
    const [applying, setApplying] = useState(false);

    const fetchConfig = async () => {
        setLoading(true);
        try {
            const data = await apiJson<StagedConfig>('/api/config/staged');
            setData(data);
        } catch (err) {
            toast.error('Failed to fetch configuration');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchConfig();
    }, []);

    const handleApply = async () => {
        setApplying(true);
        try {
            await apiJson('/api/config/apply', { method: 'POST' });
            toast.success('Configuration applied successfully');
            fetchConfig();
        } catch (err) {
            toast.error(err instanceof Error ? err.message : 'Failed to apply configuration');
        } finally {
            setApplying(false);
        }
    };

    if (loading) {
        return <div className="animate-pulse space-y-4">
            <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded w-1/4" />
            <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded" />
        </div>;
    }

    if (!data) return null;

    const allKeys = Array.from(new Set([...Object.keys(data.live), ...Object.keys(data.staged)])).sort();
    const hasChanges = JSON.stringify(data.live) !== JSON.stringify(data.staged);

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                        <History className="w-5 h-5 text-blue-500" />
                        Configuration Reconciliation
                    </h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                        Compare staged changes in database with live `openclaw.json`
                    </p>
                </div>

                <div className="flex gap-2">
                    <button
                        onClick={fetchConfig}
                        className="p-2 text-gray-500 hover:text-blue-600 transition-colors"
                        title="Refresh"
                    >
                        <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
                    </button>

                    <button
                        onClick={handleApply}
                        disabled={!hasChanges || applying}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${hasChanges && !applying
                            ? 'bg-blue-600 hover:bg-blue-700 text-white shadow-lg shadow-blue-500/20'
                            : 'bg-gray-100 dark:bg-gray-800 text-gray-400 cursor-not-allowed border border-gray-200 dark:border-gray-700'
                            }`}
                    >
                        <Save className="w-4 h-4" />
                        {applying ? 'Applying...' : 'Apply Changes'}
                    </button>
                </div>
            </div>

            {!hasChanges && (
                <div className="flex items-center gap-3 p-4 bg-green-50 dark:bg-green-950/20 border border-green-200 dark:border-green-800 rounded-xl text-green-700 dark:text-green-400">
                    <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
                    <p className="text-sm">Everything is in sync. Live configuration matches staged state.</p>
                </div>
            )}

            <Card>
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                        <thead>
                            <tr className="border-b border-gray-100 dark:border-gray-700">
                                <th className="px-4 py-3 font-medium text-gray-500 dark:text-gray-400">Setting Key</th>
                                <th className="px-4 py-3 font-medium text-gray-500 dark:text-gray-400">Live Value</th>
                                <th className="px-4 py-3 font-medium text-gray-500 dark:text-gray-400">Staged (New)</th>
                                <th className="px-4 py-3 font-medium text-gray-500 dark:text-gray-400 w-16">Status</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-50 dark:divide-gray-800">
                            {allKeys.map(key => {
                                const live = data.live[key];
                                const staged = data.staged[key];
                                const changed = JSON.stringify(live) !== JSON.stringify(staged);

                                return (
                                    <tr key={key} className={changed ? 'bg-blue-50/30 dark:bg-blue-900/10' : ''}>
                                        <td className="px-4 py-4 font-mono text-xs text-gray-700 dark:text-gray-300">{key}</td>
                                        <td className="px-4 py-4 text-gray-500 dark:text-gray-500 break-all max-w-[200px]">
                                            {live !== undefined ? JSON.stringify(live) : <span className="italic text-gray-300 dark:text-gray-600">None</span>}
                                        </td>
                                        <td className="px-4 py-4 break-all max-w-[200px]">
                                            {staged !== undefined ? (
                                                <span className={changed ? 'text-blue-600 dark:text-blue-400 font-medium' : 'text-gray-700 dark:text-gray-300'}>
                                                    {JSON.stringify(staged)}
                                                </span>
                                            ) : (
                                                <span className="italic text-gray-300 dark:text-gray-600">Removed</span>
                                            )}
                                        </td>
                                        <td className="px-4 py-4 text-center">
                                            {changed ? (
                                                <AlertCircle className="w-4 h-4 text-amber-500" />
                                            ) : (
                                                <CheckCircle2 className="w-4 h-4 text-gray-300 dark:text-gray-600" />
                                            )}
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </Card>
        </div>
    );
}
