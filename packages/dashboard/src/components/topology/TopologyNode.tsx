'use client';

import React from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps, Node } from '@xyflow/react';

// ---------------------------------------------------------------------------
// Data type for the custom node
// ---------------------------------------------------------------------------

export interface TopologyNodeData extends Record<string, unknown> {
  id: string;
  level: 1 | 2 | 3;
  intent: string;
  risk_level: 'low' | 'medium' | 'high';
  highlight?: 'added' | 'removed' | 'modified';
}

export type TopologyNodeType = Node<TopologyNodeData, 'topologyNode'>;

// ---------------------------------------------------------------------------
// Visual mappings
// ---------------------------------------------------------------------------

// Level-based border colors (no highlight override)
const LEVEL_BORDER: Record<1 | 2 | 3, string> = {
  1: 'border-purple-400',
  2: 'border-blue-400',
  3: 'border-gray-400',
};

// Diff highlight styles override level colors
const HIGHLIGHT_STYLES: Record<string, string> = {
  added:    'border-green-500 bg-green-50 dark:bg-green-900/20',
  removed:  'border-red-500 bg-red-50 dark:bg-red-900/20 opacity-70',
  modified: 'border-yellow-500 bg-yellow-50 dark:bg-yellow-900/20',
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function TopologyNodeComponent({ data, selected }: NodeProps<TopologyNodeType>) {
  const highlight = data.highlight;
  const level = data.level as 1 | 2 | 3;

  const borderClass = highlight
    ? HIGHLIGHT_STYLES[highlight]
    : `${LEVEL_BORDER[level] ?? 'border-gray-400'} bg-white dark:bg-gray-800`;

  return (
    <div
      className={[
        'relative flex flex-col justify-center px-3 py-2 rounded-md border-2',
        'text-sm shadow-sm min-w-[160px] max-w-[180px]',
        borderClass,
        selected ? 'ring-2 ring-blue-500 ring-offset-1' : '',
        'transition-all duration-150',
      ].join(' ')}
    >
      {/* Target handle (top) for TB layout */}
      <Handle type="target" position={Position.Top} className="!bg-gray-400" />

      {/* Node content */}
      <span className="font-semibold text-gray-900 dark:text-gray-100 truncate leading-tight">
        {data.id}
      </span>
      <span className="text-xs text-gray-500 dark:text-gray-400 truncate leading-tight mt-0.5">
        {data.intent}
      </span>
      {highlight && (
        <span className="absolute top-0.5 right-1 text-[9px] font-bold uppercase tracking-wide opacity-70">
          {highlight}
        </span>
      )}

      {/* Source handle (bottom) for TB layout */}
      <Handle type="source" position={Position.Bottom} className="!bg-gray-400" />
    </div>
  );
}

export default TopologyNodeComponent;
