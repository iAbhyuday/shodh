"use client";
import React, { useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useShallow } from 'zustand/shallow';

// Components
import DiscoverView from '../components/DiscoverView';

// Stores
import { usePapersStore, useProjectsStore, useUIStore } from '../stores';

// Hooks
import { useQuickRead, useIdeas } from '../hooks';

// Types
import type { Paper } from '../lib/types';

export default function FavoritesPage() {
    const router = useRouter();

    // --- Papers Store ---
    const {
        feed, loading, error,
        fetchFavorites,
        toggleFavorite,
    } = usePapersStore(useShallow((s) => ({
        feed: s.feed,
        loading: s.loading,
        error: s.error,
        fetchFavorites: s.fetchFavorites,
        toggleFavorite: s.toggleFavorite,
    })));

    // --- Projects Store ---
    const {
        projects, addPaperToProject, removePaperFromProject,
    } = useProjectsStore(useShallow((s) => ({
        projects: s.projects,
        addPaperToProject: s.addPaperToProject,
        removePaperFromProject: s.removePaperFromProject,
    })));

    // --- UI Store ---
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
    useEffect(() => {
        fetchFavorites();
    }, [fetchFavorites]);

    // --- Handlers ---
    const handleDeepRead = useCallback((paper: Paper) => {
        router.push(`/paper/${paper.id}`);
    }, [router]);

    const handleAddPaperToProject = useCallback(async (projectId: number, paperId: string, paperTitle?: string, paper?: Paper) => {
        const targetPaper = paper || feed.find(p => p.id === paperId);
        if (!targetPaper) return;

        const isAlreadyInProject = targetPaper.project_ids?.includes(projectId);

        if (isAlreadyInProject) {
            await removePaperFromProject(projectId, paperId);
        } else {
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
        // Refresh favorites to update UI state if needed (though store optimistic updates handle it usually)
        fetchFavorites();
    }, [feed, addPaperToProject, removePaperFromProject, fetchFavorites]);

    return (
        <DiscoverView
            searchQuery=""
            setSearchQuery={() => { }}
            showSearch={false}
            onSearch={(e) => e.preventDefault()}
            loading={loading}
            error={error}
            feed={feed} // In favorites view, feed is already filtered by DB query usually, or we can filter again if store is mixed
            // The store has `fetchFavorites` which sets `feed` to favorites. 
            // So `feed` here IS the favorites.
            onQuickRead={handleQuickRead}
            onDeepRead={handleDeepRead}
            onVisualize={visualize}
            onAddPaperToProject={handleAddPaperToProject}
            onToggleFavorite={async (id) => {
                await toggleFavorite(id);
                fetchFavorites(); // Refresh list after untoggling
            }}
            projects={projects}
            activeProjectMenu={activeProjectMenu}
            setActiveProjectMenu={setActiveProjectMenu}
            ingestionStatus={{}}
            totalPages={1}
            currentPage={1}
            goToPage={() => { }}
            totalPapers={feed.length}
            onRetry={fetchFavorites}
            title="Personal Collection"
            subtitle="A curated space for your most valued research papers."
            availableTags={[]}
            selectedTags={[]}
            setSelectedTags={() => { }}
            sortBy="newest"
            setSortBy={() => { }}
            onTagClick={() => { }}
        />
    );
}
