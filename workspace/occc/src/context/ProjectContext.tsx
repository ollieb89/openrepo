'use client';

import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import type { Project } from '@/lib/types';

interface ProjectContextValue {
  projectId: string | null;
  project: Project | null;
  projects: Project[];
  setProjectId: (id: string) => void;
  loading: boolean;
}

const ProjectContext = createContext<ProjectContextValue>({
  projectId: null,
  project: null,
  projects: [],
  setProjectId: () => {},
  loading: true,
});

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/projects')
      .then(res => res.json())
      .then(data => {
        const projectList = data.projects || [];
        setProjects(projectList);
        // Prefer localStorage, fall back to server active project
        const storedId = localStorage.getItem('occc-project');
        const activeId = storedId && projectList.some((p: Project) => p.id === storedId)
          ? storedId
          : data.activeId;
        setProjectId(activeId);
        if (activeId) localStorage.setItem('occc-project', activeId);
        const active = projectList.find((p: Project) => p.id === activeId);
        setProject(active || null);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const handleSetProjectId = (id: string) => {
    setProjectId(id);
    localStorage.setItem('occc-project', id);
    const found = projects.find(p => p.id === id);
    setProject(found || null);
  };

  return (
    <ProjectContext.Provider value={{ projectId, project, projects, setProjectId: handleSetProjectId, loading }}>
      {children}
    </ProjectContext.Provider>
  );
}

export const useProject = () => useContext(ProjectContext);
