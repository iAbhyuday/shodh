import React from 'react';
import { ChevronRight, ExternalLink, Code, Lightbulb, MessageSquare, Plus, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

import { Paper, Project } from '../lib/types';

interface ReaderPanelProps {
    paper: Paper | null;
    onClose: () => void;
    insights: string;
    isLoading: boolean;
    ingestionStatus: Record<string, { status: string; chunk_count: number | null }>;
    onOpenAssistant: (paper: Paper) => void;
    isProjectView?: boolean;
    projects?: Project[];
    activeProjectMenu: string | null;
    setActiveProjectMenu: (id: string | null) => void;
    onAddPaperToProject?: (projectId: string, paperId: string, paperTitle?: string) => void;
    onCreateProject?: () => void;
}

const ReaderPanel: React.FC<ReaderPanelProps> = ({
    paper,
    onClose,
    insights,
    isLoading,
    ingestionStatus,
    onOpenAssistant,
    isProjectView = false,
    projects = [],
    activeProjectMenu,
    setActiveProjectMenu,
    onAddPaperToProject,
    onCreateProject
}) => {
    if (!paper) return null;

    return (
        <>
            {/* Overlay to dim background */}
            <div
                className="fixed inset-0 bg-black/40 backdrop-blur-[2px] z-30 transition-opacity"
                onClick={onClose}
            />

            <aside className="fixed right-0 top-16 h-[calc(100vh-4rem)] w-[500px] bg-[#0c0c0d] border-l border-white/5 shadow-2xl z-40 flex flex-col animate-in slide-in-from-right duration-300">
                {/* Drawer Header */}
                <div className="p-6 border-b border-white/5 bg-[#0f0f11]/50">
                    <div className="flex justify-between items-start mb-4">
                        <div className="bg-indigo-600/10 text-indigo-400 px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider border border-indigo-500/20">
                            Quick Read
                        </div>
                        <div className="flex items-center gap-2">
                            {!isProjectView && (
                                <div className="relative">
                                    <button
                                        onClick={() => setActiveProjectMenu(activeProjectMenu === paper.id ? null : paper.id)}
                                        className={`p-1.5 rounded-lg transition-all ${activeProjectMenu === paper.id ? 'bg-indigo-600 text-white' : 'hover:bg-neutral-800 text-gray-500 hover:text-white'
                                            }`}
                                        title="Add to Project"
                                    >
                                        <Plus className="w-5 h-5" />
                                    </button>
                                    {activeProjectMenu === paper.id && (
                                        <div className="absolute right-0 top-full mt-2 w-48 glass-indigo border border-indigo-500/30 rounded-xl shadow-2xl z-50 p-2 animate-in fade-in zoom-in-95 duration-200">
                                            <p className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest p-2 border-b border-white/5 mb-1 text-left">Add to Project</p>
                                            <div className="max-h-40 overflow-y-auto customized-scrollbar">
                                                {projects.map((p) => (
                                                    <button
                                                        key={p.id}
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            onAddPaperToProject?.(p.id, paper.id, paper.title);
                                                            setActiveProjectMenu(null);
                                                        }}
                                                        className={`w-full text-left px-3 py-2 text-xs rounded-lg transition-all flex items-center justify-between group/item ${paper.project_ids?.includes(p.id)
                                                            ? 'bg-indigo-500/20 text-indigo-300 hover:bg-red-500/20 hover:text-red-300'
                                                            : 'text-gray-300 hover:bg-white/5 hover:text-white'
                                                            }`}
                                                    >
                                                        {p.name}
                                                        {paper.project_ids?.includes(p.id) ? (
                                                            <span className="text-[10px] uppercase font-bold tracking-wider group-hover/item:hidden">Added</span>
                                                        ) : (
                                                            <ChevronRight className="w-3 h-3 opacity-0 group-hover/item:opacity-100 transition-opacity" />
                                                        )}
                                                        {paper.project_ids?.includes(p.id) && (
                                                            <span className="text-[10px] uppercase font-bold tracking-wider hidden group-hover/item:block">Remove</span>
                                                        )}
                                                    </button>
                                                ))}
                                                {projects.length === 0 && <p className="text-[10px] text-gray-500 p-2 italic text-center">No projects yet.</p>}
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        onCreateProject?.();
                                                        setActiveProjectMenu(null);
                                                    }}
                                                    className="w-full text-left px-3 py-2 text-[10px] text-indigo-400 hover:bg-indigo-400/10 rounded-lg mt-1 border-t border-white/5 pt-2 font-bold uppercase tracking-wider"
                                                >
                                                    + Create New
                                                </button>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}
                            <button
                                onClick={onClose}
                                className="p-1 hover:bg-neutral-800 rounded-lg transition text-gray-500 hover:text-white"
                            >
                                <ChevronRight className="w-5 h-5" />
                            </button>
                        </div>
                    </div>
                    <h2 className="text-xl font-bold text-white leading-tight mb-2">{paper.title}</h2>
                    <p className="text-sm text-gray-400 mb-4">{paper.authors}</p>

                    <div className="flex gap-3">
                        <a
                            href={paper.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-neutral-800 hover:bg-neutral-700 text-white text-sm font-medium rounded-xl transition border border-white/5"
                        >
                            <ExternalLink className="w-4 h-4" />
                            View PDF
                        </a>
                        {paper.github_url && (
                            <a
                                href={paper.github_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-xl transition shadow-lg shadow-indigo-500/20"
                            >
                                <Code className="w-4 h-4" />
                                Github
                            </a>
                        )}
                    </div>
                </div>

                {/* Drawer Content */}
                <div className="flex-1 overflow-y-auto customized-scrollbar p-6 space-y-8">
                    {/* Key Insights Section */}
                    <section>
                        <div className="flex items-center gap-2 text-indigo-400 mb-4">
                            <Lightbulb className="w-4 h-4" />
                            <h3 className="text-sm font-bold uppercase tracking-widest text-indigo-400/80">Key Insights</h3>
                        </div>

                        {isLoading ? (
                            <div className="space-y-4 animate-pulse">
                                <div className="h-4 bg-white/5 rounded w-full"></div>
                                <div className="h-4 bg-white/5 rounded w-5/6"></div>
                                <div className="h-4 bg-white/5 rounded w-4/6"></div>
                            </div>
                        ) : (
                            <div className="prose prose-sm prose-invert max-w-none prose-p:text-gray-300 prose-li:text-gray-300">
                                <ReactMarkdown>{insights || "_No insights generated yet._"}</ReactMarkdown>
                            </div>
                        )}
                    </section>

                    {/* Status & Deep Chat Access - ONLY IN STUDY MODE (NOT PROJECT VIEW) */}
                    {!isProjectView && (
                        <section className="pt-6 border-t border-white/5">
                            <div className="glass-indigo p-5 rounded-2xl flex flex-col gap-4">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <h4 className="text-sm font-semibold text-white">Full Paper Index</h4>
                                        <p className="text-xs text-gray-400">Deep reasoning & contextual citations</p>
                                    </div>
                                    {ingestionStatus[paper.id]?.status === 'completed' ? (
                                        <span className="text-green-400 text-xs font-bold leading-none flex items-center gap-1">
                                            <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                                            READY
                                        </span>
                                    ) : (
                                        <span className="text-orange-400 text-xs font-bold leading-none">
                                            {ingestionStatus[paper.id]?.status?.toUpperCase() || 'NOT_STARTED'}
                                        </span>
                                    )}
                                </div>

                                <button
                                    onClick={() => onOpenAssistant(paper)}
                                    className="w-full py-3 bg-white hover:bg-gray-200 text-black text-sm font-bold rounded-xl transition flex items-center justify-center gap-2"
                                >
                                    <MessageSquare className="w-4 h-4" />
                                    Interactive Synthesis
                                </button>
                            </div>
                        </section>
                    )}
                </div>

                {/* Quick Chat Input (Draft) - ONLY IN STUDY MODE */}
                {!isProjectView && (
                    <div className="p-4 border-t border-white/5 bg-[#0a0a0b]">
                        <div className="relative group">
                            <input
                                type="text"
                                placeholder="Ask a quick question..."
                                className="w-full bg-[#161618] border border-white/5 rounded-2xl px-5 py-4 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition group-hover:border-white/10"
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter') {
                                        onOpenAssistant(paper);
                                    }
                                }}
                            />
                            <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
                                <div className="text-[10px] text-gray-500 border border-white/10 px-1.5 py-0.5 rounded leading-none">
                                    ENTER
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </aside>
        </>
    );
};

export default ReaderPanel;
