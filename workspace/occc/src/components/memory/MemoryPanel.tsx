'use client';

import { useState, useMemo, useEffect } from 'react';
import { toast } from 'react-toastify';
import { useMemory } from '@/lib/hooks/useMemory';
import { useProject } from '@/context/ProjectContext';
import type { MemoryItem } from '@/lib/types/memory';
import MemoryStatBar from './MemoryStatBar';
import MemoryFilters from './MemoryFilters';
import MemoryTable from './MemoryTable';
import MemorySearch from './MemorySearch';
import ConfirmDialog from './ConfirmDialog';

const PAGE_SIZE = 25;
// Fade-out animation duration in ms
const DELETE_ANIMATION_MS = 300;

type SortField = 'type' | 'category' | 'agent_type' | 'created_at';
type SortDirection = 'asc' | 'desc';

function sortItems(items: MemoryItem[], field: SortField, direction: SortDirection): MemoryItem[] {
  return [...items].sort((a, b) => {
    let aVal: string | number | undefined;
    let bVal: string | number | undefined;

    if (field === 'created_at') {
      aVal = typeof a.created_at === 'number' ? a.created_at : a.created_at ? new Date(a.created_at).getTime() : 0;
      bVal = typeof b.created_at === 'number' ? b.created_at : b.created_at ? new Date(b.created_at).getTime() : 0;
    } else {
      aVal = (a[field] as string | undefined) ?? '';
      bVal = (b[field] as string | undefined) ?? '';
    }

    if (aVal === bVal) return 0;
    const cmp = aVal < bVal ? -1 : 1;
    return direction === 'asc' ? cmp : -cmp;
  });
}

type DialogState =
  | { type: 'none' }
  | { type: 'single'; id: string }
  | { type: 'bulk'; ids: Set<string> };

export default function MemoryPanel() {
  const { projectId } = useProject();

  // Search state
  const [searchQuery, setSearchQuery] = useState<string | null>(null);

  const { items, isLoading, error, mutate } = useMemory(projectId, searchQuery);

  // Filter state
  const [filterCategory, setFilterCategory] = useState<string | null>(null);
  const [filterAgentType, setFilterAgentType] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<string | null>(null);

  // Sort state — default newest first
  const [sortField, setSortField] = useState<SortField>('created_at');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  // Expand + select state
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // Pagination
  const [page, setPage] = useState(1);

  // Delete confirmation dialog
  const [dialog, setDialog] = useState<DialogState>({ type: 'none' });

  // Deleting IDs for fade-out animation
  const [deletingIds, setDeletingIds] = useState<Set<string>>(new Set());

  // Reset search when project changes
  useEffect(() => {
    setSearchQuery(null);
    setPage(1);
  }, [projectId]);

  // Reset page when searchQuery changes
  useEffect(() => {
    setPage(1);
  }, [searchQuery]);

  function handleSort(field: string) {
    const f = field as SortField;
    if (f === sortField) {
      setSortDirection(d => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(f);
      setSortDirection('asc');
    }
    setPage(1);
  }

  function handleToggleExpand(id: string) {
    setExpandedId(prev => (prev === id ? null : id));
  }

  function handleToggleSelect(id: string) {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function handleSelectAll() {
    if (selectedIds.size === pageItems.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(pageItems.map(i => i.id)));
    }
  }

  function handleFilterChange(setter: (v: string | null) => void) {
    return (value: string | null) => {
      setter(value);
      setPage(1);
    };
  }

  // --- Delete single item ---
  function openSingleDelete(id: string) {
    setDialog({ type: 'single', id });
  }

  async function confirmSingleDelete() {
    if (dialog.type !== 'single') return;
    const id = dialog.id;
    setDialog({ type: 'none' });

    // Start fade-out animation
    setDeletingIds(prev => new Set(Array.from(prev).concat([id])));

    // Wait for animation before removing from cache
    await new Promise(resolve => setTimeout(resolve, DELETE_ANIMATION_MS));

    try {
      const res = await fetch(`/api/memory/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      // Optimistically remove from SWR cache
      await mutate(
        prev => prev ? { ...prev, items: prev.items.filter(i => i.id !== id), total: Math.max(0, prev.total - 1) } : prev,
        false
      );
      toast.success('Memory item deleted');
    } catch {
      toast.error('Failed to delete memory item');
      // Re-fetch to sync state
      await mutate();
    } finally {
      setDeletingIds(prev => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }

    // Clean up expand state
    setExpandedId(prev => (prev === id ? null : prev));
    setSelectedIds(prev => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  }

  // --- Delete bulk ---
  function openBulkDelete() {
    if (selectedIds.size === 0) return;
    setDialog({ type: 'bulk', ids: new Set(selectedIds) });
  }

  async function confirmBulkDelete() {
    if (dialog.type !== 'bulk') return;
    const ids = dialog.ids;
    setDialog({ type: 'none' });

    // Start fade-out animation on all targeted IDs
    setDeletingIds(prev => new Set(Array.from(prev).concat(Array.from(ids))));

    await new Promise(resolve => setTimeout(resolve, DELETE_ANIMATION_MS));

    try {
      await Promise.all(Array.from(ids).map(id => fetch(`/api/memory/${id}`, { method: 'DELETE' }).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status} for ${id}`); })));

      // Optimistically remove from SWR cache
      await mutate(
        prev => prev ? { ...prev, items: prev.items.filter(i => !ids.has(i.id)), total: Math.max(0, prev.total - ids.size) } : prev,
        false
      );
      toast.success(`Deleted ${ids.size} memory item${ids.size !== 1 ? 's' : ''}`);
      setSelectedIds(new Set());
    } catch {
      toast.error('Some items could not be deleted');
      // Full refetch to sync state
      await mutate();
    } finally {
      setDeletingIds(prev => {
        const next = new Set(prev);
        ids.forEach(id => next.delete(id));
        return next;
      });
    }
  }

  // Filtered items
  const filteredItems = useMemo(() => {
    return items.filter(item => {
      if (filterCategory && item.category !== filterCategory) return false;
      if (filterAgentType && item.agent_type !== filterAgentType) return false;
      if (filterType && item.type !== filterType) return false;
      return true;
    });
  }, [items, filterCategory, filterAgentType, filterType]);

  // Sorted items
  const sortedItems = useMemo(
    () => sortItems(filteredItems, sortField, sortDirection),
    [filteredItems, sortField, sortDirection]
  );

  // Pagination
  const totalPages = Math.max(1, Math.ceil(sortedItems.length / PAGE_SIZE));
  const clampedPage = Math.min(page, totalPages);
  const pageItems = sortedItems.slice((clampedPage - 1) * PAGE_SIZE, clampedPage * PAGE_SIZE);

  const isConfirmOpen = dialog.type !== 'none';
  const confirmTitle = dialog.type === 'bulk'
    ? `Delete ${dialog.ids.size} item${dialog.ids.size !== 1 ? 's' : ''}?`
    : 'Delete memory item?';
  const confirmMessage = dialog.type === 'bulk'
    ? `Delete ${dialog.ids.size} memory item${dialog.ids.size !== 1 ? 's' : ''}? This cannot be undone.`
    : 'This memory item will be permanently removed. This cannot be undone.';

  function handleConfirm() {
    if (dialog.type === 'single') confirmSingleDelete();
    else if (dialog.type === 'bulk') confirmBulkDelete();
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">Memory</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Project-scoped memory items for the active project
        </p>
      </div>

      {/* Search bar */}
      <MemorySearch
        onSearch={q => setSearchQuery(q)}
        onClear={() => setSearchQuery(null)}
        isSearchMode={!!searchQuery}
        searchQuery={searchQuery ?? ''}
      />

      <MemoryStatBar items={items} />

      <MemoryFilters
        items={items}
        category={filterCategory}
        agentType={filterAgentType}
        type={filterType}
        onCategoryChange={handleFilterChange(setFilterCategory)}
        onAgentTypeChange={handleFilterChange(setFilterAgentType)}
        onTypeChange={handleFilterChange(setFilterType)}
      />

      {/* Bulk delete button */}
      {selectedIds.size > 0 && (
        <div className="flex items-center gap-3 py-1">
          <button
            type="button"
            onClick={openBulkDelete}
            className="flex items-center gap-1.5 rounded-md bg-red-600 hover:bg-red-700 px-3 py-1.5 text-sm font-medium text-white transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            Delete selected ({selectedIds.size})
          </button>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {selectedIds.size} item{selectedIds.size !== 1 ? 's' : ''} selected
          </span>
        </div>
      )}

      {isLoading && (
        <div className="flex items-center justify-center py-16 text-gray-400 dark:text-gray-500">
          <svg className="animate-spin w-6 h-6 mr-2" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Loading memory items...
        </div>
      )}

      {!isLoading && error && (
        <div className="rounded-md border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 px-4 py-3 text-sm text-red-700 dark:text-red-300">
          Failed to load memory items. Please try again.
        </div>
      )}

      {!isLoading && !error && sortedItems.length === 0 && (
        <div className="flex items-center justify-center py-16 text-gray-400 dark:text-gray-500 text-sm">
          {searchQuery
            ? `No memory items found for "${searchQuery}".`
            : 'No memory items found' + ((filterCategory || filterAgentType || filterType) ? ' matching current filters.' : '.')}
        </div>
      )}

      {!isLoading && !error && sortedItems.length > 0 && (
        <>
          <MemoryTable
            items={pageItems}
            sortField={sortField}
            sortDirection={sortDirection}
            onSort={handleSort}
            expandedId={expandedId}
            onToggleExpand={handleToggleExpand}
            selectedIds={selectedIds}
            onToggleSelect={handleToggleSelect}
            onSelectAll={handleSelectAll}
            onDeleteItem={openSingleDelete}
            deletingIds={deletingIds}
          />

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-2">
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Page {clampedPage} of {totalPages} &middot; {sortedItems.length} items
              </p>
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={clampedPage === 1}
                  className="rounded px-2 py-1 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  &laquo; Prev
                </button>
                {Array.from({ length: totalPages }, (_, i) => i + 1)
                  .filter(p => p === 1 || p === totalPages || Math.abs(p - clampedPage) <= 2)
                  .reduce<(number | 'ellipsis')[]>((acc, p, idx, arr) => {
                    if (idx > 0 && p - (arr[idx - 1] as number) > 1) acc.push('ellipsis');
                    acc.push(p);
                    return acc;
                  }, [])
                  .map((p, idx) =>
                    p === 'ellipsis' ? (
                      <span key={`ellipsis-${idx}`} className="px-1 text-gray-400">…</span>
                    ) : (
                      <button
                        key={p}
                        type="button"
                        onClick={() => setPage(p as number)}
                        className={`rounded px-2.5 py-1 text-sm ${
                          clampedPage === p
                            ? 'bg-blue-600 text-white'
                            : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                        }`}
                      >
                        {p}
                      </button>
                    )
                  )}
                <button
                  type="button"
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={clampedPage === totalPages}
                  className="rounded px-2 py-1 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Next &raquo;
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Confirmation dialog */}
      <ConfirmDialog
        isOpen={isConfirmOpen}
        title={confirmTitle}
        message={confirmMessage}
        confirmLabel="Delete"
        onConfirm={handleConfirm}
        onCancel={() => setDialog({ type: 'none' })}
      />
    </div>
  );
}
