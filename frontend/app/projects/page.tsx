"use client";
import React, { useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useShallow } from 'zustand/shallow';

// Components
import LibraryView from '../components/LibraryView';
import ProjectView from '../components/ProjectView';
import AssistantView from '../components/AssistantView'; // Kept if we want Assistant mode inside projects?
// Actually original page.tsx had AssistantView as a separate top-level view.
// In the new route structure, Assistant might be a global overlay or specific route.
// For now, let's assume Projects page focuses on Library -> Project -> Paper/Synthesis.

// Stores
import { usePapersStore, useProjectsStore, useChatStore, useUIStore } from '../stores';

// Hooks
import { useQuickRead, useIdeas } from '../hooks';

// Types
import type { Paper } from '../lib/types';

export default function ProjectsPage() {
    const router = useRouter();

    // --- Papers Store ---
    const { feed } = usePapersStore(useShallow((s) => ({ feed: s.feed }))); // We might need global feed for lookup, or not.

    // --- Projects Store ---
    const {
        projects, selectedProject, setSelectedProject,
        isCreating: isCreatingProject, setIsCreating: setIsCreatingProject,
        newProjectName, setNewProjectName,
        newProjectDimensions, setNewProjectDimensions,
        fetchProjects, createProject, deleteProject,
        addPaperToProject, removePaperFromProject,
        fetchProjectPapers, editingProject, setEditingProject, updateProject,
        projectPapers, // <--- IMPORTANT: This is the source of truth for Project Papers now
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
        editingProject: s.editingProject,
        setEditingProject: s.setEditingProject,
        updateProject: s.updateProject,
        projectPapers: s.projectPapers,
    })));

    // --- Chat Store ---
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

    // --- UI Store ---
    const {
        projectView, setProjectView,
        activeProjectMenu, setActiveProjectMenu,
        openIdeasModal, openVisModal, setIdeas, setMindMapData, setGenerating,
    } = useUIStore(useShallow((s) => ({
        projectView: s.projectView,
        setProjectView: s.setProjectView,
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
        document.title = 'Shodh | Projects';
    }, []);

    useEffect(() => {
        fetchProjects();
    }, [fetchProjects]);

    useEffect(() => {
        if (selectedProject) {
            fetchProjectPapers(selectedProject.id);
        }
    }, [selectedProject, fetchProjectPapers]);

    // --- Handlers ---
    const handleDeepRead = useCallback((paper: Paper) => {
        router.push(`/paper/${paper.id}`);
    }, [router]);

    const handleAddPaperToProject = useCallback(async (projectId: string, paperId: string, paperTitle?: string, paper?: Paper) => {
        // We need to find the paper object. If we are in Project View, the paper is in `projectPapers`.
        const targetPaper = paper || projectPapers.find(p => p.id === paperId);
        if (!targetPaper) return;
        // Determine existence
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
        // Refresh project papers
        if (selectedProject) {
            fetchProjectPapers(selectedProject.id);
        }
    }, [projectPapers, addPaperToProject, removePaperFromProject, selectedProject, fetchProjectPapers]);

    const sendChatMessage = useCallback(async () => {
        if (selectedProject && projectView === 'synthesis') {
            await sendMessage({
                message: chatInput,
                projectId: selectedProject.id,
            });
        }
    }, [selectedProject, projectView, chatInput, sendMessage]);


    // --- Render ---
    if (!selectedProject) {
        return (
            <LibraryView
                projects={projects}
                isCreatingProject={isCreatingProject}
                setIsCreatingProject={setIsCreatingProject}
                newProjectName={newProjectName}
                setNewProjectName={setNewProjectName}
                newProjectDimensions={newProjectDimensions}
                setNewProjectDimensions={setNewProjectDimensions}
                onCreateProject={createProject}
                onSelectProject={(p) => setSelectedProject(p)}
                onDeleteProject={deleteProject}
                onFetchBookmarks={() => router.push('/favorites')} // Redirect to Favorites page for bookmarks
                onQuickRead={handleQuickRead}
                onDeepRead={handleDeepRead}
                onVisualize={visualize}
                activeEditingProject={editingProject}
                onEditProject={setEditingProject}
                onUpdateProject={updateProject}
            />
        );
    }

    return (
        <ProjectView
            project={selectedProject}
            onClose={() => setSelectedProject(null)}
            projectView={projectView}
            setProjectView={setProjectView}
            feed={projectPapers} // <--- FIX: Passing projectPapers instead of generic feed
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
            ingestionStatus={{}}
            onAddPaperToProject={handleAddPaperToProject}
            useAgentMode={useAgentMode}
            onToggleAgentMode={toggleAgentMode}
        />
    );
}
