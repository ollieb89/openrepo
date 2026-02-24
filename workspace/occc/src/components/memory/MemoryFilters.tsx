import type { MemoryItem } from '@/lib/types/memory';

interface MemoryFiltersProps {
  items: MemoryItem[];
  category: string | null;
  agentType: string | null;
  type: string | null;
  onCategoryChange: (value: string | null) => void;
  onAgentTypeChange: (value: string | null) => void;
  onTypeChange: (value: string | null) => void;
}

const selectClass =
  'bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md px-3 py-1.5 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500';

function unique(values: (string | undefined)[]): string[] {
  return Array.from(new Set(values.filter((v): v is string => v != null && v !== ''))).sort();
}

export default function MemoryFilters({
  items,
  category,
  agentType,
  type,
  onCategoryChange,
  onAgentTypeChange,
  onTypeChange,
}: MemoryFiltersProps) {
  const categories = unique(items.map(i => i.category));
  const agentTypes = unique(items.map(i => i.agent_type));
  const types = unique(items.map(i => i.type));

  return (
    <div className="flex items-center gap-3 flex-wrap py-2">
      <select
        className={selectClass}
        value={category ?? ''}
        onChange={e => onCategoryChange(e.target.value || null)}
        aria-label="Filter by category"
      >
        <option value="">All Categories</option>
        {categories.map(c => (
          <option key={c} value={c}>{c}</option>
        ))}
      </select>

      <select
        className={selectClass}
        value={agentType ?? ''}
        onChange={e => onAgentTypeChange(e.target.value || null)}
        aria-label="Filter by agent source"
      >
        <option value="">All Agents</option>
        {agentTypes.map(a => (
          <option key={a} value={a}>{a}</option>
        ))}
      </select>

      <select
        className={selectClass}
        value={type ?? ''}
        onChange={e => onTypeChange(e.target.value || null)}
        aria-label="Filter by type"
      >
        <option value="">All Types</option>
        {types.map(t => (
          <option key={t} value={t}>{t}</option>
        ))}
      </select>
    </div>
  );
}
