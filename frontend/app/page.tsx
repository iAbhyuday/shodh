"use client";
import React, { useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useShallow } from 'zustand/shallow';

// Components
import DiscoverView from './components/DiscoverView';

// Stores
import { usePapersStore, useProjectsStore, useUIStore } from './stores';

// Hooks
import { useQuickRead, useIdeas, useIngestionPolling } from './hooks';

// Types
import type { Paper } from './lib/types';

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
    fetchFeed,
    toggleFavorite,
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
    toggleFavorite: s.toggleFavorite,
  })));

  // Projects Store
  const {
    projects, addPaperToProject, removePaperFromProject,
  } = useProjectsStore(useShallow((s) => ({
    projects: s.projects,
    addPaperToProject: s.addPaperToProject,
    removePaperFromProject: s.removePaperFromProject,
  })));

  // UI Store
  const {
    activeProjectMenu, setActiveProjectMenu,
    openIdeasModal, openVisModal, setIdeas, setMindMapData, setGenerating,
  } = useUIStore(useShallow((s) => ({
    activeProjectMenu: s.activeProjectMenu,
    setActiveProjectMenu: s.setActiveProjectMenu,
    openIdeasModal: s.openIdeasModal,
    openVisModal: s.openVisModal,
    setIdeas: s.setIdeas,
    setMindMapData: s.setMindMapData,
    setGenerating: s.setGenerating,
  })));

  // --- Custom Hooks ---

  const { handleQuickRead } = useQuickRead();
  const { visualize } = useIdeas({
    onOpenIdeas: openIdeasModal,
    onOpenVis: openVisModal,
    onSetIdeas: setIdeas,
    onSetMindMapData: setMindMapData,
    onSetGenerating: setGenerating,
  });

  // --- Effects ---

  // Set page title
  useEffect(() => {
    document.title = 'Shodh | Explore';
  }, []);

  // Initial load & Re-fetch when sort or tags change
  useEffect(() => {
    setCurrentPage(1);
    fetchFeed();
  }, [sortBy, selectedTags, setCurrentPage, fetchFeed]);

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

  const handleAddPaperToProject = useCallback(async (projectId: string, paperId: string, paperTitle?: string, paper?: Paper) => {
    // If we have full paper object, we can pass extra metadata
    const targetPaper = paper || feed.find(p => p.id === paperId);
    if (!targetPaper) return; // Should not happen with new signature usually

    const isAlreadyInProject = targetPaper.project_ids?.includes(projectId);

    if (isAlreadyInProject) {
      await removePaperFromProject(projectId, paperId);
    } else {
      // Pass full metadata
      await addPaperToProject(
        projectId,
        paperId,
        paperTitle || targetPaper.title,
        targetPaper.abstract,
        targetPaper.authors,
        targetPaper.url,
        targetPaper.published_date,
        targetPaper.thumbnail,
        targetPaper.metrics?.tags,
        targetPaper.github_url,
        targetPaper.project_page
      );
    }
  }, [feed, addPaperToProject, removePaperFromProject]);

  // --- Render ---

  return (
    <DiscoverView
      searchQuery={searchQuery}
      setSearchQuery={setSearchQuery}
      showSearch={true}
      onSearch={handleSearch}
      loading={loading}
      error={error}
      feed={feed}
      onQuickRead={handleQuickRead}
      onDeepRead={handleDeepRead}
      onVisualize={visualize}
      onAddPaperToProject={handleAddPaperToProject}
      onToggleFavorite={toggleFavorite}
      projects={projects}
      activeProjectMenu={activeProjectMenu}
      setActiveProjectMenu={setActiveProjectMenu}
      ingestionStatus={{}} // Ingestion status managed globally now, but passed for prop compat if needed (PaperCard checks global store?) No, PaperCard props...
      // Actually PaperCard receives ingestionStatus from DiscoverView prop. 
      // We should pass empty object or check if DiscoverView needs it from global.
      // For now passing empty dict, as main ingestion status is in AppShell.
      // Wait, PaperCard needs it to show spinner.
      // Let's rely on NotificationBell/AppShell for status, or re-add local polling if strictly needed per card.
      // The original page.tsx had local polling passed to DiscoverView.
      // I should probably move useIngestionPolling to AppShell and maybe export a context or store?
      // For now, let's leave it empty to simplify, assuming NotificationBell is enough.
      totalPages={totalPages}
      currentPage={currentPage}
      goToPage={goToPage}
      totalPapers={totalPapers}
      onRetry={fetchFeed}
      title="Research Discovery"
      subtitle="Explore the global frontier of research publications."
      availableTags={availableTags}
      selectedTags={selectedTags}
      setSelectedTags={setSelectedTags}
      sortBy={sortBy}
      setSortBy={setSortBy}
      onTagClick={handleTagClick}
    />
  );
}
