'use client';

import { useState, useEffect } from 'react';
import { Check, X, ExternalLink, Info, MessageSquare } from 'lucide-react';
import { apiPath } from '@/lib/api-client';

interface Suggestion {
  id: string;
  decision_id: string;
  issue_id: string;
  score: number;
  reasons: string[];
  decision_content: string;
  issue_content: string;
  issue_metadata: {
    provider: string;
    [key: string]: any;
  };
}

export default function LinkReviewPanel() {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSuggestions();
  }, []);

  async function fetchSuggestions() {
    try {
      const res = await fetch(apiPath('/api/links/suggestions'));
      const data = await res.json();
      setSuggestions(data);
    } catch (err) {
      console.error('Failed to fetch suggestions:', err);
    } finally {
      setLoading(false);
    }
  }

  async function handleAction(id: string, action: 'accept' | 'reject') {
    try {
      const res = await fetch(apiPath(`/api/links/suggestions/${id}/action`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      });

      if (res.ok) {
        setSuggestions(prev => prev.filter(s => s.id !== id));
      }
    } catch (err) {
      console.error(`Failed to ${action} suggestion:`, err);
    }
  }

  if (loading) {
    return <div className="p-8 text-center text-slate-500">Loading suggestions...</div>;
  }

  if (suggestions.length === 0) {
    return (
      <div className="bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-xl p-12 text-center">
        <div className="mx-auto w-12 h-12 bg-slate-100 dark:bg-slate-800 rounded-full flex items-center justify-center mb-4">
          <Check className="w-6 h-6 text-slate-400" />
        </div>
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-1">All clear!</h3>
        <p className="text-sm text-slate-500 dark:text-slate-400">No new link suggestions to review.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
          Link Review
          <span className="bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 text-xs px-2 py-0.5 rounded-full font-bold">
            {suggestions.length}
          </span>
        </h2>
        <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold">
          Review semantic matches across sources
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {suggestions.map((s) => (
          <div key={s.id} className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-sm hover:border-blue-300 dark:hover:border-blue-800 transition-all group">
            <div className="flex flex-col md:flex-row">
              {/* Decision Side */}
              <div className="flex-1 p-5 border-b md:border-b-0 md:border-r border-slate-100 dark:border-slate-800 bg-slate-50/30 dark:bg-slate-950/30">
                <div className="flex items-center gap-2 mb-3">
                  <MessageSquare className="w-4 h-4 text-blue-500" />
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Decision Outcome</span>
                </div>
                <p className="text-sm text-slate-800 dark:text-slate-200 font-medium line-clamp-3">
                  {s.decision_content.split('\n\nCitation:')[0]}
                </p>
              </div>

              {/* Link Logic */}
              <div className="flex flex-col items-center justify-center p-4 bg-white dark:bg-slate-900 z-10 md:-mx-2">
                <div className="w-8 h-8 rounded-full bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800 flex items-center justify-center mb-2">
                  <span className="text-[10px] font-bold text-blue-600">{Math.round(s.score * 100)}%</span>
                </div>
                <div className="h-full w-px bg-slate-100 dark:bg-slate-800 hidden md:block"></div>
              </div>

              {/* Issue Side */}
              <div className="flex-1 p-5 bg-slate-50/30 dark:bg-slate-950/30">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className="bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400 text-[10px] px-1.5 py-0.5 rounded font-mono font-bold">
                      {s.issue_id}
                    </span>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Related Issue</span>
                  </div>
                  <span className="text-[10px] bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 px-1.5 py-0.5 rounded-full font-bold">
                    {s.issue_metadata.provider}
                  </span>
                </div>
                <p className="text-sm text-slate-800 dark:text-slate-200 font-medium line-clamp-3">
                  {s.issue_content.split('\n\n')[0]}
                </p>
              </div>

              {/* Actions */}
              <div className="flex md:flex-col border-t md:border-t-0 md:border-l border-slate-100 dark:border-slate-800">
                <button 
                  onClick={() => handleAction(s.id, 'accept')}
                  className="flex-1 p-4 flex items-center justify-center text-green-600 hover:bg-green-50 dark:hover:bg-green-900/10 transition-colors border-r md:border-r-0 md:border-b border-slate-100 dark:border-slate-800"
                  title="Accept Link"
                >
                  <Check className="w-5 h-5" />
                </button>
                <button 
                  onClick={() => handleAction(s.id, 'reject')}
                  className="flex-1 p-4 flex items-center justify-center text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/10 transition-colors"
                  title="Dismiss"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>
            
            {/* Reasons footer */}
            <div className="px-5 py-2 border-t border-slate-100 dark:border-slate-800 flex items-center gap-4">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1">
                <Info className="w-3 h-3" /> Reasons:
              </span>
              <div className="flex gap-2">
                {s.reasons.map(r => (
                  <span key={r} className="text-[9px] font-bold text-blue-500 dark:text-blue-400 uppercase tracking-wider px-1.5 py-0.5 bg-blue-50 dark:bg-blue-900/20 rounded">
                    {r.replace('_', ' ')}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
