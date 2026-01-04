import React from 'react';
import { MessageSquare, Quote, Send, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import remarkGfm from 'remark-gfm';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';

interface Message {
    role: 'user' | 'assistant';
    content: string;
    citations?: any[];
}

interface ChatPanelProps {
    messages: Message[];
    input: string;
    loading: boolean;
    onInputChange: (val: string) => void;
    onSend: () => void;
    useAgent?: boolean;
    onToggleAgent?: () => void;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({
    messages,
    input,
    loading,
    onInputChange,
    onSend,
    useAgent = false,
    onToggleAgent
}) => {
    return (
        <div className="flex flex-col h-full bg-[#0A0A0A]">
            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto space-y-6 p-4 customized-scrollbar flex flex-col-reverse">
                {messages.length === 0 && (
                    <div className="text-center text-gray-500 py-20 mt-auto">
                        <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-50" />
                        <p>Ask a question about this paper</p>
                    </div>
                )}

                {[...messages].reverse().map((msg, idx) => (
                    <div key={idx} className={`flex w-full ${msg.role === 'user' ? 'justify-end' : 'justify-start'} mb-8`}>
                        <div className={`flex gap-4 max-w-[90%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                            {/* Avatar */}
                            <div className="flex-shrink-0 mt-1">
                                {msg.role === 'assistant' && (
                                    <div className="w-6 h-6 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg">
                                        <span className="text-[10px] font-bold text-white">AI</span>
                                    </div>
                                )}
                            </div>

                            <div className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'} min-w-0`}>
                                <div className={`${msg.role === 'user'
                                        ? 'bg-indigo-600 text-white rounded-2xl rounded-tr-sm px-5 py-3 shadow-lg'
                                        : 'text-gray-200 pl-4 border-l-2 border-indigo-500/50 w-full'
                                    }`}>
                                    {msg.role === 'user' ? (
                                        <p className="leading-relaxed whitespace-pre-wrap text-sm">{msg.content}</p>
                                    ) : (
                                        <div className="prose prose-invert prose-sm max-w-none">
                                            <ReactMarkdown
                                                remarkPlugins={[remarkMath, remarkGfm]}
                                                rehypePlugins={[rehypeKatex]}
                                                components={{
                                                    // ... reuse citation logic or simplify for DeepRead ...
                                                    // For MVP, just standard render or simplified citation chips
                                                }}
                                            >
                                                {msg.content}
                                            </ReactMarkdown>
                                        </div>
                                    )}
                                </div>
                                {/* Citations would go here */}
                            </div>
                        </div>
                    </div>
                ))}

                {loading && (
                    <div className="flex items-center gap-3 px-4 py-3 mb-6 animate-pulse">
                        <div className="w-2 h-2 rounded-full bg-indigo-500" />
                        <span className="text-sm text-gray-400">Thinking...</span>
                    </div>
                )}
            </div>

            {/* Input Area */}
            <div className="p-4 border-t border-white/10 bg-[#0A0A0A]">
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => onInputChange(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && onSend()}
                        placeholder="Ask a question..."
                        className="flex-1 bg-[#1A1A1A] border border-white/10 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 text-sm"
                    />
                    <button
                        onClick={onSend}
                        disabled={loading || !input.trim()}
                        className="px-4 bg-indigo-600 text-white rounded-lg hover:bg-indigo-500 disabled:opacity-50 transition"
                    >
                        <Send className="w-4 h-4" />
                    </button>
                </div>
            </div>
        </div>
    );
};
