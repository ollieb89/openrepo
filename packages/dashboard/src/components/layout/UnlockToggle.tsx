'use client';

import { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { Lock, Unlock, ShieldAlert } from 'lucide-react';
import { apiJson, apiFetch } from '@/lib/api-client';

export default function UnlockToggle() {
    const [unlocked, setUnlocked] = useState(false);
    const [writeMode, setWriteMode] = useState<'readonly' | 'staging' | 'autoapply'>('staging');
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        apiJson<{ unlocked: boolean, writeMode: 'readonly' | 'staging' | 'autoapply' }>('/api/config/unlock')
            .then(data => {
                setUnlocked(data.unlocked);
                setWriteMode(data.writeMode || 'staging');
                setLoading(false);
            })
            .catch(err => {
                console.error('Failed to fetch unlock state', err);
                setWriteMode('staging'); // Fallback to staging to keep it clickable
                setLoading(false);
            });
    }, []);

    const handleToggle = async () => {
        if (writeMode === 'readonly') {
            toast.error('Dashboard is in read-only mode (DASHBOARD_WRITE_MODE=readonly)');
            return;
        }

        const newState = !unlocked;
        setLoading(true);

        try {
            const data = await apiJson<{ unlocked: boolean }>('/api/config/unlock', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ unlocked: newState }),
            });

            setUnlocked(data.unlocked);
            toast.success(data.unlocked ? 'Editing unlocked for 30 minutes' : 'Editing locked');
        } catch (err) {
            toast.error(err instanceof Error ? err.message : 'Network error');
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="h-8 w-8 animate-pulse bg-gray-200 dark:bg-gray-700 rounded-md" />
        );
    }

    if (writeMode === 'readonly') {
        return (
            <div
                className="flex items-center gap-1.5 px-2 py-1 bg-amber-50 dark:bg-amber-950/30 text-amber-600 dark:text-amber-400 rounded-md border border-amber-200 dark:border-amber-800 text-xs font-medium cursor-not-allowed"
                title="Dashboard is in Read-Only mode"
            >
                <ShieldAlert className="w-3.5 h-3.5" />
                <span>Read-Only</span>
            </div>
        );
    }

    return (
        <button
            onClick={handleToggle}
            disabled={loading}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-colors border ${unlocked
                ? 'bg-green-50 dark:bg-green-950/30 text-green-700 dark:text-green-400 border-green-200 dark:border-green-800 hover:bg-green-100 dark:hover:bg-green-900/40'
                : 'bg-gray-50 dark:bg-gray-800 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700'
                }`}
            title={unlocked ? 'Editing is unlocked. Click to lock.' : 'Editing is locked. Click to unlock.'}
        >
            {unlocked ? (
                <>
                    <Unlock className="w-3.5 h-3.5" />
                    <span>Unlocked</span>
                </>
            ) : (
                <>
                    <Lock className="w-3.5 h-3.5" />
                    <span>Locked</span>
                </>
            )}
        </button>
    );
}
