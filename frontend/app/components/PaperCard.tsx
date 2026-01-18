import React from 'react';
import { Plus, ChevronRight, Code, ExternalLink, Network, Trash2, Heart, BookOpen, Maximize2 } from 'lucide-react';

import { Paper, Project } from '../lib/types';

interface PaperCardProps {
    paper: Paper;
    onQuickRead: (paper: Paper) => void;
    onDeepRead: (paper: Paper) => void;
    onVisualize?: (paper: Paper) => void;
    onAddPaperToProject?: (projectId: string, paperId: string, paperTitle?: string, paper?: Paper) => void;
    projects?: Project[];
    activeProjectMenu: string | null;
    setActiveProjectMenu: (id: string | null) => void;
    isProjectView?: boolean;
    ingestionStatus?: Record<string, { status: string; chunk_count: number | null }>;
    isCreatingProject?: boolean;
    setIsCreatingProject?: (val: boolean) => void;
    setActiveView?: (view: any) => void;
    onRemoveFromCurrentProject?: (paper: Paper) => void;
    onToggleFavorite?: (paper: Paper) => void;
    onTagClick?: (tag: string) => void;
}

const isValidUrl = (url: string) => {
    try {
        new URL(url);
        return true;
    } catch {
        return false;
    }
};

// Defensive date formatting to prevent "Jan 1970" display
const formatDate = (dateString: string | undefined | null): string => {
    if (!dateString) return '';
    try {
        const date = new Date(dateString);
        // Check for invalid date or epoch (Jan 1970 indicates missing data)
        if (isNaN(date.getTime()) || date.getFullYear() < 1990) {
            return '';
        }
        return date.toLocaleDateString(undefined, { month: 'short', year: 'numeric' });
    } catch {
        return '';
    }
};

const PaperCard: React.FC<PaperCardProps> = ({
    paper,
    onQuickRead,
    onDeepRead,
    onVisualize,
    onAddPaperToProject,
    projects = [],
    activeProjectMenu,
    setActiveProjectMenu,
    isProjectView = false,
    ingestionStatus = {},
    isCreatingProject,
    setIsCreatingProject,
    setActiveView,
    onRemoveFromCurrentProject,
    onToggleFavorite,
    onTagClick
}) => {
    const [isExpanded, setIsExpanded] = React.useState(false);
    const metrics = paper.metrics || {};
    const tags = Array.isArray(metrics.tags) ? metrics.tags : [];
    const abstractThreshold = 200;
    const shouldShowExpand = paper.abstract.length > abstractThreshold;
    const displayedAbstract = isExpanded ? paper.abstract : (shouldShowExpand ? `${paper.abstract.substring(0, abstractThreshold)}...` : paper.abstract);

    return (
        <div
            key={paper.id}
            className={`glass rounded-2xl border border-white/5 hover:border-indigo-500/30 transition-all duration-500 shadow-2xl group relative ${activeProjectMenu === paper.id ? 'z-[60]' : ''}`}
        >
            {/* Top accent glow on hover */}
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-indigo-500/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

            {/* Thumbnail */}
            {paper.thumbnail && isValidUrl(paper.thumbnail) ? (
                <div className="relative w-full h-44 bg-[#0a0a0b] overflow-hidden rounded-t-2xl">
                    <img
                        src={paper.thumbnail}
                        alt={paper.title}
                        className="w-full h-full object-cover object-top opacity-80 group-hover:opacity-100 group-hover:scale-105 transition-all duration-700 rounded-t-2xl"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-[#161618] via-transparent to-transparent opacity-60" />

                    {/* Date Overlay */}
                    {formatDate(paper.published_date) && (
                        <div className="absolute top-4 right-4 z-10">
                            <span className="px-2 py-1 glass-indigo border border-indigo-500/30 rounded text-[10px] font-mono text-indigo-300 uppercase tracking-widest shadow-xl">
                                {formatDate(paper.published_date)}
                            </span>
                        </div>
                    )}
                </div>
            ) : (
                <div className="relative w-full h-12 bg-gradient-to-b from-[#161618] to-transparent">
                    {/* Date Overlay for no-thumbnail cards */}
                    {formatDate(paper.published_date) && (
                        <div className="absolute top-4 right-6 z-10">
                            <span className="px-2 py-1 glass-indigo border border-indigo-500/30 rounded text-[10px] font-mono text-indigo-300 uppercase tracking-widest shadow-xl">
                                {formatDate(paper.published_date)}
                            </span>
                        </div>
                    )}
                </div>
            )}

            <div
                className="p-6 relative cursor-pointer"
                onClick={() => onQuickRead(paper)}
            >
                {/* Header: Title */}
                <div className="mb-4">
                    <div className="flex justify-between items-start gap-4">
                        <h3 className="text-lg font-bold text-white leading-tight hover:text-indigo-400 transition-colors duration-300 line-clamp-2">
                            {paper.title}
                        </h3>
                    </div>
                    <p className="text-xs text-gray-500 mt-2 font-medium uppercase tracking-wide">
                        {(() => {
                            const authorList = paper.authors.split(',').map(a => a.trim());
                            if (authorList.length <= 4) return paper.authors;
                            return `${authorList.slice(0, 4).join(', ')} et al.`;
                        })()}
                    </p>
                </div>

                {/* Abstract Preview */}
                <div className="relative">
                    <p className="text-sm text-gray-400 leading-relaxed transition-all duration-300">
                        {displayedAbstract}
                    </p>
                    {shouldShowExpand && (
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                setIsExpanded(!isExpanded);
                            }}
                            className="text-xs font-bold text-indigo-400 hover:text-indigo-300 mt-1 uppercase tracking-widest flex items-center gap-1"
                        >
                            {isExpanded ? 'See less' : 'See more...'}
                        </button>
                    )}
                </div>

                {/* Hashtag Tags Row */}
                <div className="mt-4 flex flex-wrap gap-2">
                    {tags.map((tag, idx) => {
                        const TagComponent = onTagClick ? 'button' : 'span';
                        return (
                            <TagComponent
                                key={idx}
                                onClick={(e) => {
                                    if (onTagClick) {
                                        e.stopPropagation();
                                        onTagClick(tag);
                                    }
                                }}
                                className={`text-[10px] font-bold text-indigo-400/60 transition-colors ${onTagClick ? 'hover:text-indigo-400 hover:scale-105 active:scale-95 cursor-pointer' : ''}`}
                            >
                                #{tag.toLowerCase().replace(/\s+/g, '')}
                            </TagComponent>
                        );
                    })}
                </div>

                {/* Grouped Action Row Footer */}
                <div className="flex items-center justify-between pt-5 mt-4 border-t border-white/5" onClick={(e) => e.stopPropagation()}>
                    <div className="flex gap-1.5 items-center">
                        {onToggleFavorite && (
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onToggleFavorite(paper);
                                }}
                                className={`p-2.5 rounded-xl transition-all border hover:scale-105 ${paper.is_favorited
                                    ? 'bg-pink-500/10 text-pink-500 border-pink-500/30 shadow-lg shadow-pink-500/10'
                                    : 'bg-white/10 text-gray-300 hover:text-pink-400 hover:bg-white/20 border-white/10'
                                    }`}
                                title={paper.is_favorited ? "Remove from Favourites" : "Add to Favourites"}
                            >
                                <Heart className={`w-4 h-4 ${paper.is_favorited ? 'fill-current' : ''}`} />
                            </button>
                        )}
                        {/* Deep Read Button (Primary Action) */}
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                onDeepRead(paper);
                            }}
                            className="p-2 bg-indigo-600/10 hover:bg-indigo-600/20 text-indigo-400 rounded-lg transition-colors"
                            title="Deep Read"
                        >
                            <Maximize2 className="w-4 h-4" />
                        </button>

                        {/* PDF Link */}
                        <a
                            href={paper.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="p-2.5 rounded-xl bg-white/10 text-gray-300 hover:text-white hover:bg-white/20 hover:scale-105 transition-all border border-white/10"
                            title="View PDF"
                        >
                            <ExternalLink className="w-4 h-4" />
                        </a>

                        {/* GitHub Link */}
                        {paper.github_url && (
                            <a
                                href={paper.github_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="p-2.5 rounded-xl bg-white/10 text-gray-300 hover:text-white hover:bg-white/20 hover:scale-105 transition-all border border-white/10"
                                title="View Code"
                            >
                                <Code className="w-4 h-4" />
                            </a>
                        )}

                        {/* Mindmap / Visualize */}
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                onVisualize?.(paper);
                            }}
                            className="p-2.5 rounded-xl bg-white/10 text-gray-300 hover:text-white hover:bg-white/20 hover:scale-105 transition-all border border-white/10"
                            title="Open Mindmap"
                        >
                            <Network className="w-4 h-4" />
                        </button>

                        {!isProjectView && (
                            <div className="relative">
                                <button
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        setActiveProjectMenu(activeProjectMenu === paper.id ? null : paper.id);
                                    }}
                                    className={`p-2.5 rounded-xl transition-all border hover:scale-105 ${activeProjectMenu === paper.id
                                        ? 'bg-indigo-600 text-white border-indigo-500 shadow-lg shadow-indigo-500/20'
                                        : paper.project_ids && paper.project_ids.length > 0
                                            ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30 hover:bg-indigo-500/20 hover:text-indigo-300'
                                            : 'bg-indigo-500/20 text-indigo-300 hover:text-white hover:bg-indigo-500/30 border-indigo-500/20 hover:border-indigo-500/40'
                                        }`}
                                    title="Add to Project"
                                >
                                    <Plus className="w-4 h-4" />
                                </button>

                                {activeProjectMenu === paper.id && (
                                    <div className="absolute left-0 top-full mt-2 w-48 bg-[#0a0a0b] border border-white/10 rounded-xl shadow-2xl z-50 p-2 animate-in fade-in slide-in-from-top-2 duration-200">
                                        <p className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest p-2 border-b border-white/5 mb-1 text-left">Add to Project</p>
                                        <div className="max-h-40 overflow-y-auto customized-scrollbar">
                                            {projects.map((p) => (
                                                <button
                                                    key={p.id}
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        onAddPaperToProject?.(p.id, paper.id, paper.title, paper);
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
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}

                        {isProjectView && onRemoveFromCurrentProject && (
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onRemoveFromCurrentProject(paper);
                                }}
                                className="p-2.5 rounded-xl bg-red-500/10 text-red-400 hover:bg-red-500/20 hover:text-red-300 transition-all border border-red-500/20 hover:border-red-500/30 hover:scale-105 shadow-lg shadow-red-500/10"
                                title="Remove from Project"
                            >
                                <Trash2 className="w-4 h-4" />
                            </button>
                        )}
                    </div>
                </div>

                {/* Ingestion Status Overlay */}
                {paper.is_saved && (
                    <div className="absolute top-0 right-6 -translate-y-1/2">
                        {(() => {
                            const status = ingestionStatus[paper.id]?.status;
                            if (['processing', 'indexing'].includes(status || '')) return <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />;
                            return null;
                        })()}
                    </div>
                )}
            </div>
        </div>
    );
};

export default PaperCard;
