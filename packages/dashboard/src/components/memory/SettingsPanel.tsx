'use client';

import { useState } from 'react';

export interface HealthSettings {
  scan_interval_ms: number;
  age_threshold_days: number;
  retrieval_window_days: number;
  similarity_min: number;
  similarity_max: number;
}

interface SettingsPanelProps {
  settings: HealthSettings;
  onUpdate: (settings: HealthSettings) => void;
  onClose: () => void;
}

const SCAN_INTERVAL_OPTIONS = [
  { label: 'Off', value: 0 },
  { label: '15 min', value: 15 * 60 * 1000 },
  { label: '30 min', value: 30 * 60 * 1000 },
  { label: '1 hour', value: 60 * 60 * 1000 },
  { label: '2 hours', value: 2 * 60 * 60 * 1000 },
];

export default function SettingsPanel({ settings, onUpdate, onClose }: SettingsPanelProps) {
  const [draft, setDraft] = useState<HealthSettings>({ ...settings });

  function handleIntervalChange(value: string) {
    setDraft(prev => ({ ...prev, scan_interval_ms: Number(value) }));
  }

  function handleNumberChange(field: keyof HealthSettings, value: string) {
    const num = parseFloat(value);
    if (!Number.isNaN(num)) {
      setDraft(prev => ({ ...prev, [field]: num }));
    }
  }

  function handleApply() {
    onUpdate(draft);
    onClose();
  }

  const labelClass = 'block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1';
  const inputClass =
    'w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent';

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/30"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Settings panel — anchored top-right below toolbar */}
      <div
        className="fixed right-4 top-16 z-50 w-80 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-xl"
        role="dialog"
        aria-modal="true"
        aria-label="Health Scan Settings"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 px-4 py-3">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
            Health Scan Settings
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            aria-label="Close settings"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Fields */}
        <div className="space-y-4 px-4 py-4">
          {/* Scan Interval */}
          <div>
            <label className={labelClass} htmlFor="setting-scan-interval">
              Scan Interval
            </label>
            <select
              id="setting-scan-interval"
              className={inputClass}
              value={draft.scan_interval_ms}
              onChange={e => handleIntervalChange(e.target.value)}
            >
              {SCAN_INTERVAL_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Age Threshold */}
          <div>
            <label className={labelClass} htmlFor="setting-age-threshold">
              Age Threshold (days)
            </label>
            <input
              id="setting-age-threshold"
              type="number"
              min={1}
              step={1}
              className={inputClass}
              value={draft.age_threshold_days}
              onChange={e => handleNumberChange('age_threshold_days', e.target.value)}
            />
          </div>

          {/* Retrieval Window */}
          <div>
            <label className={labelClass} htmlFor="setting-retrieval-window">
              Retrieval Window (days)
            </label>
            <input
              id="setting-retrieval-window"
              type="number"
              min={1}
              step={1}
              className={inputClass}
              value={draft.retrieval_window_days}
              onChange={e => handleNumberChange('retrieval_window_days', e.target.value)}
            />
          </div>

          {/* Min Similarity */}
          <div>
            <label className={labelClass} htmlFor="setting-sim-min">
              Min Similarity (conflict lower bound)
            </label>
            <input
              id="setting-sim-min"
              type="number"
              min={0}
              max={1}
              step={0.05}
              className={inputClass}
              value={draft.similarity_min}
              onChange={e => handleNumberChange('similarity_min', e.target.value)}
            />
          </div>

          {/* Max Similarity */}
          <div>
            <label className={labelClass} htmlFor="setting-sim-max">
              Max Similarity (duplicate upper bound)
            </label>
            <input
              id="setting-sim-max"
              type="number"
              min={0}
              max={1}
              step={0.01}
              className={inputClass}
              value={draft.similarity_max}
              onChange={e => handleNumberChange('similarity_max', e.target.value)}
            />
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 border-t border-gray-200 dark:border-gray-700 px-4 py-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleApply}
            className="rounded-md bg-blue-600 hover:bg-blue-700 px-3 py-1.5 text-sm font-medium text-white transition-colors"
          >
            Apply
          </button>
        </div>
      </div>
    </>
  );
}
