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
        <div className="min-h-screen bg-black text-gray-100 font-sans flex">
            {/* Sidebar - Mercor Style: Fixed width, icon-over-label */}
            <aside className="fixed left-0 top-0 h-screen w-20 bg-neutral-950 border-r border-white/5 flex flex-col z-[90]">
                {/* Sidebar Header: Logo */}
                <div className="h-16 flex items-center justify-center border-b border-white/5">
                    <ShodhLogo className="w-9 h-9" />
                </div>

                {/* Navigation - Vertical icon + label layout */}
                <nav className="flex-1 flex flex-col items-center py-4 gap-1">
                    <button
                        onClick={() => {
                            setSelectedProject(null);
                            router.push('/');
                        }}
                        title="Explore"
                        className={`group flex flex-col items-center gap-1 py-3 px-2 w-full transition-all relative ${pathname === '/'
                            ? 'text-indigo-400'
                            : 'text-gray-500 hover:text-gray-300'
                            }`}
                    >
                        {pathname === '/' && (
                            <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-indigo-500 rounded-r-full" />
                        )}
                        <Compass className={`w-6 h-6 transition-transform group-hover:scale-110 ${pathname === '/' ? 'text-indigo-400' : ''}`} />
                        <span className={`text-[10px] font-medium ${pathname === '/' ? 'text-indigo-400' : ''}`}>Explore</span>
                    </button>

                    <button
                        onClick={() => {
                            setSelectedProject(null);
                            router.push('/favorites');
                        }}
                        title="Favorites"
                        className={`group flex flex-col items-center gap-1 py-3 px-2 w-full transition-all relative ${pathname === '/favorites'
                            ? 'text-indigo-400'
                            : 'text-gray-500 hover:text-gray-300'
                            }`}
                    >
                        {pathname === '/favorites' && (
                            <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-indigo-500 rounded-r-full" />
                        )}
                        <Heart className={`w-6 h-6 transition-transform group-hover:scale-110 ${pathname === '/favorites' ? 'text-indigo-400' : ''}`} />
                        <span className={`text-[10px] font-medium ${pathname === '/favorites' ? 'text-indigo-400' : ''}`}>Favorites</span>
                    </button>

                    <button
                        onClick={() => router.push('/projects')}
                        title="Projects"
                        className={`group flex flex-col items-center gap-1 py-3 px-2 w-full transition-all relative ${pathname.startsWith('/projects')
                            ? 'text-indigo-400'
                            : 'text-gray-500 hover:text-gray-300'
                            }`}
                    >
                        {pathname.startsWith('/projects') && (
                            <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-indigo-500 rounded-r-full" />
                        )}
                        <FolderArchive className={`w-6 h-6 transition-transform group-hover:scale-110 ${pathname.startsWith('/projects') ? 'text-indigo-400' : ''}`} />
                        <span className={`text-[10px] font-medium ${pathname.startsWith('/projects') ? 'text-indigo-400' : ''}`}>Projects</span>
                    </button>
                </nav>

                {/* Sidebar Footer: Utilities */}
                <div className="flex flex-col items-center gap-2 py-4 border-t border-white/5">
                    {/* Notification Bell */}
                    <NotificationBell ingestionStatus={ingestionStatus} />

                    {/* Refresh - Only on Explore page */}
                    {pathname === '/' && (
                        <button
                            onClick={() => fetchFeed()}
                            className="group flex flex-col items-center gap-1 py-2 px-2 text-gray-500 hover:text-gray-300 transition-all"
                            title="Refresh Feed"
                        >
                            <RefreshCw className={`w-5 h-5 transition-transform group-hover:scale-110 ${loading ? 'animate-spin text-indigo-400' : ''}`} />
                        </button>
                    )}

                    {/* Settings */}
                    <button
                        onClick={() => setSettingsOpen(true)}
                        className="group flex flex-col items-center gap-1 py-2 px-2 text-gray-500 hover:text-gray-300 transition-all"
                        title="Settings"
                    >
                        <Settings className="w-5 h-5 transition-transform group-hover:rotate-90" />
                    </button>
                </div>
            </aside>

            {/* Main Content */}
            <main className={`flex-1 transition-all duration-300 ease-in-out ml-20 ${pathname.startsWith('/paper/') ? '' : 'px-4 py-8'}`}>
                {children}

                {/* Ideas/Visualization Modal */}
                {viewMode !== 'none' && activePaper && (
                    <div className="fixed inset-0 bg-black/90 backdrop-blur-md z-[110] flex items-center justify-center p-4">
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
