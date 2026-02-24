'use client';

import { useState, useEffect } from 'react';
import { Lightbulb, ArrowRight, X } from 'lucide-react';
import Link from 'next/link';

export default function SuggestionToast() {
  const [count, setCount] = useState(0);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Initial check
    checkSuggestions();

    // Poll every 30 seconds for new suggestions
    const interval = setInterval(checkSuggestions, 30000);
    return () => clearInterval(interval);
  }, []);

  async function checkSuggestions() {
    try {
      const res = await fetch('/api/links/suggestions');
      const data = await res.json();
      if (data.length > 0) {
        setCount(data.length);
        setVisible(true);
      } else {
        setVisible(false);
      }
    } catch (err) {
      console.error('Failed to check suggestions:', err);
    }
  }

  if (!visible || count === 0) return null;

  return (
    <div className="fixed bottom-6 right-6 z-50 animate-in fade-in slide-in-from-bottom-4 duration-300">
      <div className="bg-blue-600 dark:bg-blue-500 text-white rounded-xl shadow-2xl p-4 pr-12 relative flex items-center gap-4 border border-blue-400 dark:border-blue-400/30">
        <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center shrink-0">
          <Lightbulb className="w-5 h-5 text-white" />
        </div>
        <div>
          <h4 className="text-sm font-bold">New Link Suggestions</h4>
          <p className="text-xs text-white/80">Found {count} potential links between decisions and issues.</p>
          <Link 
            href="/tasks/review" 
            className="mt-2 text-[10px] font-bold uppercase tracking-widest flex items-center gap-1 hover:underline"
            onClick={() => setVisible(false)}
          >
            Review Now
            <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
        <button 
          onClick={() => setVisible(false)}
          className="absolute top-3 right-3 text-white/60 hover:text-white transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
