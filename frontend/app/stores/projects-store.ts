// Projects Store - manages projects, creation, and paper assignments
import { create } from 'zustand';
import { projectsApi, papersApi } from '../lib/api-client';
import type { Project, Paper } from '../lib/types';

interface ProjectsState {
    // State
    projects: Project[];
    selectedProject: Project | null;
    projectPapers: Paper[];
    isCreating: boolean;
    newProjectName: string;
    newProjectDimensions: string;

    // Actions
    setSelectedProject: (project: Project | null) => void;
    setIsCreating: (creating: boolean) => void;
    setNewProjectName: (name: string) => void;
    setNewProjectDimensions: (dimensions: string) => void;
    fetchProjects: () => Promise<void>;
    fetchProjectPapers: (projectId: number) => Promise<Paper[]>;
    createProject: () => Promise<void>;
    deleteProject: (projectId: number) => Promise<void>;
    addPaperToProject: (projectId: number, paperId: string, title?: string) => Promise<void>;
    removePaperFromProject: (projectId: number, paperId: string) => Promise<void>;
}

export const useProjectsStore = create<ProjectsState>((set, get) => ({
    // Initial state
    projects: [],
    selectedProject: null,
    projectPapers: [],
    isCreating: false,
    newProjectName: "",
    newProjectDimensions: "",

    // Setters
    setSelectedProject: (project) => set({ selectedProject: project }),
    setIsCreating: (creating) => set({ isCreating: creating }),
    setNewProjectName: (name) => set({ newProjectName: name }),
    setNewProjectDimensions: (dimensions) => set({ newProjectDimensions: dimensions }),

    // Fetch all projects
    fetchProjects: async () => {
        try {
            const data = await projectsApi.list();
            set({ projects: data });
        } catch (e) {
            console.error("Failed to fetch projects", e);
        }
    },

    // Fetch papers for a specific project
    fetchProjectPapers: async (projectId) => {
        try {
            const data = await projectsApi.get(projectId);
            set({ projectPapers: data.papers });
            return data.papers;
        } catch (e) {
            console.error("Failed to fetch project papers", e);
            return [];
        }
    },

    // Create a new project
    createProject: async () => {
        const { newProjectName, newProjectDimensions, fetchProjects } = get();
        if (!newProjectName.trim()) return;

        try {
            await projectsApi.create(newProjectName, newProjectDimensions);
            set({
                newProjectName: "",
                newProjectDimensions: "",
                isCreating: false,
            });
            await fetchProjects();
        } catch (e) {
            console.error("Failed to create project", e);
        }
    },

    // Delete a project
    deleteProject: async (projectId) => {
        const { selectedProject, fetchProjects } = get();
        try {
            await projectsApi.delete(projectId);
            if (selectedProject?.id === projectId) {
                set({ selectedProject: null });
            }
            await fetchProjects();
        } catch (e) {
            console.error("Failed to delete project", e);
        }
    },

    // Add a paper to a project
    addPaperToProject: async (projectId, paperId, title) => {
        try {
            await projectsApi.addPaper(projectId, paperId, title);
            await get().fetchProjects();
        } catch (e) {
            console.error("Failed to add paper to project", e);
        }
    },

    // Remove a paper from a project
    removePaperFromProject: async (projectId, paperId) => {
        try {
            await projectsApi.removePaper(projectId, paperId);
            await get().fetchProjects();
        } catch (e) {
            console.error("Failed to remove paper from project", e);
        }
    },
}));
