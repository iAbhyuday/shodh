// UI Store - manages UI state like sidebar, active view, modals
import { create } from 'zustand';
import type { Paper, ViewType, ProjectView, MindMapNode } from '../lib/types';

interface UIState {
    // Navigation
    sidebarOpen: boolean;
    activeView: ViewType;
    projectView: ProjectView;
    scrolled: boolean;

    // Modals & Panels
    settingsOpen: boolean;
    quickReadPaper: Paper | null;
    isQuickReadOpen: boolean;
    activeProjectMenu: string | null;

    // Ideas/Visualization Modal
    activePaper: Paper | null;
    viewMode: 'ideas' | 'vis' | 'none';
    generating: boolean;
    ideas: string[];
    mindMapData: MindMapNode | null;

    // Actions
    toggleSidebar: () => void;
    setSidebarOpen: (open: boolean) => void;
    setActiveView: (view: ViewType) => void;
    setProjectView: (view: ProjectView) => void;
    setScrolled: (scrolled: boolean) => void;
    setSettingsOpen: (open: boolean) => void;
    openQuickRead: (paper: Paper) => void;
    closeQuickRead: () => void;
    setActiveProjectMenu: (paperId: string | null) => void;
    openIdeasModal: (paper: Paper) => void;
    openVisModal: (paper: Paper) => void;
    closeModal: () => void;
    setGenerating: (generating: boolean) => void;
    setIdeas: (ideas: string[]) => void;
    setMindMapData: (data: MindMapNode | null) => void;
}

export const useUIStore = create<UIState>((set) => ({
    // Initial state
    sidebarOpen: true,
    activeView: 'explore',
    projectView: 'papers',
    scrolled: false,
    settingsOpen: false,
    quickReadPaper: null,
    isQuickReadOpen: false,
    activeProjectMenu: null,
    activePaper: null,
    viewMode: 'none',
    generating: false,
    ideas: [],
    mindMapData: null,

    // Navigation actions
    toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
    setSidebarOpen: (open) => set({ sidebarOpen: open }),
    setActiveView: (view) => set({ activeView: view }),
    setProjectView: (view) => set({ projectView: view }),
    setScrolled: (scrolled) => set({ scrolled }),

    // Modal/Panel actions
    setSettingsOpen: (open) => set({ settingsOpen: open }),

    openQuickRead: (paper) => set({
        quickReadPaper: paper,
        isQuickReadOpen: true
    }),

    closeQuickRead: () => set({ isQuickReadOpen: false }),

    setActiveProjectMenu: (paperId) => set({ activeProjectMenu: paperId }),

    // Ideas/Visualization modal
    openIdeasModal: (paper) => set({
        activePaper: paper,
        viewMode: 'ideas',
        generating: true,
        ideas: [],
    }),

    openVisModal: (paper) => set({
        activePaper: paper,
        viewMode: 'vis',
        generating: true,
        mindMapData: null,
    }),

    closeModal: () => set({
        viewMode: 'none',
        activePaper: null
    }),

    setGenerating: (generating) => set({ generating }),
    setIdeas: (ideas) => set({ ideas }),
    setMindMapData: (data) => set({ mindMapData: data }),
}));
