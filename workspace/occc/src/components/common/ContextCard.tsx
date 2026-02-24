import React from 'react';
import { Decision } from '@/lib/types/decisions';
import { MessageSquare, ArrowRight } from 'lucide-react';
import Link from 'next/link';

interface ContextCardProps {
  decision: Decision;
}

export default function ContextCard({ decision }: ContextCardProps) {
  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg p-4 hover:border-blue-400 dark:hover:border-blue-500 transition-all group shadow-sm">
      <div className="flex items-start gap-3">
        <div className="mt-1 bg-blue-50 dark:bg-blue-900/20 p-2 rounded-lg text-blue-600 dark:text-blue-400">
          <MessageSquare className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-slate-900 dark:text-white line-clamp-2 mb-1 group-hover:text-blue-600 transition-colors">
            {decision.outcome}
          </h4>
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-3 italic line-clamp-1">
            &quot;{decision.citation}&quot;
          </p>
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">
              {new Date(decision.createdAt).toLocaleDateString()}
            </span>
            <Link 
              href="/decisions" 
              className="text-[10px] font-bold text-blue-600 uppercase tracking-wider flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity"
            >
              Details
              <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
