'use client';

import { 
  FileText, 
  FileEdit, 
  Terminal, 
  Search, 
  GitBranch,
  type LucideIcon 
} from 'lucide-react';

export type ToolCategory = 'file_read' | 'file_write' | 'shell_execution' | 'web_search' | 'git_operations';

const toolIcons: Record<ToolCategory, LucideIcon> = {
  file_read: FileText,
  file_write: FileEdit,
  shell_execution: Terminal,
  web_search: Search,
  git_operations: GitBranch,
};

const toolLabels: Record<ToolCategory, string> = {
  file_read: 'File Read',
  file_write: 'File Write',
  shell_execution: 'Shell',
  web_search: 'Web Search',
  git_operations: 'Git',
};

interface SelectedToolsProps {
  tools: string[];
}

export function SelectedTools({ tools }: SelectedToolsProps) {
  if (tools.includes('all') || tools.length === 0) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
        All Tools
      </span>
    );
  }
  
  return (
    <div className="flex gap-1 flex-wrap">
      {tools.map(tool => {
        const Icon = toolIcons[tool as ToolCategory] || FileText;
        const label = toolLabels[tool as ToolCategory] || tool.replace(/_/g, ' ');
        
        return (
          <span 
            key={tool} 
            className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded border border-gray-200 dark:border-gray-600 text-xs bg-white dark:bg-gray-800"
          >
            <Icon className="h-3 w-3 text-gray-500" />
            <span className="capitalize">{label}</span>
          </span>
        );
      })}
    </div>
  );
}

export default SelectedTools;
