'use client';

import { useState, useEffect } from 'react';
import Card from '@/components/common/Card';

interface NotificationSettingsState {
  desktop: boolean;
  sound: boolean;
  minConfidence: number;
}

const STORAGE_KEY = 'occc_notification_settings';

const defaultSettings: NotificationSettingsState = {
  desktop: true,
  sound: false,
  minConfidence: 0.4,
};

export function NotificationSettings() {
  const [settings, setSettings] = useState<NotificationSettingsState>(defaultSettings);
  const [isLoaded, setIsLoaded] = useState(false);

  // Load settings from localStorage on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        try {
          const parsed = JSON.parse(stored);
          setSettings({ ...defaultSettings, ...parsed });
        } catch (err) {
          console.error('Failed to parse notification settings:', err);
        }
      }
      setIsLoaded(true);
    }
  }, []);

  // Save settings to localStorage when changed
  useEffect(() => {
    if (isLoaded && typeof window !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    }
  }, [settings, isLoaded]);

  // Request notification permission when desktop is enabled
  const handleDesktopChange = async (enabled: boolean) => {
    if (enabled && typeof window !== 'undefined' && 'Notification' in window) {
      const permission = await Notification.requestPermission();
      if (permission !== 'granted') {
        // Don't enable if permission denied
        setSettings(prev => ({ ...prev, desktop: false }));
        return;
      }
    }
    setSettings(prev => ({ ...prev, desktop: enabled }));
  };

  const handleConfidenceChange = (value: number) => {
    setSettings(prev => ({ ...prev, minConfidence: value / 100 }));
  };

  if (!isLoaded) {
    return (
      <Card>
        <div className="p-6">
          <p className="text-gray-500">Loading settings...</p>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <div className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Escalation Notifications
        </h3>
        
        <div className="space-y-6">
          {/* Desktop Notifications */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <label className="text-sm font-medium text-gray-900 dark:text-white">
                Desktop Notifications
              </label>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Show browser notification on escalation
              </p>
            </div>
            <button
              onClick={() => handleDesktopChange(!settings.desktop)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                settings.desktop 
                  ? 'bg-blue-600' 
                  : 'bg-gray-200 dark:bg-gray-700'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  settings.desktop ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {/* Sound Alerts */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <label className="text-sm font-medium text-gray-900 dark:text-white">
                Sound Alerts
              </label>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Play sound when escalation occurs
              </p>
            </div>
            <button
              onClick={() => setSettings(prev => ({ ...prev, sound: !prev.sound }))}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                settings.sound 
                  ? 'bg-blue-600' 
                  : 'bg-gray-200 dark:bg-gray-700'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  settings.sound ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {/* Minimum Confidence Threshold */}
          <div className="space-y-3">
            <div>
              <label className="text-sm font-medium text-gray-900 dark:text-white">
                Minimum Confidence Threshold
              </label>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Only notify when confidence below this threshold
              </p>
            </div>
            
            <div className="flex items-center gap-4">
              <input
                type="range"
                min="0"
                max="100"
                step="10"
                value={Math.round(settings.minConfidence * 100)}
                onChange={(e) => handleConfidenceChange(parseInt(e.target.value))}
                className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-600"
              />
              <span className="text-sm font-medium text-gray-900 dark:text-white w-12 text-right">
                {Math.round(settings.minConfidence * 100)}%
              </span>
            </div>
            
            <div className="flex justify-between text-xs text-gray-400">
              <span>Notify on all escalations</span>
              <span>Only critical escalations</span>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}

export default NotificationSettings;
