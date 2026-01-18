"use client";

import React, { useEffect, useState } from 'react';
import { X, FolderPlus, Loader2, Check, AlertCircle } from 'lucide-react';
import { useProjectsStore } from '../stores';
import { useShallow } from 'zustand/react/shallow';

interface ProjectPickerModalProps {
    isOpen: boolean;
    onClose: () => void;
    paperId: string;
    paperTitle?: string;
    paperSummary?: string;
    paperAuthors?: string;
    paperUrl?: string;
    paperPublishedDate?: string;
    paperThumbnail?: string;
    onIngestionStarted?: () => void;
    onIngestionComplete?: () => void;
}

type IngestionState = 'idle' | 'adding' | 'ingesting' | 'completed' | 'error';

/**
 * Modal for adding a paper to a project.
 * Shows project list, handles paper addition, and displays ingestion progress.
 */
export const ProjectPickerModal: React.FC<ProjectPickerModalProps> = ({
    isOpen,
    onClose,
    paperId,
    paperTitle,
    paperSummary,
    paperAuthors,
    paperUrl,
    paperPublishedDate,
    paperThumbnail,
    onIngestionStarted,
    onIngestionComplete
}) => {
    const { projects, fetchProjects, addPaperToProject } = useProjectsStore(useShallow((s) => ({
        projects: s.projects,
        fetchProjects: s.fetchProjects,
        addPaperToProject: s.addPaperToProject
    })));

    const [ingestionState, setIngestionState] = useState<IngestionState>('idle');
    const [ingestionProgress, setIngestionProgress] = useState('');
    const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    // Fetch projects when modal opens
    useEffect(() => {
        if (isOpen) {
            fetchProjects();
            setIngestionState('idle');
            setError(null);
        }
    }, [isOpen, fetchProjects]);

    // Handle project selection and add paper
    const handleSelectProject = async (projectId: string) => {
        if (ingestionState === 'adding' || ingestionState === 'ingesting') return;

        setSelectedProjectId(projectId);
        setIngestionState('adding');
        setError(null);

        try {
            await addPaperToProject(
                projectId,
                paperId,
                paperTitle,
                paperSummary,
                paperAuthors,
                paperUrl,
                paperPublishedDate,
                paperThumbnail
            );

            setIngestionState('ingesting');
            setIngestionProgress('Ingestion started...');
            onIngestionStarted?.();

            // The SSE hook in AppShell will handle the actual progress updates
            // For now, we'll show a simple progress message and auto-close after a delay
            setTimeout(() => {
                setIngestionState('completed');
                setIngestionProgress('Paper added successfully!');

                setTimeout(() => {
                    onIngestionComplete?.();
                    onClose();
                }, 1500);
            }, 2000);

        } catch (err) {
            console.error('Failed to add paper to project:', err);
            setIngestionState('error');
            setError('Failed to add paper. Please try again.');
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-[#1A1A1A] border border-white/10 rounded-xl w-full max-w-md shadow-2xl">
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-white/10">
                    <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                        <FolderPlus className="w-5 h-5 text-indigo-400" />
                        Add to Project
                    </h2>
                    <button
                        onClick={onClose}
                        disabled={ingestionState === 'adding' || ingestionState === 'ingesting'}
                        className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded-md transition disabled:opacity-50"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-4">
                    {/* Paper Title Preview */}
                    {paperTitle && (
                        <div className="mb-4 p-3 bg-white/5 rounded-lg">
                            <p className="text-sm text-gray-400 mb-1">Adding paper:</p>
                            <p className="text-white text-sm font-medium line-clamp-2">{paperTitle}</p>
                        </div>
                    )}

                    {/* Progress State */}
                    {ingestionState !== 'idle' && (
                        <div className={`mb-4 p-3 rounded-lg flex items-center gap-3 ${ingestionState === 'completed' ? 'bg-emerald-900/30 border border-emerald-500/30' :
                                ingestionState === 'error' ? 'bg-red-900/30 border border-red-500/30' :
                                    'bg-indigo-900/30 border border-indigo-500/30'
                            }`}>
                            {ingestionState === 'adding' && <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />}
                            {ingestionState === 'ingesting' && <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />}
                            {ingestionState === 'completed' && <Check className="w-5 h-5 text-emerald-400" />}
                            {ingestionState === 'error' && <AlertCircle className="w-5 h-5 text-red-400" />}
                            <span className={`text-sm ${ingestionState === 'completed' ? 'text-emerald-400' :
                                    ingestionState === 'error' ? 'text-red-400' :
                                        'text-indigo-400'
                                }`}>
                                {ingestionState === 'adding' && 'Adding to project...'}
                                {ingestionState === 'ingesting' && ingestionProgress}
                                {ingestionState === 'completed' && ingestionProgress}
                                {ingestionState === 'error' && error}
                            </span>
                        </div>
                    )}

                    {/* Projects List */}
                    {ingestionState === 'idle' && (
                        <>
                            {projects.length === 0 ? (
                                <div className="text-center py-8 text-gray-500">
                                    <FolderPlus className="w-10 h-10 mx-auto mb-3 opacity-40" />
                                    <p className="text-sm">No projects yet</p>
                                    <p className="text-xs mt-1">Create a project in the Library first</p>
                                </div>
                            ) : (
                                <div className="space-y-2 max-h-64 overflow-y-auto">
                                    {projects.map((project) => (
                                        <button
                                            key={project.id}
                                            onClick={() => handleSelectProject(project.id)}
                                            className="w-full flex items-center gap-3 p-3 rounded-lg bg-white/5 hover:bg-white/10 border border-transparent hover:border-indigo-500/50 transition-all text-left group"
                                        >
                                            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-indigo-600 to-purple-600 flex items-center justify-center text-white font-bold">
                                                {project.name.charAt(0).toUpperCase()}
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <p className="text-white font-medium truncate">{project.name}</p>
                                                <p className="text-xs text-gray-500">
                                                    {project.paper_count || 0} papers
                                                </p>
                                            </div>
                                        </button>
                                    ))}
                                </div>
                            )}
                        </>
                    )}
                </div>

                {/* Footer */}
                <div className="p-4 border-t border-white/10">
                    <button
                        onClick={onClose}
                        disabled={ingestionState === 'adding' || ingestionState === 'ingesting'}
                        className="w-full py-2 text-gray-400 hover:text-white text-sm transition disabled:opacity-50"
                    >
                        {ingestionState === 'completed' ? 'Done' : 'Cancel'}
                    </button>
                </div>
            </div>
        </div>
    );
};
