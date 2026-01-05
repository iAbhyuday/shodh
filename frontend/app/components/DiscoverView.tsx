import React, { useState } from 'react';
import { Search, Loader2, X } from 'lucide-react';
import PaperCard from './PaperCard';

type Paper = {
    id: string;
    title: string;
    abstract: string;
    source?: string;
    metrics: {
        tags?: string[];
        core_idea?: string;
        approach?: string[];
    };
    url: string;
    published_date: string;
    authors: string;
    is_favorited: boolean;
    is_saved: boolean;
    github_url?: string;
    project_page?: string;
    thumbnail?: string;
    project_ids?: number[];
};

type Project = {
    id: number;
    name: string;
    description: string | null;
    created_at: string;
    paper_count: number;
};

interface DiscoverViewProps {
    searchQuery: string;
    setSearchQuery: (val: string) => void;
    onSearch: (e: React.FormEvent) => void;
    loading: boolean;
    error: boolean;
    feed: Paper[];
    onQuickRead: (paper: Paper) => void;
    onDeepRead: (paper: Paper) => void;
    onVisualize: (paper: Paper) => void;
    onAddPaperToProject: (projectId: number, paperId: string, paperTitle?: string, paper?: Paper) => void;
    projects: Project[];
    activeProjectMenu: string | null;
    setActiveProjectMenu: (id: string | null) => void;
    ingestionStatus: Record<string, { status: string; chunk_count: number | null }>;
    totalPages: number;
    currentPage: number;
    goToPage: (page: number) => void;
    totalPapers: number;
    onRetry: () => void;
    onToggleFavorite: (paper: Paper) => void;
    title?: string;
    subtitle?: string;
    showSearch?: boolean;
    // New Props for Sort/Filter
    availableTags?: string[];
    selectedTags?: string[];
    setSelectedTags?: (tags: string[]) => void;
    sortBy?: "date_desc" | "date_asc" | "title_asc" | "title_desc";
    setSortBy?: (sort: any) => void;
    onTagClick?: (tag: string) => void;
}

const DiscoverView: React.FC<DiscoverViewProps> = ({
    searchQuery,
    setSearchQuery,
    onSearch,
    loading,
    error,
    feed,
    onQuickRead,
    onDeepRead,
    onVisualize,
    onAddPaperToProject,
    projects,
    activeProjectMenu,
    setActiveProjectMenu,
    ingestionStatus,
    totalPages,
    currentPage,
    goToPage,
    totalPapers,
    onRetry,
    onToggleFavorite,
    title = "Discovery Horizon",
    subtitle = "Explore the global frontier of research publications.",
    showSearch = true,
    availableTags = [],
    selectedTags = [],
    setSelectedTags,
    sortBy = "date_desc",
    setSortBy,
    onTagClick
}) => {
    return (
        <>
            <div className="max-w-4xl mx-auto mb-16 relative animate-in fade-in slide-in-from-bottom-4 duration-700">
                <div className="text-center">
                    <h2 className="text-4xl font-bold text-white mb-3 tracking-tight">{title}</h2>
                    <p className="text-gray-400 text-base mb-10 max-w-2xl mx-auto">{subtitle}</p>

                    {showSearch && (
                        <div className="max-w-2xl mx-auto relative group flex flex-col gap-4">
                            <style>{`
                                @keyframes breathing {
                                    0%, 100% { 
                                        box-shadow: 0 0 40px -10px rgba(79, 70, 229, 0.2);
                                        border-color: rgba(255, 255, 255, 0.1);
                                        background-color: rgba(255, 255, 255, 0.03);
                                    }
                                    50% { 
                                        box-shadow: 0 0 60px 0px rgba(79, 70, 229, 0.4);
                                        border-color: rgba(255, 255, 255, 0.3);
                                        background-color: rgba(255, 255, 255, 0.07);
                                    }
                                }
                                .animate-breathing {
                                    animation: breathing 3s ease-in-out infinite;
                                }
                            `}</style>
                            <form onSubmit={onSearch} className="relative flex items-center">
                                <Search className={`absolute left-5 w-6 h-6 text-gray-400 group-focus-within:text-indigo-400 transition-colors z-10 ${loading ? 'animate-pulse' : ''}`} />
                                <input
                                    type="text"
                                    placeholder="Search the global knowledge base..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    className={`w-full bg-white/[0.05] backdrop-blur-3xl border border-white/20 hover:border-white/40 focus:border-indigo-500/60 rounded-2xl pl-14 pr-6 py-5 text-lg text-white placeholder:text-gray-500 focus:outline-none focus:ring-8 focus:ring-indigo-500/5 shadow-[0_0_80px_-20px_rgba(0,0,0,0.6)] transition-all ${loading ? 'animate-breathing !border-white/30' : ''}`}
                                />
                            </form>
                            <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500/10 via-purple-500/10 to-indigo-500/10 rounded-3xl blur-xl opacity-0 group-focus-within:opacity-100 transition duration-1000 pointer-events-none" />

                            {/* Sort & Filter Controls - Only show when searching or results exist */}
                            {(searchQuery || feed.length > 0 || selectedTags.length > 0) && setSortBy && setSelectedTags && (
                                <div className="flex gap-4 justify-end items-center animate-in fade-in slide-in-from-top-2 duration-300 flex-wrap">
                                    {/* Active Filter Chips */}
                                    {selectedTags.map(tag => (
                                        <div key={tag} className="flex items-center gap-2 px-3 py-2 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-sm font-bold">
                                            <span>#{tag}</span>
                                            <button
                                                onClick={() => setSelectedTags(selectedTags.filter(t => t !== tag))}
                                                className="hover:text-white transition-colors"
                                            >
                                                <X className="w-4 h-4" />
                                            </button>
                                        </div>
                                    ))}

                                    {/* Sort Dropdown */}
                                    <div className="relative">
                                        <select
                                            value={sortBy}
                                            onChange={(e) => setSortBy(e.target.value)}
                                            className="appearance-none bg-[#161618] border border-white/10 text-gray-300 text-sm font-medium py-2 pl-4 pr-10 rounded-xl focus:outline-none focus:border-indigo-500/50 hover:border-white/20 transition-all cursor-pointer"
                                        >
                                            <option value="date_desc">Newest First</option>
                                            <option value="date_asc">Oldest First</option>
                                            <option value="title_asc">Name (A-Z)</option>
                                            <option value="title_desc">Name (Z-A)</option>
                                        </select>
                                        <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-gray-500">
                                            <svg className="fill-current h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"><path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z" /></svg>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>


            <section>
                {loading && feed.length === 0 ? (
                    <div className="max-w-2xl mx-auto flex flex-col gap-8">
                        {[1, 2, 3].map((i) => (
                            <div key={i} className="bg-neutral-900 rounded-2xl border border-white/5 p-8 animate-pulse">
                                <div className="flex justify-between items-start mb-4">
                                    <div className="flex-1 space-y-3">
                                        <div className="h-6 bg-neutral-800 rounded w-3/4"></div>
                                        <div className="h-4 bg-neutral-800 rounded w-1/2"></div>
                                    </div>
                                    <div className="h-6 w-20 bg-neutral-800 rounded ml-4"></div>
                                </div>
                                <div className="space-y-2 mb-4">
                                    <div className="h-3 bg-neutral-800 rounded w-full"></div>
                                    <div className="h-3 bg-neutral-800 rounded w-full"></div>
                                    <div className="h-3 bg-neutral-800 rounded w-4/5"></div>
                                </div>
                            </div>
                        ))}
                    </div>
                ) : error ? (
                    <div className="text-center py-20 text-red-400 bg-red-900/10 rounded-3xl border border-red-900/20 max-w-2xl mx-auto">
                        <p className="text-lg font-bold">Unable to connect to Shodh Server.</p>
                        <p className="text-sm mt-2 text-gray-500">Please ensure the backend is running.</p>
                        <button onClick={onRetry} className="mt-8 px-8 py-3 bg-white text-black font-bold rounded-2xl hover:bg-gray-200 transition-all shadow-xl shadow-white/5">
                            Retry Connection
                        </button>
                    </div>
                ) : (
                    <div className="max-w-5xl mx-auto">
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                            {feed.map((paper) => (
                                <PaperCard
                                    key={paper.id}
                                    paper={paper}
                                    onQuickRead={onQuickRead}
                                    onDeepRead={onDeepRead}
                                    onVisualize={onVisualize}
                                    onAddPaperToProject={onAddPaperToProject}
                                    onToggleFavorite={onToggleFavorite}
                                    projects={projects}
                                    activeProjectMenu={activeProjectMenu}
                                    setActiveProjectMenu={setActiveProjectMenu}
                                    ingestionStatus={ingestionStatus}
                                    onTagClick={onTagClick}
                                />
                            ))}
                        </div>

                        {/* Pagination Controls */}
                        {totalPages > 1 && (
                            <div className="max-w-2xl mx-auto mt-16 flex flex-col items-center gap-6">
                                <div className="flex items-center justify-center gap-3">
                                    <button
                                        onClick={() => goToPage(currentPage - 1)}
                                        disabled={currentPage === 1}
                                        className="px-6 py-3 rounded-2xl bg-[#161618] text-white hover:bg-[#1c1c1e] disabled:opacity-30 disabled:cursor-not-allowed transition-all border border-white/5 font-bold text-sm uppercase tracking-widest"
                                    >
                                        Prev
                                    </button>

                                    <div className="flex gap-2">
                                        {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                                            let pageNum;
                                            if (totalPages <= 5) pageNum = i + 1;
                                            else if (currentPage <= 3) pageNum = i + 1;
                                            else if (currentPage >= totalPages - 2) pageNum = totalPages - 4 + i;
                                            else pageNum = currentPage - 2 + i;

                                            return (
                                                <button
                                                    key={i}
                                                    onClick={() => goToPage(pageNum)}
                                                    className={`w-12 h-12 rounded-2xl transition-all border ${currentPage === pageNum
                                                        ? 'bg-indigo-600 border-indigo-500 text-white shadow-lg shadow-indigo-500/20'
                                                        : 'bg-[#161618] border-white/5 text-gray-500 hover:border-white/10 hover:text-white'
                                                        } font-bold text-sm`}
                                                >
                                                    {pageNum}
                                                </button>
                                            );
                                        })}
                                    </div>

                                    <button
                                        onClick={() => goToPage(currentPage + 1)}
                                        disabled={currentPage === totalPages}
                                        className="px-6 py-3 rounded-2xl bg-[#161618] text-white hover:bg-[#1c1c1e] disabled:opacity-30 disabled:cursor-not-allowed transition-all border border-white/5 font-bold text-sm uppercase tracking-widest"
                                    >
                                        Next
                                    </button>
                                </div>
                                <span className="text-[10px] font-bold text-gray-600 uppercase tracking-[0.2em]">
                                    Page {currentPage} of {totalPages} — {totalPapers} papers discoverable
                                </span>
                            </div>
                        )}
                    </div>
                )}
            </section>
        </>
    );
};

export default DiscoverView;
