"use client";
import React, { useEffect, useState, useCallback } from 'react';
import { ChevronLeft, ChevronRight, Compass, Heart, FolderArchive, Settings, RefreshCw } from 'lucide-react';
import { useRouter, usePathname } from 'next/navigation';
import { useShallow } from 'zustand/shallow';

// Components
import SettingsModal from './SettingsModal';
import NotificationBell from './NotificationBell';
import QuickReadPanel from './QuickReadPanel';
import { ShodhLogo } from './ShodhLogo';
import InteractiveMindMap from './InteractiveMindMap';

// Stores
import { usePapersStore, useProjectsStore, useUIStore } from '../stores';

// Hooks
import { useQuickRead, useIdeas, useIngestionPolling } from '../hooks';

// Types
import type { Paper, IngestionStatus } from '../lib/types';

export default function AppShell({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const pathname = usePathname();

    // --- Zustand Store Selectors ---
    // We need these stores here for Sidebar, Header, and Global Modals (QuickRead, Ideas)

    const {
        feed, loading, fetchFeed,
    } = usePapersStore(useShallow((s) => ({
        feed: s.feed,
        loading: s.loading,
        fetchFeed: s.fetchFeed,
    })));

    const { projects, fetchProjects, selectedProject, setSelectedProject } = useProjectsStore(useShallow((s) => ({
        projects: s.projects,
        fetchProjects: s.fetchProjects,
        selectedProject: s.selectedProject,
        setSelectedProject: s.setSelectedProject,
    })));

    const {
        sidebarOpen, setSidebarOpen, toggleSidebar,
        settingsOpen, setSettingsOpen,
        activePaper, viewMode, generating, ideas, mindMapData,
        openIdeasModal, openVisModal, closeModal, setGenerating, setIdeas, setMindMapData,
        activeProjectMenu, setActiveProjectMenu,
    } = useUIStore(useShallow((s) => ({
        sidebarOpen: s.sidebarOpen,
        setSidebarOpen: s.setSidebarOpen,
        toggleSidebar: s.toggleSidebar,
        settingsOpen: s.settingsOpen,
        setSettingsOpen: s.setSettingsOpen,
        activePaper: s.activePaper,
        viewMode: s.viewMode,
        generating: s.generating,
        ideas: s.ideas,
        mindMapData: s.mindMapData,
        openIdeasModal: s.openIdeasModal,
        openVisModal: s.openVisModal,
        closeModal: s.closeModal,
        setGenerating: s.setGenerating,
        setIdeas: s.setIdeas,
        setMindMapData: s.setMindMapData,
        activeProjectMenu: s.activeProjectMenu,
        setActiveProjectMenu: s.setActiveProjectMenu,
    })));

    // --- Custom Hooks ---

    const { quickReadPaper, isQuickReadOpen, studyInsights, isLoadingInsights, handleQuickRead, closeQuickRead } = useQuickRead();

    const { generateIdeas, visualize } = useIdeas({
        onOpenIdeas: openIdeasModal,
        onOpenVis: openVisModal,
        onSetIdeas: setIdeas,
        onSetMindMapData: setMindMapData,
        onSetGenerating: setGenerating,
    });

    // --- Local State ---
    const [ingestionStatus, setIngestionStatus] = useState<Record<string, IngestionStatus>>({});

    const { checkPaperStatus } = useIngestionPolling({
        feed,
        onStatusUpdate: setIngestionStatus
    });

    // --- Effects ---
    useEffect(() => {
        fetchProjects();
    }, [fetchProjects]);

    // Collapse sidebar on Deep Read pages
    useEffect(() => {
        if (pathname.startsWith('/paper/')) {
            setSidebarOpen(false);
        }
    }, [pathname, setSidebarOpen]);

    // Handle clicking outside to close project menu
    useEffect(() => {
        if (!activeProjectMenu) return;
        const handleGlobalClick = () => setActiveProjectMenu(null);
        const timeout = setTimeout(() => {
            window.addEventListener('click', handleGlobalClick);
        }, 10);
        return () => {
            clearTimeout(timeout);
            window.removeEventListener('click', handleGlobalClick);
        };
    }, [activeProjectMenu, setActiveProjectMenu]);

    // --- Handlers ---
    const handleDeepRead = useCallback((paper: Paper) => {
        router.push(`/paper/${paper.id}`);
    }, [router]);

    return (
        <div className="min-h-screen bg-black text-gray-100 font-sans">
            {/* Header */}
            <header className="bg-black/80 backdrop-blur-md border-b border-white/10 sticky top-0 z-[100]">
                <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
                    <div className="flex items-center space-x-2">
                        <ShodhLogo className="w-6 h-6" />
                        <h1 className="text-xl font-bold text-white">Shodh (शोध)</h1>
                    </div>
                    <div className="flex items-center gap-3">
                        <NotificationBell ingestionStatus={ingestionStatus} />
                        <button onClick={() => fetchFeed()} className="p-2 hover:bg-neutral-800 rounded-full transition text-gray-400 hover:text-white" title="Refresh Feed">
                            <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
                        </button>
                    </div>
                </div>
            </header>

            {/* Sidebar */}
            <aside className={`fixed left-0 top-16 h-[calc(100vh-4rem)] bg-neutral-900 border-r border-white/10 flex flex-col transition-all duration-300 ease-in-out z-[90] ${sidebarOpen ? 'w-64' : 'w-16'}`}>
                <nav className="flex-1 space-y-2 p-2">
                    <button
                        onClick={() => {
                            setSelectedProject(null);
                            router.push('/');
                        }}
                        title="Research Discovery"
                        className={`w-full flex items-center py-3 rounded-lg transition-all ${sidebarOpen ? 'gap-3 px-3' : 'justify-center px-2'} ${pathname === '/' ? 'bg-indigo-600 text-white font-semibold shadow-lg shadow-indigo-500/20' : 'text-gray-400 hover:bg-neutral-800 hover:text-white'}`}
                    >
                        <Compass className="w-5 h-5 flex-shrink-0" />
                        <span className={`transition-opacity duration-200 ${sidebarOpen ? 'opacity-100' : 'opacity-0 w-0 overflow-hidden'}`}>Research Discovery</span>
                    </button>

                    <button
                        onClick={() => {
                            setSelectedProject(null);
                            router.push('/favorites');
                        }}
                        title="Personal Collection"
                        className={`w-full flex items-center py-3 rounded-lg transition-all ${sidebarOpen ? 'gap-3 px-3' : 'justify-center px-2'} ${pathname === '/favorites' ? 'bg-indigo-600 text-white font-semibold shadow-lg shadow-indigo-500/20' : 'text-gray-400 hover:bg-neutral-800 hover:text-white'}`}
                    >
                        <Heart className="w-5 h-5 flex-shrink-0" />
                        <span className={`transition-opacity duration-200 ${sidebarOpen ? 'opacity-100' : 'opacity-0 w-0 overflow-hidden'}`}>Personal Collection</span>
                    </button>

                    <button
                        onClick={() => router.push('/projects')}
                        title="Synthesis Hub"
                        className={`w-full flex items-center py-3 rounded-lg transition-all ${sidebarOpen ? 'gap-3 px-3' : 'justify-center px-2'} ${pathname.startsWith('/projects') ? 'bg-indigo-600 text-white font-semibold shadow-lg shadow-indigo-500/20' : 'text-gray-400 hover:bg-neutral-800 hover:text-white'}`}
                    >
                        <FolderArchive className="w-5 h-5 flex-shrink-0" />
                        <span className={`transition-opacity duration-200 ${sidebarOpen ? 'opacity-100' : 'opacity-0 w-0 overflow-hidden'}`}>Synthesis Hub</span>
                    </button>

                    {/* Recent Projects */}
                    {sidebarOpen && projects.length > 0 && (
                        <div className="mt-4 px-3 py-2">
                            <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-2 px-1">Recent Projects</p>
                            <div className="space-y-1">
                                {projects.slice(0, 5).map(proj => (
                                    <button
                                        key={proj.id}
                                        onClick={() => {
                                            setSelectedProject(proj);
                                            setSidebarOpen(false);
                                            // Force navigation to projects page if not already there, 
                                            // but typically selecting a project should open it.
                                            // For now, let's just go to /projects which will show the selected project
                                            router.push('/projects');
                                        }}
                                        className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-sm transition-colors ${pathname.startsWith('/projects') && selectedProject?.id === proj.id ? 'bg-indigo-600/20 text-indigo-400 font-medium' : 'text-gray-400 hover:bg-white/5 hover:text-gray-200'}`}
                                    >
                                        <div className={`w-1.5 h-1.5 rounded-full ${selectedProject?.id === proj.id ? 'bg-indigo-500' : 'bg-neutral-600'}`} />
                                        <span className="truncate">{proj.name}</span>
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}
                </nav>

                {/* Sidebar Footer */}
                <div className="p-2 border-t border-white/10 space-y-1">
                    <button
                        onClick={() => setSettingsOpen(true)}
                        className={`w-full flex items-center gap-3 px-3 py-3 rounded-lg text-gray-400 hover:bg-neutral-800 hover:text-white transition-all ${!sidebarOpen ? 'justify-center' : ''}`}
                        title="Settings"
                    >
                        <Settings className="w-5 h-5" />
                        <span className={`transition-opacity duration-200 ${sidebarOpen ? 'opacity-100' : 'opacity-0 w-0 overflow-hidden'}`}>Settings</span>
                    </button>
                    <button
                        onClick={toggleSidebar}
                        className={`w-full flex items-center gap-3 px-3 py-3 rounded-lg text-gray-400 hover:bg-neutral-800 hover:text-white transition-all ${!sidebarOpen ? 'justify-center' : ''}`}
                    >
                        {sidebarOpen ? <ChevronLeft className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
                    </button>
                </div>
            </aside>

            {/* Main Content */}
            <main className={`transition-all duration-300 ease-in-out ${sidebarOpen ? 'ml-64' : 'ml-16'} ${pathname.startsWith('/paper/') ? '' : 'px-4 py-8'}`}>
                {children}

                {/* Ideas/Visualization Modal */}
                {viewMode !== 'none' && activePaper && (
                    <div className="fixed inset-0 bg-black/90 backdrop-blur-md z-50 flex items-center justify-center p-4">
                        <div className="bg-neutral-900 border border-white/10 rounded-2xl shadow-2xl w-full max-w-5xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in duration-200">
                            <div className="p-6 border-b border-white/10 flex justify-between items-center bg-black/40">
                                <div className="flex-1 pr-4">
                                    <h3 className="text-xl font-bold text-white truncate">{activePaper.title}</h3>
                                    <p className="text-sm text-gray-500 mt-1">
                                        {viewMode === 'ideas' ? 'Research Hypotheses & New Directions' : 'Interactive Knowledge Graph'}
                                    </p>
                                </div>
                                <button onClick={closeModal} className="text-gray-400 hover:text-white transition">✕</button>
                            </div>

                            <div className="p-0 overflow-hidden flex-1 relative min-h-[500px]">
                                {generating ? (
                                    <div className="h-full w-full flex flex-col items-center justify-center bg-zinc-900 z-10 min-h-[500px]">
                                        <div className="w-16 h-16 border-4 border-white border-t-transparent rounded-full animate-spin mb-6"></div>
                                        <p className="text-white font-medium text-lg animate-pulse">
                                            {viewMode === 'vis' ? 'Building mindmap...' : 'Forging research ideas...'}
                                        </p>
                                    </div>
                                ) : (
                                    <div className="h-full overflow-y-auto p-8 custom-scrollbar">
                                        {viewMode === 'ideas' && (
                                            <div className="space-y-6">
                                                <h4 className="text-lg font-semibold text-white flex items-center mb-6">Hypotheses & Future Directions</h4>
                                                <div className="grid gap-6">
                                                    {ideas.map((idea, idx) => (
                                                        <div key={idx} className="bg-black p-6 rounded-xl border border-white/10 relative">
                                                            <div className="absolute top-0 left-0 w-1 h-full bg-white rounded-l-xl"></div>
                                                            <p className="text-gray-300 leading-relaxed pl-2">{idea}</p>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {viewMode === 'vis' && (
                                            <div className="h-full flex flex-col min-h-[500px]">
                                                {mindMapData ? (
                                                    <InteractiveMindMap data={mindMapData} />
                                                ) : (
                                                    <div className="flex flex-col items-center justify-center h-full text-red-400">
                                                        <p>Failed to load visualization.</p>
                                                        <p className="text-xs text-gray-500 mt-2">Try re-generating or check backend logs.</p>
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                )}
            </main>

            {/* Settings Modal */}
            <SettingsModal isOpen={settingsOpen} onClose={() => setSettingsOpen(false)} />

            {/* Quick Read Panel */}
            {quickReadPaper && (
                <QuickReadPanel
                    paper={quickReadPaper}
                    isOpen={isQuickReadOpen}
                    onClose={closeQuickRead}
                    onDeepRead={handleDeepRead}
                    studyInsights={studyInsights}
                    isLoadingInsights={isLoadingInsights}
                />
            )}
        </div>
    );
}
