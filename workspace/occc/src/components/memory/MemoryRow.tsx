'use client';

import { useState } from 'react';
import type { MemoryItem } from '@/lib/types/memory';
import type { HealthFlag } from './HealthTab';

interface MemoryRowProps {
  item: MemoryItem;
  isExpanded: boolean;
  onToggle: () => void;
  isSelected: boolean;
  onToggleSelect: () => void;
  onDelete: () => void;
  isDeleting?: boolean;
  healthFlag?: HealthFlag;
  onOpenConflict?: (flag: HealthFlag) => void;
}

const CONTENT_CAP = 300;

const AGENT_BADGE_COLORS: Record<string, string> = {
  l2_pm: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  l3_code: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
  l3_test: 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300',
};

const DEFAULT_BADGE = 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300';

function agentBadgeClass(agentType: string | undefined): string {
  if (!agentType) return DEFAULT_BADGE;
  return AGENT_BADGE_COLORS[agentType] ?? DEFAULT_BADGE;
}

function formatDate(value: string | number | undefined): string {
  if (value == null) return '—';
  const ms = typeof value === 'number' ? value * 1000 : Date.parse(value);
  if (Number.isNaN(ms)) return String(value);
  const date = new Date(ms);
  const now = Date.now();
  const diffMs = now - date.getTime();
  const diffH = diffMs / (1000 * 60 * 60);
  if (diffH < 24) {
    const h = Math.round(diffH);
    return h < 1 ? 'just now' : `${h}h ago`;
  }
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

const pillClass = 'inline-block rounded-full px-2 py-0.5 text-xs font-medium';

function Badge({ value, color }: { value: string | undefined; color?: string }) {
  if (!value) return <span className="text-gray-400 dark:text-gray-600">—</span>;
  return (
    <span className={`${pillClass} ${color ?? DEFAULT_BADGE}`}>{value}</span>
  );
}

const EXCLUDED_COLUMNS = new Set(['id', 'content', 'category', 'agent_type', 'type', 'created_at', 'user_id', 'metadata']);

export default function MemoryRow({
  item,
  isExpanded,
  onToggle,
  isSelected,
  onToggleSelect,
  onDelete,
  isDeleting = false,
  healthFlag,
  onOpenConflict,
}: MemoryRowProps) {
  const [showMore, setShowMore] = useState(false);

  const content = item.content ?? '';
  const isTruncated = content.length > CONTENT_CAP;
  const displayContent = showMore || !isTruncated ? content : content.slice(0, CONTENT_CAP) + '…';

  // Extra metadata keys beyond the standard columns
  const extraKeys = Object.keys(item).filter(k => !EXCLUDED_COLUMNS.has(k));

  return (
    <>
      <tr
        className={`hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer transition-opacity duration-300 ${isDeleting ? 'opacity-0' : 'opacity-100'}`}
        onClick={e => {
          // Don't toggle expand when clicking checkbox
          if ((e.target as HTMLElement).closest('input[type="checkbox"]')) return;
          onToggle();
        }}
      >
        <td className="px-3 py-3 w-10" onClick={e => e.stopPropagation()}>
          <input
            type="checkbox"
            checked={isSelected}
            onChange={onToggleSelect}
            className="rounded border-gray-300 dark:border-gray-600 text-blue-600 focus:ring-blue-500"
            aria-label="Select row"
          />
        </td>
        <td className="px-4 py-3 text-sm whitespace-nowrap">
          <Badge value={item.type} color={DEFAULT_BADGE} />
        </td>
        <td className="px-4 py-3 text-sm whitespace-nowrap">
          <Badge value={item.category} color="bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300" />
        </td>
        <td className="px-4 py-3 text-sm whitespace-nowrap">
          <Badge value={item.agent_type} color={agentBadgeClass(item.agent_type)} />
        </td>
        <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400 whitespace-nowrap">
          {formatDate(item.created_at)}
        </td>
        <td className="px-4 py-3 text-sm whitespace-nowrap">
          {healthFlag && (
            <button
              type="button"
              onClick={e => {
                e.stopPropagation();
                if (healthFlag.flag_type === 'conflict' && onOpenConflict) {
                  onOpenConflict(healthFlag);
                }
              }}
              className={`${pillClass} cursor-pointer ${
                healthFlag.flag_type === 'stale'
                  ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300'
                  : 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
              }`}
            >
              {healthFlag.flag_type}
            </button>
          )}
        </td>
      </tr>

      {isExpanded && (
        <tr className="bg-gray-50 dark:bg-gray-800/50">
          <td colSpan={5} className="px-4 py-4">
            <div className="space-y-3">
              {/* Content */}
              <div>
                <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1 uppercase tracking-wide">
                  Content
                </p>
                <p className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap break-words">
                  {displayContent}
                </p>
                {isTruncated && (
                  <button
                    type="button"
                    onClick={() => setShowMore(v => !v)}
                    className="mt-1 text-xs text-blue-600 dark:text-blue-400 hover:underline focus:outline-none"
                  >
                    {showMore ? 'Show less' : 'Show more'}
                  </button>
                )}
              </div>

              {/* Metadata */}
              <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm">
                <div className="text-gray-500 dark:text-gray-400 text-xs font-semibold uppercase tracking-wide col-span-2 mt-1">
                  Metadata
                </div>
                <div className="flex gap-2">
                  <span className="text-gray-500 dark:text-gray-400 text-xs">ID</span>
                  <span className="font-mono text-xs text-gray-700 dark:text-gray-300 truncate">{item.id}</span>
                </div>
                {item.user_id && (
                  <div className="flex gap-2">
                    <span className="text-gray-500 dark:text-gray-400 text-xs">User ID</span>
                    <span className="font-mono text-xs text-gray-700 dark:text-gray-300">{item.user_id}</span>
                  </div>
                )}
                {item.metadata && Object.keys(item.metadata).length > 0 && (
                  <div className="col-span-2">
                    <span className="text-gray-500 dark:text-gray-400 text-xs">Metadata</span>
                    <pre className="mt-0.5 text-xs text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-900 rounded p-2 overflow-auto max-h-32">
                      {JSON.stringify(item.metadata, null, 2)}
                    </pre>
                  </div>
                )}
                {extraKeys.map(k => (
                  <div key={k} className="flex gap-2">
                    <span className="text-gray-500 dark:text-gray-400 text-xs">{k}</span>
                    <span className="text-xs text-gray-700 dark:text-gray-300 truncate">
                      {String(item[k])}
                    </span>
                  </div>
                ))}
              </div>

              {/* Delete button */}
              <div className="pt-1">
                <button
                  type="button"
                  onClick={onDelete}
                  className="bg-red-600 text-white px-3 py-1 rounded text-sm hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-1"
                >
                  Delete
                </button>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
