import React from 'react';
import { X, ExternalLink, BookOpen, Clock, Calendar, Sparkles } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import remarkGfm from 'remark-gfm';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import type { Paper } from '../lib/types';

interface QuickReadPanelProps {
    paper: Paper;
    isOpen: boolean;
    onClose: () => void;
    onDeepRead: (paper: Paper) => void;
    studyInsights?: string;
    isLoadingInsights?: boolean;
}

const QuickReadPanel: React.FC<QuickReadPanelProps> = ({
    paper,
    isOpen,
    onClose,
    onDeepRead,
    studyInsights,
    isLoadingInsights
}) => {
    return (
        <>
            {/* Backdrop */}
            <div
                className={`fixed inset-0 bg-black/40 backdrop-blur-sm z-[190] transition-opacity duration-300 ease-in-out ${isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}
                onClick={onClose}
            />

            {/* Panel */}
            <div className={`fixed top-0 right-0 h-full w-[600px] bg-[#0A0A0A] border-l border-white/10 shadow-2xl z-[200] transform transition-transform duration-300 ease-in-out flex flex-col ${isOpen ? 'translate-x-0' : 'translate-x-full'}`}>

                {/* Header */}
                <div className="flex items-start justify-between p-6 border-b border-white/10 bg-neutral-900/50 backdrop-blur-xl">
                    <div className="flex-1 pr-8">
                        <div className="flex items-center gap-2 mb-2 text-xs text-indigo-400 font-mono uppercase tracking-widest">
                            <span className="px-2 py-0.5 rounded-full bg-indigo-500/10 border border-indigo-500/20">
                                {new Date(paper.published_date).getFullYear()}
                            </span>
                            <span>{paper.id}</span>
                        </div>
                        <h2 className="text-xl font-bold text-white leading-tight">{paper.title}</h2>
                        <p className="text-sm text-gray-500 mt-2 font-medium">{paper.authors}</p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-lg hover:bg-white/5 text-gray-400 hover:text-white transition"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Content - Scrollable */}
                <div className="flex-1 overflow-y-auto p-8 customized-scrollbar">

                    {/* Action Bar */}
                    <div className="flex gap-4 mb-10">
                        <button
                            onClick={() => onDeepRead(paper)}
                            className="flex-1 flex items-center justify-center gap-2 px-6 py-4 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl shadow-lg shadow-indigo-500/20 active:scale-95 transition-all group"
                        >
                            <BookOpen className="w-5 h-5 group-hover:scale-110 transition-transform" />
                            Start Deep Read
                        </button>
                        <a
                            href={paper.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center justify-center gap-2 px-6 py-4 bg-white/5 hover:bg-white/10 text-gray-300 hover:text-white font-semibold rounded-xl border border-white/10 transition-all"
                        >
                            <ExternalLink className="w-5 h-5" />
                            ArXiv
                        </a>
                    </div>

                    {/* Quick Insights Section */}
                    <div className="mb-10 p-6 rounded-2xl bg-gradient-to-br from-indigo-500/10 to-purple-500/5 border border-indigo-500/20">
                        <div className="flex items-center gap-2 mb-4 text-indigo-300 font-bold uppercase tracking-wider text-xs">
                            <Sparkles className="w-4 h-4" />
                            Quick Insights
                        </div>

                        {isLoadingInsights ? (
                            <div className="space-y-3 animate-pulse">
                                <div className="h-4 bg-indigo-500/20 rounded w-3/4" />
                                <div className="h-4 bg-indigo-500/20 rounded w-full" />
                                <div className="h-4 bg-indigo-500/20 rounded w-5/6" />
                            </div>
                        ) : studyInsights ? (
                            <div className="prose prose-invert prose-sm max-w-none text-gray-300 leading-relaxed">
                                <ReactMarkdown
                                    remarkPlugins={[remarkMath, remarkGfm]}
                                    rehypePlugins={[rehypeKatex]}
                                >
                                    {studyInsights}
                                </ReactMarkdown>
                            </div>
                        ) : paper.metrics.core_idea ? (
                            <p className="text-gray-300 leading-relaxed">{paper.metrics.core_idea}</p>
                        ) : (
                            <p className="text-gray-500 italic">No AI insights generated yet.</p>
                        )}
                    </div>


                    {/* Tags */}
                    {paper.metrics.tags && paper.metrics.tags.length > 0 && (
                        <div>
                            <h3 className="text-sm font-bold text-gray-400 uppercase tracking-widest mb-4">Keywords</h3>
                            <div className="flex flex-wrap gap-2">
                                {paper.metrics.tags.map(tag => (
                                    <span key={tag} className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs text-gray-400 font-medium">
                                        #{tag}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </>
    );
};

export default QuickReadPanel;
