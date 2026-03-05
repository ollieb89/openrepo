'use client';

import { useState, useMemo } from 'react';
import type { Task, TaskStatus } from '@/lib/types';
import Card from '../common/Card';

interface TaskDataTableProps {
  tasks: Task[] | null;
  loading?: boolean;
  totalCount?: number;
  currentPage?: number;
  pageSize?: number;
  onPageChange?: (page: number) => void;
}

type SortField = 'id' | 'status' | 'skill_hint' | 'created_at' | 'updated_at';
type SortDirection = 'asc' | 'desc';

interface SortState {
  field: SortField;
  direction: SortDirection;
}

const STATUS_COLORS: Record<TaskStatus, string> = {
  pending: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
  in_progress: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  starting: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
  testing: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-400',
  completed: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  failed: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  rejected: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400',
  escalating: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
};

function TaskDataTableSkeleton() {
  return (
    <div className="animate-pulse space-y-3">
      {/* Header */}
      <div className="flex gap-2 pb-2 border-b border-gray-200 dark:border-gray-700">
        {[1, 2, 3, 4, 5].map(i => (
          <div key={i} className="h-4 bg-gray-200 dark:bg-gray-700 rounded flex-1" />
        ))}
      </div>
      {/* Rows */}
      {[1, 2, 3, 4, 5].map(i => (
        <div key={i} className="flex gap-2 py-2">
          {[1, 2, 3, 4, 5].map(j => (
            <div key={j} className="h-4 bg-gray-200 dark:bg-gray-700 rounded flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="h-48 flex flex-col items-center justify-center gap-3">
      <div className="flex items-center justify-center w-12 h-12 rounded-full bg-gray-100 dark:bg-gray-800">
        <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
      </div>
      <p className="text-sm text-gray-400 dark:text-gray-500">
        No tasks found
      </p>
    </div>
  );
}

function formatDate(timestamp: number): string {
  const date = new Date(timestamp * 1000);
  return date.toLocaleDateString('en-US', { 
    month: 'short', 
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

function formatStatus(status: TaskStatus): string {
  return status.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
}

export function TaskDataTable({ 
  tasks, 
  loading, 
  totalCount = 0,
  currentPage = 1,
  pageSize = 10,
  onPageChange 
}: TaskDataTableProps) {
  const [sort, setSort] = useState<SortState>({ field: 'updated_at', direction: 'desc' });
  const [filterStatus, setFilterStatus] = useState<TaskStatus | 'all'>('all');
  const [filterText, setFilterText] = useState('');

  // Filter and sort tasks
  const filteredAndSortedTasks = useMemo(() => {
    if (!tasks) return [];

    let result = [...tasks];

    // Apply status filter
    if (filterStatus !== 'all') {
      result = result.filter(t => t.status === filterStatus);
    }

    // Apply text filter
    if (filterText.trim()) {
      const search = filterText.toLowerCase();
      result = result.filter(t => 
        t.id.toLowerCase().includes(search) ||
        t.skill_hint.toLowerCase().includes(search)
      );
    }

    // Apply sorting
    result.sort((a, b) => {
      let comparison = 0;
      switch (sort.field) {
        case 'id':
          comparison = a.id.localeCompare(b.id);
          break;
        case 'status':
          comparison = a.status.localeCompare(b.status);
          break;
        case 'skill_hint':
          comparison = a.skill_hint.localeCompare(b.skill_hint);
          break;
        case 'created_at':
          comparison = a.created_at - b.created_at;
          break;
        case 'updated_at':
          comparison = a.updated_at - b.updated_at;
          break;
      }
      return sort.direction === 'asc' ? comparison : -comparison;
    });

    return result;
  }, [tasks, sort, filterStatus, filterText]);

  // Pagination
  const totalPages = Math.ceil(filteredAndSortedTasks.length / pageSize);
  const paginatedTasks = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredAndSortedTasks.slice(start, start + pageSize);
  }, [filteredAndSortedTasks, currentPage, pageSize]);

  function handleSort(field: SortField) {
    setSort(prev => ({
      field,
      direction: prev.field === field && prev.direction === 'asc' ? 'desc' : 'asc'
    }));
  }

  function handleExport() {
    if (!filteredAndSortedTasks.length) return;

    const headers = ['ID', 'Status', 'Skill', 'Created', 'Updated'];
    const rows = filteredAndSortedTasks.map(t => [
      t.id,
      t.status,
      t.skill_hint,
      new Date(t.created_at * 1000).toISOString(),
      new Date(t.updated_at * 1000).toISOString()
    ]);

    const csv = [headers.join(','), ...rows.map(r => r.map(cell => `"${cell}"`).join(','))].join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `tasks-${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function renderSortIcon(field: SortField) {
    if (sort.field !== field) {
      return <span className="text-gray-300 dark:text-gray-600">↕</span>;
    }
    return sort.direction === 'asc' ? 
      <span className="text-blue-500">↑</span> : 
      <span className="text-blue-500">↓</span>;
  }

  const exportButton = (
    <button
      onClick={handleExport}
      disabled={!filteredAndSortedTasks.length}
      className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
    >
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
      </svg>
      Export
    </button>
  );

  if (loading) {
    return (
      <Card title="Task Details" action={exportButton}>
        <div className="p-4">
          <TaskDataTableSkeleton />
        </div>
      </Card>
    );
  }

  return (
    <Card title="Task Details" action={exportButton}>
      <div className="p-4">
        {/* Filters */}
        <div className="flex flex-wrap gap-3 mb-4">
          <div className="flex-1 min-w-[200px]">
            <input
              type="text"
              placeholder="Search tasks..."
              value={filterText}
              onChange={(e) => setFilterText(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value as TaskStatus | 'all')}
            className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="all">All Status</option>
            <option value="pending">Pending</option>
            <option value="in_progress">In Progress</option>
            <option value="starting">Starting</option>
            <option value="testing">Testing</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>

        {filteredAndSortedTasks.length === 0 ? (
          <EmptyState />
        ) : (
          <>
            {/* Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-gray-700">
                    <th 
                      className="text-left py-2 px-3 font-medium text-gray-700 dark:text-gray-300 cursor-pointer hover:text-gray-900 dark:hover:text-white select-none"
                      onClick={() => handleSort('id')}
                    >
                      <div className="flex items-center gap-1">
                        ID {renderSortIcon('id')}
                      </div>
                    </th>
                    <th 
                      className="text-left py-2 px-3 font-medium text-gray-700 dark:text-gray-300 cursor-pointer hover:text-gray-900 dark:hover:text-white select-none"
                      onClick={() => handleSort('status')}
                    >
                      <div className="flex items-center gap-1">
                        Status {renderSortIcon('status')}
                      </div>
                    </th>
                    <th 
                      className="text-left py-2 px-3 font-medium text-gray-700 dark:text-gray-300 cursor-pointer hover:text-gray-900 dark:hover:text-white select-none"
                      onClick={() => handleSort('skill_hint')}
                    >
                      <div className="flex items-center gap-1">
                        Skill {renderSortIcon('skill_hint')}
                      </div>
                    </th>
                    <th 
                      className="text-left py-2 px-3 font-medium text-gray-700 dark:text-gray-300 cursor-pointer hover:text-gray-900 dark:hover:text-white select-none"
                      onClick={() => handleSort('created_at')}
                    >
                      <div className="flex items-center gap-1">
                        Created {renderSortIcon('created_at')}
                      </div>
                    </th>
                    <th 
                      className="text-left py-2 px-3 font-medium text-gray-700 dark:text-gray-300 cursor-pointer hover:text-gray-900 dark:hover:text-white select-none"
                      onClick={() => handleSort('updated_at')}
                    >
                      <div className="flex items-center gap-1">
                        Updated {renderSortIcon('updated_at')}
                      </div>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedTasks.map(task => (
                    <tr 
                      key={task.id}
                      className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                    >
                      <td className="py-2 px-3 font-mono text-xs text-gray-900 dark:text-white truncate max-w-[150px]">
                        {task.id}
                      </td>
                      <td className="py-2 px-3">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[task.status]}`}>
                          {formatStatus(task.status)}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-gray-700 dark:text-gray-300 truncate max-w-[200px]">
                        {task.skill_hint}
                      </td>
                      <td className="py-2 px-3 text-gray-500 dark:text-gray-400 whitespace-nowrap">
                        {formatDate(task.created_at)}
                      </td>
                      <td className="py-2 px-3 text-gray-500 dark:text-gray-400 whitespace-nowrap">
                        {formatDate(task.updated_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Showing {((currentPage - 1) * pageSize) + 1} - {Math.min(currentPage * pageSize, filteredAndSortedTasks.length)} of {filteredAndSortedTasks.length}
                </p>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => onPageChange?.(currentPage - 1)}
                    disabled={currentPage <= 1}
                    className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    Previous
                  </button>
                  <span className="text-sm text-gray-700 dark:text-gray-300">
                    Page {currentPage} of {totalPages}
                  </span>
                  <button
                    onClick={() => onPageChange?.(currentPage + 1)}
                    disabled={currentPage >= totalPages}
                    className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </Card>
  );
}

export default TaskDataTable;
