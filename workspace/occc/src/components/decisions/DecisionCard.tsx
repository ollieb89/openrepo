'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, Link as LinkIcon, Lock, RotateCw, Trash2 } from 'lucide-react';
import { Decision } from '@/lib/types/decisions';

interface DecisionCardProps {
  decision: Decision;
  projectName?: string;
  onHide?: (id: string) => void;
  onReSummarize?: (id: string, hint?: string) => void;
}

export function DecisionCard({ decision, projectName, onHide, onReSummarize }: DecisionCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showReSummarizePopver, setShowReSummarizePopover] = useState(false);
  const [hint, setHint] = useState('');
  const [isUpdating, setIsUpdating] = useState(false);

  // Mock restricted check - in a real app, this would check against user's Slack permissions
  const isRestricted = false; 

  const handleHide = async () => {
    if (confirm('Are you sure you want to hide this decision?')) {
      onHide?.(decision.id);
    }
  };

  const handleReSummarize = async () => {
    setIsUpdating(true);
    await onReSummarize?.(decision.id, hint);
    setIsUpdating(false);
    setShowReSummarizePopover(false);
    setHint('');
  };

  const slackUrl = `slack://channel?team=T01234567&id=C01234567&message=${decision.threadId}`; // Mock IDs
  const slackWebUrl = `https://slack.com/archives/C01234567/p${decision.threadId.replace('.', '')}`;

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-sm overflow-hidden mb-4">
      {/* Header / Collapsed State */}
      <div 
        className="p-4 cursor-pointer flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400">
              {projectName || 'Project'}
            </span>
            <span className="text-xs text-slate-500">
              {new Date(decision.createdAt).toLocaleDateString()}
            </span>
            {isRestricted && (
              <span className="flex items-center gap-1 text-[10px] bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 px-1.5 py-0.5 rounded-full font-medium">
                <Lock className="w-2.5 h-2.5" />
                Source Restricted
              </span>
            )}
          </div>
          <h3 className="text-base font-medium text-slate-900 dark:text-white truncate">
            {decision.outcome}
          </h3>
        </div>
        <div className="flex items-center gap-3 ml-4">
          <button 
            onClick={(e) => { e.stopPropagation(); handleHide(); }}
            className="p-1.5 text-slate-400 hover:text-red-500 transition-colors"
            title="Hide decision"
          >
            <Trash2 className="w-4 h-4" />
          </button>
          {isExpanded ? <ChevronUp className="w-5 h-5 text-slate-400" /> : <ChevronDown className="w-5 h-5 text-slate-400" />}
        </div>
      </div>

      {/* Expanded State */}
      {isExpanded && (
        <div className="px-4 pb-4 border-t border-slate-100 dark:border-slate-800 pt-4 space-y-4">
          {/* Participants */}
          <div>
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Participants</h4>
            <div className="flex flex-wrap gap-1">
              {decision.participants.length > 0 ? (
                decision.participants.map(p => (
                  <span key={p} className="text-sm text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 px-2 py-0.5 rounded">
                    {p}
                  </span>
                ))
              ) : (
                <span className="text-sm text-slate-400 italic">No specific participants identified</span>
              )}
            </div>
          </div>

          {/* Next Steps */}
          {decision.nextStep && (
            <div>
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Next Steps</h4>
              <p className="text-sm text-slate-700 dark:text-slate-300">
                {decision.nextStep}
              </p>
            </div>
          )}

          {/* Citation / Provenance */}
          <div className="bg-slate-50 dark:bg-slate-950/50 rounded p-3 border border-slate-100 dark:border-slate-800">
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 flex items-center justify-between">
              Citation Snippet
              {!isRestricted && (
                <div className="flex items-center gap-3">
                  <a 
                    href={slackUrl} 
                    className="text-blue-600 hover:underline flex items-center gap-1"
                    title="Open in Slack App"
                  >
                    <LinkIcon className="w-3 h-3" />
                    App
                  </a>
                  <a 
                    href={slackWebUrl} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline flex items-center gap-1"
                    title="Open in Browser"
                  >
                    Web
                  </a>
                </div>
              )}
            </h4>
            <blockquote className="text-sm italic text-slate-600 dark:text-slate-400 border-l-2 border-slate-300 dark:border-slate-700 pl-3">
              &quot;{decision.citation}&quot;
            </blockquote>
          </div>

          {/* Correction Controls */}
          <div className="flex justify-end pt-2">
            <div className="relative">
              <button 
                onClick={() => setShowReSummarizePopover(!showReSummarizePopver)}
                className="flex items-center gap-2 text-xs font-medium text-slate-600 dark:text-slate-400 hover:text-blue-600 transition-colors"
                disabled={isUpdating}
              >
                <RotateCw className={`w-3 h-3 ${isUpdating ? 'animate-spin' : ''}`} />
                Re-summarize with Hints
              </button>

              {showReSummarizePopver && (
                <div className="absolute right-0 bottom-full mb-2 w-72 p-3 bg-white dark:bg-slate-800 rounded-lg shadow-xl border border-slate-200 dark:border-slate-700 z-10">
                  <h5 className="text-xs font-bold mb-2">Refine Summary</h5>
                  <textarea 
                    value={hint}
                    onChange={(e) => setHint(e.target.value)}
                    placeholder="e.g. Focus on the timeline discussed..."
                    className="w-full h-20 text-xs p-2 border border-slate-200 dark:border-slate-700 rounded bg-slate-50 dark:bg-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500 mb-2"
                  />
                  <div className="flex justify-end gap-2">
                    <button 
                      onClick={() => setShowReSummarizePopover(false)}
                      className="text-[10px] font-bold uppercase tracking-wider text-slate-400 hover:text-slate-600"
                    >
                      Cancel
                    </button>
                    <button 
                      onClick={handleReSummarize}
                      className="text-[10px] font-bold uppercase tracking-wider text-blue-600 hover:text-blue-700"
                    >
                      Apply
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
