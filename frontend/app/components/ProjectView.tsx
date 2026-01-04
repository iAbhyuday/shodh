import React from 'react';
import { ArrowLeft, Plus, Network, Send, Brain, Quote } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import remarkGfm from 'remark-gfm';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import PaperCard from './PaperCard';

type Paper = {
    id: string;
    title: string;
    abstract: string;
    source: string;
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
};

type Project = {
    id: number;
    name: string;
};

type Conversation = {
    id: number;
    title: string;
    message_count: number;
};

interface ProjectViewProps {
    project: Project;
    onClose: () => void;
    projectView: 'papers' | 'synthesis';
    setProjectView: (view: 'papers' | 'synthesis') => void;
    feed: Paper[];
    onQuickRead: (paper: Paper) => void;
    onDeepRead: (paper: Paper) => void;
    onVisualize?: (paper: Paper) => void;
    onAddPaperToProject: (projectId: number, paperId: string) => void;
    activeProjectMenu: string | null;
    setActiveProjectMenu: (id: string | null) => void;
    ingestionStatus: Record<string, { status: string; chunk_count: number | null }>;
    conversations: Conversation[];
    activeConversationId: number | null;
    onLoadConversation: (id: number) => void;
    onStartNewChat: () => void;
    chatMessages: any[];
    chatInput: string;
    setChatInput: (val: string) => void;
    onSendChatMessage: () => void;
    chatLoading: boolean;
    onFetchConversations: (paperId?: string, projectId?: number) => void;
    useAgentMode: boolean;
    onToggleAgentMode: () => void;
}

const ProjectView: React.FC<ProjectViewProps> = ({
    project,
    onClose,
    projectView,
    setProjectView,
    feed,
    onQuickRead,
    onDeepRead,
    onVisualize,
    onAddPaperToProject,
    activeProjectMenu,
    setActiveProjectMenu,
    ingestionStatus,
    conversations,
    activeConversationId,
    onLoadConversation,
    onStartNewChat,
    chatMessages,
    chatInput,
    setChatInput,
    onSendChatMessage,
    chatLoading,
    onFetchConversations,
    useAgentMode,
    onToggleAgentMode,
}) => {
    return (
        <div className={`mx-auto animate-in fade-in slide-in-from-left-4 duration-500 ${projectView === 'synthesis' ? 'max-w-none h-[calc(100vh-6rem)] flex flex-col' : 'max-w-5xl'}`}>
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-6">
                    <button
                        onClick={onClose}
                        className="p-3 bg-[#161618] hover:bg-[#1c1c1e] rounded-2xl text-gray-400 hover:text-white transition-all border border-white/5 active:scale-90"
                    >
                        <ArrowLeft className="w-5 h-5" />
                    </button>
                    <div>
                        <h2 className={`font-bold text-white tracking-tight ${projectView === 'synthesis' ? 'text-2xl' : 'text-3xl'}`}>{project.name}</h2>
                        {projectView !== 'synthesis' && (
                            <p className="text-sm text-gray-500 font-medium uppercase tracking-widest mt-1">
                                {feed.length} papers in collection
                            </p>
                        )}
                    </div>
                </div>

                <div className="flex p-1.5 bg-[#161618] border border-white/5 rounded-2xl shadow-xl">
                    <button
                        onClick={() => setProjectView('papers')}
                        className={`px-6 py-2.5 rounded-xl text-sm font-bold transition-all ${projectView === 'papers'
                            ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20'
                            : 'text-gray-500 hover:text-gray-300'
                            }`}
                    >
                        Papers
                    </button>
                    <button
                        onClick={() => {
                            setProjectView('synthesis');
                            onFetchConversations(undefined, project.id);
                        }}
                        className={`px-6 py-2.5 rounded-xl text-sm font-bold transition-all ${projectView === 'synthesis'
                            ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20'
                            : 'text-gray-500 hover:text-gray-300'
                            }`}
                    >
                        Synthesis
                    </button>
                </div>
            </div>

            {projectView === 'synthesis' ? (
                <div className="glass rounded-3xl border-none flex-1 flex overflow-hidden shadow-2xl animate-in zoom-in-95 duration-500">
                    <div className="w-72 border-r border-indigo-500/30 bg-black/20 flex flex-col shadow-[20px_0_40px_-10px_rgba(79,70,229,0.15)] z-10 relative">
                        <div className="p-4 border-b border-white/5">
                            <button
                                onClick={onStartNewChat}
                                className="w-full flex items-center justify-center gap-2 py-3 bg-indigo-600/10 text-indigo-400 text-xs font-bold rounded-xl hover:bg-indigo-600/20 transition-all border border-indigo-500/20 uppercase tracking-widest"
                            >
                                <Plus className="w-4 h-4" />
                                New Synthesis
                            </button>
                        </div>
                        <div className="flex-1 overflow-y-auto p-3 space-y-2 customized-scrollbar">
                            {conversations.length === 0 ? (
                                <div className="flex flex-col items-center justify-center h-full opacity-30 px-6 text-center">
                                    <Network className="w-8 h-8 mb-2" />
                                    <p className="text-[10px] font-bold uppercase tracking-tighter">No past chats</p>
                                </div>
                            ) : (
                                conversations.map((conv) => (
                                    <button
                                        key={conv.id}
                                        onClick={() => onLoadConversation(conv.id)}
                                        className={`w-full text-left p-4 rounded-2xl transition-all ${activeConversationId === conv.id
                                            ? 'bg-indigo-600/20 border border-indigo-500/30 shadow-lg'
                                            : 'hover:bg-white/5 border border-transparent text-gray-400 hover:text-gray-200'
                                            }`}
                                    >
                                        <p className="text-xs font-bold line-clamp-2 break-all leading-relaxed">{conv.title}</p>
                                    </button>
                                ))
                            )}
                        </div>
                    </div>

                    <div className="flex-1 min-w-0 flex flex-col bg-black/10">
                        <div className="flex-1 min-w-0 overflow-y-auto p-8 space-y-10 flex flex-col-reverse customized-scrollbar">
                            {chatLoading && (
                                <div className="flex justify-start w-full animate-in fade-in slide-in-from-bottom-2 duration-500 mb-4">
                                    <style>{`
                                        @keyframes breathingSynthesis {
                                            0%, 100% { 
                                                box-shadow: 0 0 20px -5px rgba(79, 70, 229, 0.2);
                                                border-color: rgba(255, 255, 255, 0.1);
                                                background-color: rgba(255, 255, 255, 0.03);
                                            }
                                            50% { 
                                                box-shadow: 0 0 30px 0px rgba(79, 70, 229, 0.4);
                                                border-color: rgba(255, 255, 255, 0.3);
                                                background-color: rgba(255, 255, 255, 0.07);
                                            }
                                        }
                                        .animate-breathing-synthesis {
                                            animation: breathingSynthesis 3s ease-in-out infinite;
                                        }
                                    `}</style>
                                    <div className="flex items-center gap-3 px-6 py-3 rounded-2xl bg-white/[0.03] backdrop-blur-2xl border border-white/10 animate-breathing-synthesis">
                                        <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
                                        <span className="text-sm font-medium text-gray-400 tracking-wide">Thinking...</span>
                                    </div>
                                </div>
                            )}
                            {[...chatMessages].reverse().map((msg, idx) => (
                                <div
                                    key={idx}
                                    className={`flex w-full ${msg.role === 'user' ? 'justify-end' : 'justify-start'} mb-8`}
                                >
                                    <div className={`flex gap-4 max-w-[80%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                                        {/* Avatar */}
                                        <div className="flex-shrink-0 mt-1">
                                            {msg.role === 'user' ? (
                                                null
                                            ) : (
                                                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg">
                                                    <Brain className="w-4 h-4 text-white" />
                                                </div>
                                            )}
                                        </div>

                                        <div className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'} max-w-full`}>
                                            <div
                                                className={`${msg.role === 'user'
                                                    ? 'bg-indigo-600 text-white rounded-2xl rounded-tr-sm px-6 py-4 shadow-lg break-words whitespace-pre-wrap'
                                                    : 'text-gray-200 pl-4 border-l-2 border-indigo-500/50 break-words w-full'
                                                    }`}
                                            >
                                                {msg.role === 'user' ? (
                                                    <p className="leading-relaxed">{msg.content}</p>
                                                ) : (
                                                    <div className="prose prose-invert prose-p:leading-loose prose-p:mb-4 prose-headings:text-gray-100 prose-headings:font-semibold prose-strong:text-white prose-ul:my-4 prose-li:my-1 max-w-none break-words">
                                                        <ReactMarkdown
                                                            remarkPlugins={[remarkMath, remarkGfm]}
                                                            rehypePlugins={[rehypeKatex]}
                                                            components={{
                                                                a: ({ node, ...props }) => {
                                                                    const href = props.href || '';

                                                                    // Handle grouped citations
                                                                    if (href.startsWith('#citation-group-')) {
                                                                        const indices = href.replace('#citation-group-', '').split('-').map(i => parseInt(i) - 1);
                                                                        const citations = indices.map(i => msg.citations?.[i]).filter(Boolean);

                                                                        if (citations.length === 0) return null;

                                                                        return (
                                                                            <span className="relative inline-block ml-1 group align-baseline">
                                                                                <span className="cursor-help px-1 py-0.5 rounded-full text-[10px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 hover:bg-indigo-500/30 transition-colors inline-flex items-center justify-center mx-0.5 align-top mt-0.5 h-4 w-auto min-w-[16px]">
                                                                                    <Quote className="w-2.5 h-2.5" />
                                                                                    <span className="ml-0.5 text-[8px] opacity-70">{citations.length}</span>
                                                                                </span>
                                                                                <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-96 max-h-80 overflow-y-auto customized-scrollbar p-3 bg-[#1A1A1A] border border-white/10 rounded-xl shadow-2xl z-50 text-xs text-gray-300 opacity-0 group-hover:opacity-100 invisible group-hover:visible transition-opacity whitespace-normal backdrop-blur-xl flex flex-col gap-3">
                                                                                    {/* Bridge to prevent hover loss */}
                                                                                    <span className="absolute -bottom-2 left-0 w-full h-2 bg-transparent" />
                                                                                    {citations.map((citation, idx) => (
                                                                                        <span key={idx} className="block pb-2 border-b border-white/5 last:border-0 last:pb-0">
                                                                                            <span className="block font-bold text-indigo-400 mb-1 tracking-wide uppercase text-[10px]">
                                                                                                {citation?.section} <span className="text-gray-500 ml-1">[{indices[idx] + 1}]</span>
                                                                                            </span>
                                                                                            <span className="leading-relaxed">
                                                                                                {citation?.summary ? (
                                                                                                    <span className="text-gray-300 italic">{citation.summary}</span>
                                                                                                ) : (
                                                                                                    <span>{citation?.content.slice(0, 400)}...</span>
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
                                                                        const citation = msg.citations?.[index];
                                                                        return (
                                                                            <span className="relative inline-block ml-1 group align-baseline">
                                                                                <span className="cursor-help px-1 py-0.5 rounded-full text-[10px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 hover:bg-indigo-500/30 transition-colors inline-flex items-center justify-center mx-0.5 align-top mt-0.5 h-4 w-4">
                                                                                    <Quote className="w-2.5 h-2.5" />
                                                                                </span>
                                                                                {citation && (
                                                                                    <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-80 p-3 bg-[#1A1A1A] border border-white/10 rounded-xl shadow-2xl z-50 text-xs text-gray-300 opacity-0 group-hover:opacity-100 invisible group-hover:visible transition-opacity whitespace-normal backdrop-blur-xl">
                                                                                        {/* Bridge to prevent hover loss */}
                                                                                        <span className="absolute -bottom-2 left-0 w-full h-2 bg-transparent" />
                                                                                        <span className="block font-bold text-indigo-400 mb-1 tracking-wide uppercase text-[10px]">{citation.section}</span>
                                                                                        <span className="leading-relaxed">
                                                                                            {citation.summary ? (
                                                                                                <span className="text-gray-300 italic">{citation.summary}</span>
                                                                                            ) : (
                                                                                                <span>{citation.content.slice(0, 600)}...</span>
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
                                                            {msg.content
                                                                .replace(/\\\[/g, '$$$')
                                                                .replace(/\\\]/g, '$$$')
                                                                .replace(/\\\(/g, '$')
                                                                .replace(/\\\)/g, '$')
                                                                // Group citations: [1], [2] -> #citation-group-1-2
                                                                .replace(/(\[\d+\](?:,\s*\[\d+\]|\s*\[\d+\])+)/g, (match: string) => {
                                                                    const nums = match.match(/\d+/g)?.join('-') || '';
                                                                    return `[citations](#citation-group-${nums})`;
                                                                })
                                                                .replace(/\[(\d+)\]/g, '[$1](#citation-$1)')
                                                            }
                                                        </ReactMarkdown>
                                                    </div>
                                                )}
                                            </div>

                                            {/* Citations (Only for Assistant) */}
                                            {/* Citations displayed inline via chips */}
                                        </div>
                                    </div>
                                </div>
                            ))}
                            {chatMessages.length === 0 && (
                                <div className="mt-auto py-24 text-center">
                                    <div className="w-20 h-20 bg-indigo-600/10 rounded-full flex items-center justify-center mx-auto mb-6 border border-indigo-500/20">
                                        <Network className="w-10 h-10 text-indigo-500/50" />
                                    </div>
                                    <h3 className="text-xl font-bold text-white mb-2">Project Synthesis</h3>
                                    <p className="text-gray-500 text-sm max-w-xs mx-auto">
                                        Ask anything about the papers in this collection. I'll synthesize information across all of them.
                                    </p>
                                </div>
                            )}
                        </div>
                        <div className="p-6 bg-[#0a0a0b] border-t border-white/5 flex gap-4">
                            <button
                                onClick={onToggleAgentMode}
                                className={`p-4 rounded-2xl transition-all border ${useAgentMode
                                    ? 'bg-purple-600 text-white border-purple-500 shadow-lg shadow-purple-500/20'
                                    : 'bg-[#161618] text-gray-500 border-white/5 hover:text-white hover:bg-[#1c1c1e]'}`}
                                title={useAgentMode ? "Agent Mode On" : "Enable Agent Mode"}
                            >
                                <Brain className="w-5 h-5" />
                            </button>
                            <input
                                type="text"
                                value={chatInput}
                                onChange={(e) => setChatInput(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && onSendChatMessage()}
                                placeholder="Ask about this collection..."
                                className="flex-1 bg-[#161618] border border-white/5 rounded-2xl px-6 py-4 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
                            />
                            <button
                                onClick={onSendChatMessage}
                                disabled={chatLoading}
                                className="p-4 bg-indigo-600 text-white rounded-2xl hover:bg-indigo-500 disabled:opacity-50 transition-all shadow-xl shadow-indigo-500/20 active:scale-90"
                            >
                                <Send className="w-5 h-5" />
                            </button>
                        </div>
                    </div>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                    {feed.map((paper) => (
                        <PaperCard
                            key={paper.id}
                            paper={paper}
                            onQuickRead={onQuickRead}
                            onDeepRead={onDeepRead}
                            onVisualize={onVisualize}
                            onAddPaperToProject={onAddPaperToProject}
                            activeProjectMenu={activeProjectMenu}
                            setActiveProjectMenu={setActiveProjectMenu}
                            ingestionStatus={ingestionStatus}
                            isProjectView={true}
                            onRemoveFromCurrentProject={(p) => onAddPaperToProject(project.id, p.id)}
                        />
                    ))}
                </div>
            )
            }
        </div >
    );
};

export default ProjectView;
