import type { MemoryItem } from '@/lib/types/memory';
import MemoryRow from './MemoryRow';

interface MemoryTableProps {
  items: MemoryItem[];
  sortField: string;
  sortDirection: 'asc' | 'desc';
  onSort: (field: string) => void;
  expandedId: string | null;
  onToggleExpand: (id: string) => void;
  selectedIds: Set<string>;
  onToggleSelect: (id: string) => void;
  onSelectAll: () => void;
  onDeleteItem: (id: string) => void;
  deletingIds?: Set<string>;
}

type Column = {
  field: string;
  label: string;
};

const COLUMNS: Column[] = [
  { field: 'type', label: 'Type' },
  { field: 'category', label: 'Category' },
  { field: 'agent_type', label: 'Agent' },
  { field: 'created_at', label: 'Created' },
];

function SortIcon({ active, direction }: { active: boolean; direction: 'asc' | 'desc' }) {
  if (!active) {
    return (
      <svg className="w-3 h-3 text-gray-400 ml-1 inline" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M8 9l4-4 4 4M16 15l-4 4-4-4" />
      </svg>
    );
  }
  return direction === 'asc' ? (
    <svg className="w-3 h-3 text-blue-600 dark:text-blue-400 ml-1 inline" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 15l7-7 7 7" />
    </svg>
  ) : (
    <svg className="w-3 h-3 text-blue-600 dark:text-blue-400 ml-1 inline" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
    </svg>
  );
}

export default function MemoryTable({
  items,
  sortField,
  sortDirection,
  onSort,
  expandedId,
  onToggleExpand,
  selectedIds,
  onToggleSelect,
  onSelectAll,
  onDeleteItem,
  deletingIds = new Set(),
}: MemoryTableProps) {
  const allSelected = items.length > 0 && items.every(i => selectedIds.has(i.id));

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
      <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
        <thead className="bg-gray-50 dark:bg-gray-800">
          <tr>
            <th className="px-3 py-3 w-10">
              <input
                type="checkbox"
                checked={allSelected}
                onChange={onSelectAll}
                className="rounded border-gray-300 dark:border-gray-600 text-blue-600 focus:ring-blue-500"
                aria-label="Select all on page"
              />
            </th>
            {COLUMNS.map(col => (
              <th
                key={col.field}
                className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide cursor-pointer select-none hover:text-gray-700 dark:hover:text-gray-200 whitespace-nowrap"
                onClick={() => onSort(col.field)}
              >
                {col.label}
                <SortIcon active={sortField === col.field} direction={sortDirection} />
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
          {items.map(item => (
            <MemoryRow
              key={item.id}
              item={item}
              isExpanded={expandedId === item.id}
              onToggle={() => onToggleExpand(item.id)}
              isSelected={selectedIds.has(item.id)}
              onToggleSelect={() => onToggleSelect(item.id)}
              onDelete={() => onDeleteItem(item.id)}
              isDeleting={deletingIds.has(item.id)}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}
