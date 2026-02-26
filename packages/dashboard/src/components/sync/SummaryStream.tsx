'use client';

import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { StopCircle, AlertCircle, Loader2 } from 'lucide-react';

interface SummaryStreamProps {
  stream: ReadableStream | null;
  onComplete?: () => void;
}

interface Citation {
  id: string;
  type: string;
}

export function SummaryStream({ stream, onComplete }: SummaryStreamProps) {
  const [content, setContent] = useState('');
  const [citations, setCitations] = useState<Citation[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const readerRef = useRef<ReadableStreamDefaultReader | null>(null);

  useEffect(() => {
    if (!stream) return;

    const readStream = async () => {
      setIsLoading(true);
      setError(null);
      setContent('');
      setCitations([]);

      const reader = stream.getReader();
      readerRef.current = reader;
      const decoder = new TextDecoder();
      let buffer = '';

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (!line.trim()) continue;
            try {
              const data = JSON.parse(line);
              if (data.type === 'metadata') {
                setCitations(data.context || []);
              } else if (data.type === 'token') {
                setContent(prev => prev + data.token);
              }
            } catch (e) {
              console.error('Error parsing stream chunk:', e);
            }
          }
        }
      } catch (err: any) {
        if (err.name === 'AbortError') {
          console.log('Stream reading aborted');
        } else {
          setError('Failed to read response stream');
          console.error('Stream read error:', err);
        }
      } finally {
        setIsLoading(false);
        readerRef.current = null;
        if (onComplete) onComplete();
      }
    };

    readStream();

    return () => {
      if (readerRef.current) {
        readerRef.current.cancel();
      }
    };
  }, [stream, onComplete]);

  const handleInterrupt = () => {
    if (readerRef.current) {
      readerRef.current.cancel();
      setIsLoading(false);
    }
  };

  if (error) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
        <AlertCircle size={20} />
        <span>{error}</span>
      </div>
    );
  }

  if (!content && isLoading) {
    return (
      <div className="flex items-center gap-2 text-slate-500 italic p-4">
        <Loader2 className="animate-spin" size={20} />
        <span>Synthesizing your summary...</span>
      </div>
    );
  }

  return (
    <div className="relative bg-white border border-slate-200 rounded-lg shadow-sm p-6">
      <div className="prose prose-slate max-w-none">
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>

      {citations.length > 0 && (
        <div className="mt-6 pt-4 border-t border-slate-100">
          <h4 className="text-sm font-semibold text-slate-700 mb-2">Sources:</h4>
          <div className="flex flex-wrap gap-2">
            {citations.map((cite, idx) => (
              <span 
                key={idx}
                className="inline-flex items-center px-2 py-1 rounded bg-slate-100 text-slate-600 text-xs font-mono border border-slate-200"
              >
                [{cite.type}:{cite.id.substring(0, 6)}]
              </span>
            ))}
          </div>
        </div>
      )}

      {isLoading && (
        <button
          onClick={handleInterrupt}
          className="absolute top-4 right-4 flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-md text-slate-600 text-sm hover:bg-slate-50 transition-colors"
        >
          <StopCircle size={16} className="text-red-500" />
          <span>Stop</span>
        </button>
      )}
    </div>
  );
}
