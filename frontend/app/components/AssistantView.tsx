import React from 'react';
import { Plus, ArrowLeft, MessageSquare, Loader2, Send } from 'lucide-react';
import CitedMarkdown, { Citation, SourceList } from './CitedMarkdown';

type Paper = {
    id: string;
    title: string;
    abstract: string;
    authors: string;
    url: string;
    published_date: string;
    is_favorited: boolean;
    is_saved: boolean;
    github_url?: string;
    project_page?: string;
    thumbnail?: string;
};

interface Message {
    role: 'user' | 'assistant';
    content: string;
    citations?: Citation[];
}

interface Conversation {
    id: number;
    paper_id: string;
    title: string;
    created_at: string;
    message_count: number;
}

interface AssistantViewProps {
    selectedPaper: Paper | null;
    conversations: Conversation[];
    activeConversationId: number | null;
    chatMessages: Message[];
    chatInput: string;
    chatLoading: boolean;
    useAgentMode: boolean;
    onStartNewChat: () => void;
    onLoadConversation: (id: number) => void;
    onBackToLibrary: () => void;
    onSetChatInput: (val: string) => void;
    onSendChatMessage: () => void;
    onToggleAgentMode: () => void;
}

const AssistantView: React.FC<AssistantViewProps> = ({
    selectedPaper,
    conversations,
    activeConversationId,
    chatMessages,
    chatInput,
    chatLoading,
    useAgentMode,
    onStartNewChat,
    onLoadConversation,
    onBackToLibrary,
    onSetChatInput,
    onSendChatMessage,
    onToggleAgentMode
}) => {
    return (
        <div className="flex h-[calc(100vh-4rem)]">
            {/* Conversation Sidebar */}
            {selectedPaper && (
                <div className="w-64 flex-shrink-0 flex flex-col bg-neutral-900 border-r border-white/10 p-4 h-full">
                    <button
                        onClick={onStartNewChat}
                        className="w-full flex items-center gap-2 px-4 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-500 transition mb-4 shadow-lg shadow-indigo-500/20"
                    >
                        <Plus className="w-5 h-5" />
                        New Chat
                    </button>

                    <div className="text-xs text-gray-500 uppercase tracking-wider mb-2">
                        Chat History
                    </div>

                    <div className="flex-1 overflow-y-auto space-y-2">
                        {conversations.length === 0 ? (
                            <p className="text-sm text-gray-500 text-center py-4">No conversations yet</p>
                        ) : (
                            conversations.map(conv => (
                                <button
                                    key={conv.id}
                                    onClick={() => onLoadConversation(conv.id)}
                                    className={`w-full text-left p-3 rounded-lg transition ${activeConversationId === conv.id
                                        ? 'bg-indigo-600/20 border border-indigo-500/30'
                                        : 'hover:bg-white/5 border border-transparent'
                                        }`}
                                >
                                    <div className="text-sm font-medium text-white line-clamp-2 break-all">
                                        {conv.title}
                                    </div>
                                    <div className="text-xs text-gray-500 mt-1">
                                        {conv.message_count} messages
                                    </div>
                                </button>
                            ))
                        )}
                    </div>
                </div>
            )}

            {/* Main Chat Area */}
            <div className="flex-1 min-w-0 flex flex-col">
                {selectedPaper ? (
                    <>
                        {/* Paper Header */}
                        <div className="flex items-center gap-4 p-4 bg-neutral-900 border-b border-white/10 shrink-0">
                            <button
                                onClick={onBackToLibrary}
                                className="p-2 rounded-lg hover:bg-neutral-800 transition"
                            >
                                <ArrowLeft className="w-5 h-5 text-gray-400" />
                            </button>
                            <div className="flex-1">
                                <h3 className="text-lg font-semibold text-white line-clamp-1">{selectedPaper.title}</h3>
                                <p className="text-sm text-gray-500">{selectedPaper.authors}</p>
                            </div>
                        </div>

                        {/* Chat Messages */}
                        <div className="flex-1 min-w-0 overflow-y-auto space-y-6 p-4 pr-6 customized-scrollbar bg-black/20 flex flex-col-reverse">
                            {chatMessages.length === 0 && (
                                <div className="text-center text-gray-500 py-10 mt-auto">
                                    <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-50" />
                                    <p>Ask a question about this paper</p>
                                </div>
                            )}
                            {[...chatMessages].reverse().map((msg, idx) => (
                                <div
                                    key={idx}
                                    className={`flex w-full ${msg.role === 'user' ? 'justify-end' : 'justify-start'} mb-6`}
                                >
                                    <div className={`flex gap-3 max-w-[85%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                                        {/* Avatar */}
                                        <div className="flex-shrink-0 mt-1">
                                            {msg.role === 'user' ? (
                                                null
                                            ) : (
                                                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center shadow-lg">
                                                    <span className="text-xs font-bold text-white">AI</span>
                                                </div>
                                            )}
                                        </div>

                                        <div className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'} max-w-[90%]`}>
                                            <div
                                                className={`${msg.role === 'user'
                                                    ? 'bg-indigo-600 text-white rounded-2xl rounded-tr-sm px-5 py-3 shadow-lg break-all overflow-hidden'
                                                    : 'text-gray-200 pl-4 border-l-2 border-indigo-500/50 break-all overflow-hidden'
                                                    }`}
                                            >
                                                {msg.role === 'user' ? (
                                                    <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                                                ) : (
                                                    <div className="prose prose-invert prose-p:leading-loose prose-p:mb-4 prose-headings:text-gray-100 prose-headings:font-semibold prose-strong:text-white prose-ul:my-4 prose-li:my-1 max-w-none">
                                                        <CitedMarkdown content={msg.content} citations={msg.citations} />
                                                    </div>
                                                )}
                                            </div>

                                            {/* Sources: collapsed by default — the inline chips are the
                                                primary citation; this is the "show your work" backup. */}
                                            {msg.role === 'assistant' && (
                                                <SourceList citations={msg.citations} />
                                            )}
                                        </div>
                                    </div>
                                </div>
                            ))}
                            {chatLoading && (
                                <div className="flex justify-start w-full animate-in fade-in slide-in-from-bottom-2 duration-500 mb-6">
                                    <style>{`
                                        @keyframes breathingThinking {
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
                                        .animate-breathing-thinking {
                                            animation: breathingThinking 3s ease-in-out infinite;
                                        }
                                    `}</style>
                                    <div className="flex items-center gap-3 px-6 py-3 rounded-2xl bg-white/[0.03] backdrop-blur-2xl border border-white/10 animate-breathing-thinking">
                                        <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
                                        <span className="text-sm font-medium text-gray-400 tracking-wide">Thinking...</span>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Chat Input */}
                        <div className="flex flex-col gap-2 p-4 bg-neutral-900 border-t border-white/10 shrink-0">
                            {/* Agent Mode Toggle */}
                            <div className="flex items-center gap-2 text-xs text-gray-400">
                                <button
                                    onClick={onToggleAgentMode}
                                    className={`px-3 py-1.5 rounded-full border transition-all ${useAgentMode
                                        ? 'bg-orange-600/20 border-orange-500 text-orange-400'
                                        : 'bg-neutral-800 border-white/10 text-gray-500'
                                        }`}
                                >
                                    {useAgentMode ? '🤖 Agent Mode' : '⚡ Fast Mode'}
                                </button>
                                <span>
                                    {useAgentMode
                                        ? 'Searches the paper, then answers with citations'
                                        : 'Single-shot answer — quicker, less thorough'}
                                </span>
                            </div>

                            <div className="flex gap-3">
                                <input
                                    type="text"
                                    value={chatInput}
                                    onChange={(e) => onSetChatInput(e.target.value)}
                                    onKeyDown={(e) => e.key === 'Enter' && onSendChatMessage()}
                                    placeholder="Ask about this paper..."
                                    className="flex-1 bg-neutral-800 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                />
                                <button
                                    onClick={onSendChatMessage}
                                    disabled={chatLoading || !chatInput.trim()}
                                    className="px-4 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-lg shadow-indigo-500/20"
                                >
                                    <Send className="w-5 h-5" />
                                </button>
                            </div>
                        </div>
                    </>
                ) : (
                    <div className="text-center py-20">
                        <MessageSquare className="w-16 h-16 mx-auto mb-4 text-gray-600" />
                        <h3 className="text-2xl font-bold text-white mb-2">Research Assistant</h3>
                        <p className="text-gray-400 mb-6">Select a paper from Bookmarks to start a discussion</p>
                        <button
                            onClick={onBackToLibrary}
                            className="px-6 py-3 bg-white text-black font-semibold rounded-lg hover:bg-gray-200 transition"
                        >
                            Go to Bookmarks
                        </button>
                    </div>
                )}
            </div>
        </div >
    );
};

export default AssistantView;
