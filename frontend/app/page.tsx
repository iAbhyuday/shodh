"use client";
import React, { useEffect, useState, useCallback } from 'react';
import { ChevronLeft, ChevronRight, Compass, Heart, FolderArchive, Settings, RefreshCw } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useShallow } from 'zustand/shallow';

// Components
import InteractiveMindMap from './components/InteractiveMindMap';
import DiscoverView from './components/DiscoverView';
import LibraryView from './components/LibraryView';
import ProjectView from './components/ProjectView';
import AssistantView from './components/AssistantView';
import SettingsModal from './components/SettingsModal';
import NotificationBell from './components/NotificationBell';
import QuickReadPanel from './components/QuickReadPanel';
import { ShodhLogo } from './components/ShodhLogo';

// Stores
import { usePapersStore, useProjectsStore, useChatStore, useUIStore } from './stores';

// Hooks
import { useQuickRead, useIdeas } from './hooks';

// Types (for local state that didn't fit neatly into stores)
import type { Paper, IngestionStatus } from './lib/types';

export default function Home() {
  const router = useRouter();

  // --- Zustand Store Selectors ---

  // Papers Store
  const {
    feed, loading, error,
    searchQuery, setSearchQuery,
    availableTags, selectedTags, setSelectedTags,
    sortBy, setSortBy,
    currentPage, setCurrentPage,
    totalPages, totalPapers,
    fetchFeed, fetchBookmarks, fetchFavorites,
    toggleFavorite, toggleSave,
  } = usePapersStore(useShallow((s) => ({
    feed: s.feed,
    loading: s.loading,
    error: s.error,
    searchQuery: s.searchQuery,
    setSearchQuery: s.setSearchQuery,
    availableTags: s.availableTags,
    selectedTags: s.selectedTags,
    setSelectedTags: s.setSelectedTags,
    sortBy: s.sortBy,
    setSortBy: s.setSortBy,
    currentPage: s.currentPage,
    setCurrentPage: s.setCurrentPage,
    totalPages: s.totalPages,
    totalPapers: s.totalPapers,
    fetchFeed: s.fetchFeed,
    fetchBookmarks: s.fetchBookmarks,
    fetchFavorites: s.fetchFavorites,
    toggleFavorite: s.toggleFavorite,
    toggleSave: s.toggleSave,
  })));

  // Projects Store
  const {
    projects, selectedProject, setSelectedProject,
    isCreating: isCreatingProject, setIsCreating: setIsCreatingProject,
    newProjectName, setNewProjectName,
    newProjectDimensions, setNewProjectDimensions,
    fetchProjects, createProject, deleteProject,
    addPaperToProject, removePaperFromProject,
    fetchProjectPapers,
  } = useProjectsStore(useShallow((s) => ({
    projects: s.projects,
    selectedProject: s.selectedProject,
    setSelectedProject: s.setSelectedProject,
    isCreating: s.isCreating,
    setIsCreating: s.setIsCreating,
    newProjectName: s.newProjectName,
    setNewProjectName: s.setNewProjectName,
    newProjectDimensions: s.newProjectDimensions,
    setNewProjectDimensions: s.setNewProjectDimensions,
    fetchProjects: s.fetchProjects,
    createProject: s.createProject,
    deleteProject: s.deleteProject,
    addPaperToProject: s.addPaperToProject,
    removePaperFromProject: s.removePaperFromProject,
    fetchProjectPapers: s.fetchProjectPapers,
  })));

  // Chat Store
  const {
    messages: chatMessages, conversations,
    activeConversationId, chatInput, setChatInput,
    loading: chatLoading, useAgentMode,
    fetchConversations, loadConversation, startNewChat,
    sendMessage, toggleAgentMode,
  } = useChatStore(useShallow((s) => ({
    messages: s.messages,
    conversations: s.conversations,
    activeConversationId: s.activeConversationId,
    chatInput: s.chatInput,
    setChatInput: s.setChatInput,
    loading: s.loading,
    useAgentMode: s.useAgentMode,
    fetchConversations: s.fetchConversations,
    loadConversation: s.loadConversation,
    startNewChat: s.startNewChat,
    sendMessage: s.sendMessage,
    toggleAgentMode: s.toggleAgentMode,
  })));

  // UI Store
  const {
    sidebarOpen, setSidebarOpen, toggleSidebar,
    activeView, setActiveView,
    projectView, setProjectView,
    settingsOpen, setSettingsOpen,
    activePaper, viewMode, generating, ideas, mindMapData,
    openIdeasModal, openVisModal, closeModal, setGenerating, setIdeas, setMindMapData,
    activeProjectMenu, setActiveProjectMenu,
  } = useUIStore(useShallow((s) => ({
    sidebarOpen: s.sidebarOpen,
    setSidebarOpen: s.setSidebarOpen,
    toggleSidebar: s.toggleSidebar,
    activeView: s.activeView,
    setActiveView: s.setActiveView,
    projectView: s.projectView,
    setProjectView: s.setProjectView,
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

  // --- Local State (not in stores) ---

  // Ingestion status - kept local with simple polling
  const [ingestionStatus, setIngestionStatus] = useState<Record<string, IngestionStatus>>({});

  // Selected paper for assistant view (rarely used now since paper chat moved to /paper/[id])
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null);

  // --- Effects ---

  // Initial load
  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  // Fetch data based on active view
  useEffect(() => {
    if (activeView === 'bookmarks') {
      if (selectedProject) {
        fetchProjectPapers(selectedProject.id);
      } else {
        fetchBookmarks();
      }
    } else if (activeView === 'favourites') {
      fetchFavorites();
    } else if (activeView === 'explore') {
      fetchFeed();
    }
  }, [activeView, selectedProject, currentPage, fetchFeed, fetchBookmarks, fetchFavorites, fetchProjectPapers]);

  // Re-fetch when sort or tags change
  useEffect(() => {
    setCurrentPage(1);
    fetchFeed();
  }, [sortBy, selectedTags, setCurrentPage, fetchFeed]);

  // Scroll tracking
  useEffect(() => {
    const handleScroll = () => {
      // Could be used for sticky header effects
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

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

  const handleSearch = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1);
    fetchFeed();
  }, [setCurrentPage, fetchFeed]);

  const handleTagClick = useCallback((tag: string) => {
    const isSelected = selectedTags.includes(tag);
    const newTags = isSelected
      ? selectedTags.filter(t => t !== tag)
      : [...selectedTags, tag];
    setSelectedTags(newTags);
  }, [selectedTags, setSelectedTags]);

  const goToPage = useCallback((page: number) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }, [totalPages, setCurrentPage]);

  const handleAddPaperToProject = useCallback(async (projectId: number, paperId: string, paperTitle?: string) => {
    const paper = feed.find(p => p.id === paperId);
    const isAlreadyInProject = paper?.project_ids?.includes(projectId);

    if (isAlreadyInProject) {
      await removePaperFromProject(projectId, paperId);
    } else {
      await addPaperToProject(projectId, paperId, paperTitle);
    }
  }, [feed, addPaperToProject, removePaperFromProject]);

  const sendChatMessage = useCallback(async () => {
    const isProjectSynthesis = activeView === 'bookmarks' && selectedProject && projectView === 'synthesis';
    if (isProjectSynthesis && selectedProject) {
      await sendMessage({
        message: chatInput,
        projectId: selectedProject.id,
      });
    } else if (selectedPaper) {
      await sendMessage({
        message: chatInput,
        paperId: selectedPaper.id,
      });
    }
  }, [activeView, selectedProject, projectView, selectedPaper, chatInput, sendMessage]);

  // --- Render ---

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
            onClick={() => { setActiveView('explore'); setSelectedProject(null); setCurrentPage(1); }}
            title="Research Discovery"
            className={`w-full flex items-center py-3 rounded-lg transition-all ${sidebarOpen ? 'gap-3 px-3' : 'justify-center px-2'} ${activeView === 'explore' ? 'bg-indigo-600 text-white font-semibold shadow-lg shadow-indigo-500/20' : 'text-gray-400 hover:bg-neutral-800 hover:text-white'}`}
          >
            <Compass className="w-5 h-5 flex-shrink-0" />
            <span className={`transition-opacity duration-200 ${sidebarOpen ? 'opacity-100' : 'opacity-0 w-0 overflow-hidden'}`}>Research Discovery</span>
          </button>

          <button
            onClick={() => { setActiveView('favourites'); setSelectedProject(null); setCurrentPage(1); }}
            title="Personal Collection"
            className={`w-full flex items-center py-3 rounded-lg transition-all ${sidebarOpen ? 'gap-3 px-3' : 'justify-center px-2'} ${activeView === 'favourites' ? 'bg-indigo-600 text-white font-semibold shadow-lg shadow-indigo-500/20' : 'text-gray-400 hover:bg-neutral-800 hover:text-white'}`}
          >
            <Heart className="w-5 h-5 flex-shrink-0" />
            <span className={`transition-opacity duration-200 ${sidebarOpen ? 'opacity-100' : 'opacity-0 w-0 overflow-hidden'}`}>Personal Collection</span>
          </button>

          <button
            onClick={() => { setActiveView('bookmarks'); setSelectedProject(null); setCurrentPage(1); }}
            title="Synthesis Hub"
            className={`w-full flex items-center py-3 rounded-lg transition-all ${sidebarOpen ? 'gap-3 px-3' : 'justify-center px-2'} ${activeView === 'bookmarks' && !selectedProject ? 'bg-indigo-600 text-white font-semibold shadow-lg shadow-indigo-500/20' : 'text-gray-400 hover:bg-neutral-800 hover:text-white'}`}
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
                    onClick={() => { setSelectedProject(proj); setSidebarOpen(false); setActiveView('bookmarks'); }}
                    className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-sm transition-colors ${selectedProject?.id === proj.id ? 'bg-indigo-600/20 text-indigo-400 font-medium' : 'text-gray-400 hover:bg-white/5 hover:text-gray-200'}`}
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
      <main className={`transition-all duration-300 ease-in-out ${sidebarOpen ? 'ml-64' : 'ml-16'} ${activeView === 'assistant' ? 'p-0' : 'px-4 py-8'}`}>
        {activeView === 'explore' || activeView === 'favourites' ? (
          <DiscoverView
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
            showSearch={activeView === 'explore'}
            onSearch={handleSearch}
            loading={loading}
            error={error}
            feed={feed.filter((p) => (activeView === 'favourites' ? p.is_favorited : true))}
            onQuickRead={handleQuickRead}
            onDeepRead={handleDeepRead}
            onVisualize={visualize}
            onAddPaperToProject={(projId, paperId) => {
              const p = feed.find(paper => paper.id === paperId);
              handleAddPaperToProject(projId, paperId, p?.title);
            }}
            onToggleFavorite={toggleFavorite}
            projects={projects}
            activeProjectMenu={activeProjectMenu}
            setActiveProjectMenu={setActiveProjectMenu}
            ingestionStatus={ingestionStatus}
            totalPages={totalPages}
            currentPage={currentPage}
            goToPage={goToPage}
            totalPapers={totalPapers}
            onRetry={fetchFeed}
            title={activeView === 'favourites' ? "Personal Collection" : "Research Discovery"}
            subtitle={activeView === 'favourites' ? "A curated space for your most valued research papers." : "Explore the global frontier of research publications."}
            availableTags={availableTags}
            selectedTags={selectedTags}
            setSelectedTags={setSelectedTags}
            sortBy={sortBy}
            setSortBy={setSortBy}
            onTagClick={handleTagClick}
          />
        ) : (
          <>
            {activeView === 'assistant' ? (
              <AssistantView
                selectedPaper={selectedPaper}
                conversations={conversations}
                activeConversationId={activeConversationId}
                chatMessages={chatMessages}
                chatInput={chatInput}
                chatLoading={chatLoading}
                useAgentMode={useAgentMode}
                onStartNewChat={startNewChat}
                onLoadConversation={loadConversation}
                onBackToLibrary={() => {
                  setActiveView('bookmarks');
                  setSelectedPaper(null);
                }}
                onSetChatInput={setChatInput}
                onSendChatMessage={sendChatMessage}
                onToggleAgentMode={toggleAgentMode}
              />
            ) : activeView === 'bookmarks' && !selectedProject ? (
              <LibraryView
                projects={projects}
                isCreatingProject={isCreatingProject}
                setIsCreatingProject={setIsCreatingProject}
                newProjectName={newProjectName}
                setNewProjectName={setNewProjectName}
                newProjectDimensions={newProjectDimensions}
                setNewProjectDimensions={setNewProjectDimensions}
                onCreateProject={createProject}
                onSelectProject={(p) => {
                  setSelectedProject(p);
                  if (p) setSidebarOpen(false);
                }}
                onDeleteProject={deleteProject}
                onFetchBookmarks={fetchBookmarks}
                onQuickRead={handleQuickRead}
                onDeepRead={handleDeepRead}
                onVisualize={visualize}
              />
            ) : (
              <ProjectView
                project={selectedProject!}
                onClose={() => setSelectedProject(null)}
                projectView={projectView}
                setProjectView={setProjectView}
                feed={feed}
                onQuickRead={handleQuickRead}
                onDeepRead={handleDeepRead}
                onVisualize={visualize}
                onFetchConversations={fetchConversations}
                conversations={conversations}
                activeConversationId={activeConversationId}
                onLoadConversation={loadConversation}
                chatMessages={chatMessages}
                chatInput={chatInput}
                setChatInput={setChatInput}
                onSendChatMessage={sendChatMessage}
                chatLoading={chatLoading}
                onStartNewChat={startNewChat}
                activeProjectMenu={activeProjectMenu}
                setActiveProjectMenu={setActiveProjectMenu}
                ingestionStatus={ingestionStatus}
                onAddPaperToProject={handleAddPaperToProject}
                useAgentMode={useAgentMode}
                onToggleAgentMode={toggleAgentMode}
              />
            )}
          </>
        )}

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
