// Projects Store - manages projects, creation, and paper assignments
import { create } from 'zustand';
import { projectsApi } from '../lib/api-client';
import type { Project, Paper } from '../lib/types';

interface ProjectsState {
    // State
    projects: Project[];
    selectedProject: Project | null;
    projectPapers: Paper[];
    isCreating: boolean;
    newProjectName: string;
    newProjectDimensions: string;
    editingProject: Project | null;

    // Actions
    setSelectedProject: (project: Project | null) => void;
    setIsCreating: (creating: boolean) => void;
    setEditingProject: (project: Project | null) => void;
    setNewProjectName: (name: string) => void;
    setNewProjectDimensions: (dimensions: string) => void;
    fetchProjects: () => Promise<void>;
    fetchProjectPapers: (projectId: string) => Promise<Paper[]>;
    createProject: () => Promise<void>;
    updateProject: () => Promise<void>;
    deleteProject: (projectId: string) => Promise<void>;
    addPaperToProject: (projectId: string, paperId: string, title?: string, summary?: string, authors?: string, url?: string, published_date?: string, thumbnail?: string, tags?: string[], github_url?: string, project_page?: string) => Promise<void>;
    removePaperFromProject: (projectId: string, paperId: string) => Promise<void>;
}

export const useProjectsStore = create<ProjectsState>((set, get) => ({
    // Initial state
    projects: [],
    selectedProject: null,
    projectPapers: [],
    isCreating: false,
    newProjectName: "",
    newProjectDimensions: "",
    editingProject: null,

    // Setters
    setSelectedProject: (project) => set({ selectedProject: project }),
    setIsCreating: (creating) => {
        set({ isCreating: creating });
        // Reset form if closing
        if (!creating) {
            set({
                newProjectName: "",
                newProjectDimensions: "",
                editingProject: null
            });
        }
    },
    setEditingProject: (project) => {
        if (project) {
            set({
                editingProject: project,
                newProjectName: project.name,
                newProjectDimensions: project.research_dimensions || "",
                isCreating: true // Open form
            });
        } else {
            set({ editingProject: null, isCreating: false });
        }
    },
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

    // Update an existing project
    updateProject: async () => {
        const { editingProject, newProjectName, newProjectDimensions, fetchProjects } = get();
        if (!editingProject || !newProjectName.trim()) return;

        try {
            await projectsApi.update(editingProject.id, newProjectName, newProjectDimensions);
            set({
                newProjectName: "",
                newProjectDimensions: "",
                isCreating: false,
                editingProject: null,
            });
            await fetchProjects();
        } catch (e) {
            console.error("Failed to update project", e);
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
    addPaperToProject: async (projectId, paperId, title, summary, authors, url, published_date, thumbnail, tags, github_url, project_page) => {
        try {
            await projectsApi.addPaper(projectId, paperId, title, summary, authors, url, published_date, thumbnail, tags, github_url, project_page);
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
