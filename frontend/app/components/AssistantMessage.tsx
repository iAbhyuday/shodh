import React, { useState, useEffect, useMemo } from 'react';
import { Quote, X, ZoomIn } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import remarkGfm from 'remark-gfm';
import rehypeKatex from 'rehype-katex';
import { figuresApi, FigureData } from '../lib/api-client';
import 'katex/dist/katex.min.css';

interface Citation {
    id: number;
    content: string;
    section: string;
    summary?: string;
    figures?: string;
}

interface AssistantMessageProps {
    content: string;
    citations?: Citation[];
    paperId?: string;
}

/**
 * Basic content preprocessing - minimal sanitization only
 */
const preprocessContent = (content: string): string => {
    return content
        // Convert <br> to newlines
        .replace(/<br\s*\/?>/gi, '\n')
        // Remove stray HTML tags
        .replace(/<\/?(?:p|div|span)[^>]*>/gi, '')
        // Convert \[ \] and \( \) to $$ and $ for KaTeX compatibility
        .replace(/\\\[([\s\S]*?)\\\]/g, (_, math) => `$$${math.trim()}$$`)
        .replace(/\\\(([\s\S]*?)\\\)/g, (_, math) => `$${math.trim()}$`);
};

/**
 * Extract figure references from content (e.g., "Figure 1", "[Figure 2]", "Fig. 3")
 */
const extractFigureRefs = (content: string): string[] => {
    // Match various figure formats: [Figure 1], Figure 1, Fig. 1, figure 2
    const matches = content.match(/(?:\[)?(?:Figure|Fig\.?)\s*(\d+)(?:\])?/gi) || [];
    const figureIds = matches.map(m => {
        const match = m.match(/\d+/);
        return match ? match[0] : null;
    }).filter(Boolean) as string[];
    // Return unique figure IDs
    return [...new Set(figureIds)];
};

/**
 * Component that renders an assistant message with figures embedded as images
 */
export const AssistantMessage: React.FC<AssistantMessageProps> = ({
    content,
    citations = [],
    paperId
}) => {
    const [figures, setFigures] = useState<FigureData[]>([]);
    const [loadingFigures, setLoadingFigures] = useState(false);
    const [expandedFigure, setExpandedFigure] = useState<FigureData | null>(null);

    // Extract figure references from content
    const figureRefs = useMemo(() => extractFigureRefs(content), [content]);

    // Fetch figure data when content changes
    useEffect(() => {
        if (!paperId || figureRefs.length === 0) {
            setFigures([]);
            return;
        }

        const fetchFigures = async () => {
            setLoadingFigures(true);
            try {
                const figurePromises = figureRefs.map(figId =>
                    figuresApi.get(paperId, figId).catch(() => null)
                );
                const results = await Promise.all(figurePromises);
                setFigures(results.filter(Boolean) as FigureData[]);
            } catch (error) {
                console.error('Failed to fetch figures:', error);
            } finally {
                setLoadingFigures(false);
            }
        };

        fetchFigures();
    }, [paperId, figureRefs.join(',')]);

    // Process content to remove [Figure X] markers (they'll be shown in the figures section)
    const processedContent = useMemo(() => {
        let text = preprocessContent(content);
        // Keep figure references as styled text (not links)
        text = text.replace(/\[Figure\s*(\d+)\]/gi, '**Figure $1**');
        return text;
    }, [content]);

    // Build content for citations tooltip rendering
    const contentWithCitations = useMemo(() => {
        return processedContent
            // Group citations: [1], [2] -> #citation-group-1-2
            .replace(/(\[\d+\](?:,\s*\[\d+\]|\s*\[\d+\])+)/g, (match: string) => {
                const nums = match.match(/\d+/g)?.join('-') || '';
                return `[citations](#citation-group-${nums})`;
            })
            // Single citations: [1] -> #citation-1
            .replace(/\[(\d+)\]/g, '[$1](#citation-$1)');
    }, [processedContent]);

    return (
        <div className="prose prose-invert prose-sm max-w-none">
            <ReactMarkdown
                remarkPlugins={[remarkMath, remarkGfm]}
                rehypePlugins={[rehypeKatex]}
                components={{
                    a: ({ node, ...props }) => {
                        const href = props.href || '';

                        // Handle grouped citations
                        if (href.startsWith('#citation-group-')) {
                            const indices = href.replace('#citation-group-', '').split('-').map(i => parseInt(i) - 1);
                            const citationData = indices.map(i => citations[i]).filter(Boolean);
                            if (citationData.length === 0) return null;

                            return (
                                <span className="relative inline-block ml-1 group align-baseline">
                                    <span className="cursor-help px-1 py-0.5 rounded-full text-[10px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 hover:bg-indigo-500/30 transition-colors inline-flex items-center justify-center mx-0.5 align-top mt-0.5 h-4 w-auto min-w-[16px]">
                                        <Quote className="w-2.5 h-2.5" />
                                        <span className="ml-0.5 text-[8px] opacity-70">{citationData.length}</span>
                                    </span>
                                    <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-96 max-h-80 overflow-y-auto customized-scrollbar p-3 bg-[#1A1A1A] border border-white/10 rounded-xl shadow-2xl z-[9999] text-xs text-gray-300 opacity-0 group-hover:opacity-100 invisible group-hover:visible transition-opacity whitespace-normal backdrop-blur-xl flex flex-col gap-3">
                                        <span className="absolute -bottom-2 left-0 w-full h-2 bg-transparent" />
                                        {citationData.map((citation, idx) => (
                                            <span key={idx} className="block pb-2 border-b border-white/5 last:border-0 last:pb-0">
                                                <span className="block font-bold text-indigo-400 mb-1 tracking-wide uppercase text-[10px]">
                                                    {citation?.section} <span className="text-gray-500 ml-1">[{indices[idx] + 1}]</span>
                                                </span>
                                                <span className="leading-relaxed">
                                                    {citation?.summary ? (
                                                        <span className="text-gray-300 italic">{citation.summary}</span>
                                                    ) : (
                                                        <span>{citation?.content?.slice(0, 400)}...</span>
                                                    )}
                                                </span>
                                            </span>
                                        ))}
                                    </span>
                                </span>
                            );
                        }

                        // Handle single citations
                        if (href.startsWith('#citation-')) {
                            const index = parseInt(href.split('-')[1]) - 1;
                            const citation = citations[index];
                            return (
                                <span className="relative inline-block ml-1 group align-baseline">
                                    <span className="cursor-help px-1 py-0.5 rounded-full text-[10px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 hover:bg-indigo-500/30 transition-colors inline-flex items-center justify-center mx-0.5 align-top mt-0.5 h-4 w-4">
                                        <Quote className="w-2.5 h-2.5" />
                                    </span>
                                    {citation && (
                                        <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-80 p-3 bg-[#1A1A1A] border border-white/10 rounded-xl shadow-2xl z-[9999] text-xs text-gray-300 opacity-0 group-hover:opacity-100 invisible group-hover:visible transition-opacity whitespace-normal backdrop-blur-xl">
                                            <span className="absolute -bottom-2 left-0 w-full h-2 bg-transparent" />
                                            <span className="block font-bold text-indigo-400 mb-1 tracking-wide uppercase text-[10px]">{citation.section}</span>
                                            <span className="leading-relaxed">
                                                {citation.summary ? (
                                                    <span className="text-gray-300 italic">{citation.summary}</span>
                                                ) : (
                                                    <span>{citation.content?.slice(0, 600)}...</span>
                                                )}
                                            </span>
                                        </span>
                                    )}
                                </span>
                            );
                        }

                        return <a className="text-indigo-400 underline cursor-pointer hover:text-indigo-300 transition-colors" {...props} target="_blank" rel="noopener noreferrer" />;
                    }
                }}
            >
                {contentWithCitations}
            </ReactMarkdown>

            {/* Relevant Figures Section */}
            {figures.length > 0 && (
                <div className="mt-6 pt-4 border-t border-white/10">
                    <h4 className="text-sm font-semibold text-emerald-400 mb-4 flex items-center gap-2">
                        <span className="w-5 h-5 rounded bg-emerald-500/20 flex items-center justify-center">
                            📊
                        </span>
                        Relevant Figures
                        <span className="text-xs text-gray-500 font-normal">(click to enlarge)</span>
                    </h4>
                    <div className="grid gap-4">
                        {figures.map((fig) => (
                            <div key={fig.figure_id} className="bg-white/5 rounded-lg p-4 border border-white/10">
                                <div className="flex items-center justify-between mb-3">
                                    <span className="text-sm font-medium text-emerald-300">
                                        Figure {fig.figure_id}
                                    </span>
                                    <button
                                        onClick={() => setExpandedFigure(fig)}
                                        className="text-xs text-gray-400 hover:text-emerald-400 flex items-center gap-1 transition-colors"
                                    >
                                        <ZoomIn className="w-3 h-3" /> Expand
                                    </button>
                                </div>
                                <div
                                    className="relative cursor-pointer group"
                                    onClick={() => setExpandedFigure(fig)}
                                >
                                    <img
                                        src={`data:image/png;base64,${fig.data}`}
                                        alt={`Figure ${fig.figure_id}: ${fig.caption}`}
                                        className="w-full max-h-[400px] object-contain rounded-md bg-white"
                                    />
                                    <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors rounded-md flex items-center justify-center">
                                        <ZoomIn className="w-8 h-8 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
                                    </div>
                                </div>
                                <p className="text-sm text-gray-400 italic mt-3">
                                    {fig.caption}
                                </p>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Expanded Figure Modal */}
            {expandedFigure && (
                <div
                    className="fixed inset-0 z-[9999] bg-black/90 flex items-center justify-center p-4 overflow-auto"
                    onClick={() => setExpandedFigure(null)}
                >
                    <button
                        className="absolute top-4 right-4 text-white hover:text-gray-300 transition-colors z-10"
                        onClick={() => setExpandedFigure(null)}
                    >
                        <X className="w-8 h-8" />
                    </button>
                    <div
                        className="max-w-[95vw] max-h-[95vh] flex flex-col overflow-auto bg-gray-900 rounded-xl p-4"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="text-emerald-400 font-medium mb-3 text-lg flex-shrink-0">
                            Figure {expandedFigure.figure_id}
                        </div>
                        <div className="flex-1 min-h-0 overflow-auto flex items-center justify-center">
                            <img
                                src={`data:image/png;base64,${expandedFigure.data}`}
                                alt={`Figure ${expandedFigure.figure_id}`}
                                className="max-w-full max-h-[70vh] object-contain bg-white rounded-lg"
                            />
                        </div>
                        <p className="text-gray-300 text-sm mt-4 text-center flex-shrink-0">
                            {expandedFigure.caption}
                        </p>
                    </div>
                </div>
            )}

            {/* Loading indicator for figures */}
            {loadingFigures && figureRefs.length > 0 && (
                <div className="mt-4 text-xs text-gray-500 animate-pulse">
                    Loading figures...
                </div>
            )}
        </div>
    );
};
