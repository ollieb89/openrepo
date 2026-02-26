'use client';

import React, { useState } from 'react';
import { Search, Info, Pin, Share2, Sparkles, AlertCircle } from 'lucide-react';
import { SummaryStream } from '@/components/sync/SummaryStream';

export default function CatchUpPage() {
  const [query, setQuery] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [stream, setStream] = useState<ReadableStream | null>(null);
  const [suggestions, setSuggestions] = useState<any[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent, forcedId?: string) => {
    e.preventDefault();
    if (!query.trim() && !forcedId) return;

    setIsSubmitting(true);
    setError(null);
    setStream(null);
    setSuggestions(null);

    try {
      const res = await fetch('/api/sync/catch-up', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          query: forcedId ? `${query} (id: ${forcedId})` : query,
          activeProjectId: 'default' // Should be dynamically selected if project selection is implemented
        }),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || 'Failed to start catch-up');
      }

      const contentType = res.headers.get('Content-Type');
      if (contentType?.includes('application/json')) {
        const data = await res.json();
        if (data.confidence === 'low') {
          setSuggestions(data.suggestions);
          setIsSubmitting(false);
          return;
        }
      }

      if (res.body) {
        setStream(res.body);
      } else {
        throw new Error('No response stream received');
      }
    } catch (err: any) {
      setError(err.message);
      setIsSubmitting(false);
    }
  };

  const handleComplete = () => {
    setIsSubmitting(false);
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="flex flex-col items-center mb-12">
        <div className="w-12 h-12 bg-blue-600 text-white rounded-xl flex items-center justify-center mb-4 shadow-lg shadow-blue-200">
          <Sparkles size={24} fill="currentColor" />
        </div>
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Catch Me Up</h1>
        <p className="text-slate-500 text-center max-w-lg">
          Get a natural language summary of what's happened across your sources.
          Try "What's the status of the auth bug?" or "Summarize recent activity in Slack."
        </p>
      </div>

      <form onSubmit={(e) => handleSubmit(e)} className="mb-8">
        <div className="relative group">
          <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none text-slate-400 group-focus-within:text-blue-500 transition-colors">
            <Search size={20} />
          </div>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={isSubmitting}
            placeholder="Ask anything about your project..."
            className="w-full pl-12 pr-4 py-4 bg-white border border-slate-200 rounded-2xl shadow-sm outline-none focus:ring-4 focus:ring-blue-100 focus:border-blue-400 transition-all text-lg"
          />
          <button
            type="submit"
            disabled={isSubmitting || !query.trim()}
            className="absolute right-2 top-2 bottom-2 px-6 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors"
          >
            {isSubmitting ? 'Thinking...' : 'Go'}
          </button>
        </div>
      </form>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      )}

      {/* Clarification Picker Placeholder for Task 2 */}
      {suggestions && (
        <div className="mb-8 p-6 bg-amber-50 border border-amber-200 rounded-xl">
          <h3 className="text-amber-800 font-semibold mb-3 flex items-center gap-2">
            <Info size={18} />
            Wait, I found multiple possibilities. Which one did you mean?
          </h3>
          <div className="grid grid-cols-1 gap-3">
            {suggestions.map((s: any) => (
              <button
                key={s.id}
                onClick={(e) => handleSubmit(e as any, s.id)}
                className="text-left p-4 bg-white border border-amber-100 rounded-lg hover:border-amber-400 hover:shadow-md transition-all group"
              >
                <div className="text-xs font-bold text-amber-600 uppercase mb-1">{s.type}</div>
                <div className="text-slate-700">{s.content}</div>
              </button>
            ))}
          </div>
        </div>
      )}

      {(stream || (isSubmitting && !suggestions)) && (
        <div className="space-y-6">
          <SummaryStream stream={stream} onComplete={handleComplete} />
          
          {/* Summary Controls Placeholder for Task 2 */}
          {!isSubmitting && stream && (
            <div className="flex justify-between items-center bg-slate-50 p-4 rounded-lg border border-slate-100">
              <div className="flex gap-4">
                <button className="flex items-center gap-2 text-sm text-slate-600 hover:text-blue-600 transition-colors">
                  <Pin size={16} />
                  <span>Pin to Project</span>
                </button>
                <button className="flex items-center gap-2 text-sm text-slate-600 hover:text-blue-600 transition-colors">
                  <Share2 size={16} />
                  <span>Share</span>
                </button>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400 italic">Enhanced with Cloud AI</span>
                <div className="w-8 h-4 bg-slate-200 rounded-full relative">
                  <div className="absolute left-1 top-1 w-2 h-2 bg-white rounded-full"></div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
