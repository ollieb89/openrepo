'use client';

import SuggestionsPanel from '@/components/suggestions/SuggestionsPanel';
import { useProject } from '@/context/ProjectContext';

export default function SuggestionsPage() {
  const { projectId } = useProject();
  return (
    <div className="flex-1 overflow-auto p-6">
      <SuggestionsPanel projectId={projectId} />
    </div>
  );
}
