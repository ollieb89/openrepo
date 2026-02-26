'use client';

import TaskBoard from '@/components/tasks/TaskBoard';

export default function TasksPage() {
  return (
    <div className="h-full">
      <div className="mb-6">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">Task Board</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          L3 specialist tasks across the development workflow
        </p>
      </div>
      <TaskBoard />
    </div>
  );
}
