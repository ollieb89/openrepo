'use client';

import { useState, useRef, useEffect } from 'react';

export type TimeRange = '7d' | '30d' | '90d' | 'all' | 'custom';

export interface CustomRange {
  start: Date;
  end: Date;
}

interface TimeRangeSelectorProps {
  value: TimeRange;
  customRange?: CustomRange;
  onChange: (range: TimeRange, customRange?: CustomRange) => void;
}

const RANGE_OPTIONS: { value: TimeRange; label: string; days?: number }[] = [
  { value: '7d', label: '7d', days: 7 },
  { value: '30d', label: '30d', days: 30 },
  { value: '90d', label: '90d', days: 90 },
  { value: 'all', label: 'All' },
  { value: 'custom', label: 'Custom ▼' },
];

export function TimeRangeSelector({ value, customRange, onChange }: TimeRangeSelectorProps) {
  const [showCustomPicker, setShowCustomPicker] = useState(false);
  const [localStart, setLocalStart] = useState('');
  const [localEnd, setLocalEnd] = useState('');
  const pickerRef = useRef<HTMLDivElement>(null);

  // Close picker when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (pickerRef.current && !pickerRef.current.contains(event.target as Node)) {
        setShowCustomPicker(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Initialize local dates from customRange
  useEffect(() => {
    if (customRange) {
      setLocalStart(formatDateForInput(customRange.start));
      setLocalEnd(formatDateForInput(customRange.end));
    }
  }, [customRange]);

  function formatDateForInput(date: Date): string {
    return date.toISOString().split('T')[0];
  }

  function handleRangeClick(range: TimeRange) {
    if (range === 'custom') {
      // Initialize with default range (last 30 days)
      const end = new Date();
      const start = new Date();
      start.setDate(start.getDate() - 30);
      
      setLocalStart(formatDateForInput(start));
      setLocalEnd(formatDateForInput(end));
      setShowCustomPicker(true);
    } else {
      onChange(range);
    }
  }

  function handleCustomApply() {
    if (localStart && localEnd) {
      const start = new Date(localStart);
      const end = new Date(localEnd);
      end.setHours(23, 59, 59, 999); // Include the full end day
      
      onChange('custom', { start, end });
      setShowCustomPicker(false);
    }
  }

  return (
    <div className="relative" ref={pickerRef}>
      <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
        {RANGE_OPTIONS.map((option) => (
          <button
            key={option.value}
            onClick={() => handleRangeClick(option.value)}
            className={`
              px-3 py-1.5 text-sm font-medium rounded-md transition-colors
              ${value === option.value
                ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-200 dark:hover:bg-gray-700'
              }
            `}
          >
            {option.value === 'custom' && value === 'custom' && customRange
              ? `${formatDateForInput(customRange.start)} - ${formatDateForInput(customRange.end)}`
              : option.label}
          </button>
        ))}
      </div>

      {/* Custom Range Picker Dropdown */}
      {showCustomPicker && (
        <div className="absolute top-full left-0 mt-2 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-4 z-50 min-w-[280px]">
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
            Select date range
          </p>
          <div className="space-y-3">
            <div>
              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                Start date
              </label>
              <input
                type="date"
                value={localStart}
                onChange={(e) => setLocalStart(e.target.value)}
                max={localEnd || formatDateForInput(new Date())}
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                End date
              </label>
              <input
                type="date"
                value={localEnd}
                onChange={(e) => setLocalEnd(e.target.value)}
                min={localStart}
                max={formatDateForInput(new Date())}
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 mt-4">
            <button
              onClick={() => setShowCustomPicker(false)}
              className="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleCustomApply}
              disabled={!localStart || !localEnd}
              className="px-3 py-1.5 text-sm bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Apply
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default TimeRangeSelector;
