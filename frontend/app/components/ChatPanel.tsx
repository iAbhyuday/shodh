import React, { useRef, useEffect } from 'react';
import { MessageSquare, Send, Loader2 } from 'lucide-react';
import { AssistantMessage } from './AssistantMessage';
import 'katex/dist/katex.min.css';

interface Message {
    role: 'user' | 'assistant';
    content: string;
    citations?: any[];
}

type ChatMode = 'rag' | 'abstract' | 'agent';

interface ChatPanelProps {
    messages: Message[];
    input: string;
    loading: boolean;
    onInputChange: (val: string) => void;
    onSend: () => void;
    useAgent?: boolean;
    onToggleAgent?: () => void;
    chatMode?: ChatMode; // 'rag', 'abstract', or 'agent'
    paperId?: string; // For fetching figures
}



export const ChatPanel: React.FC<ChatPanelProps> = ({
    messages,
    input,
    loading,
    onInputChange,
    onSend,
    useAgent = false,
    onToggleAgent,
    chatMode = 'rag',
    paperId
}) => {
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // Auto-resize textarea
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px';
        }
    }, [input]);

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (input.trim() && !loading) {
                onSend();
            }
        }
    };

    // Custom styles for math equations - indigo color
    const mathStyles = `
        .katex {
            color: #6366f1;
        }
        .katex .mord,
        .katex .mbin,
        .katex .mrel,
        .katex .mopen,
        .katex .mclose,
        .katex .mpunct,
        .katex .minner {
            color: #6366f1;
        }
        .katex .katex-html {
            color: #6366f1;
        }
    `;
    return (
        <>
            <style>{mathStyles}</style>
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

                                <div className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'} min-w-0`}>
                                    <div className={`${msg.role === 'user'
                                        ? 'bg-indigo-600 text-white rounded-2xl rounded-tr-sm px-5 py-3 shadow-lg'
                                        : 'text-gray-200 pl-4 border-l-2 border-indigo-500/50 w-full'
                                        }`}>
                                        {msg.role === 'user' ? (
                                            <p className="leading-relaxed whitespace-pre-wrap text-sm">{msg.content}</p>
                                        ) : (
                                            <AssistantMessage
                                                content={msg.content}
                                                citations={msg.citations}
                                                paperId={paperId}
                                            />
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}

                </div>

                {/* Thinking Indicator - Premium Breathing Effect */}
                {loading && (
                    <div className="flex items-center gap-3 px-6 py-2 animate-in fade-in duration-300">
                        <div className="relative flex items-center justify-center w-4 h-4">
                            <div className="absolute w-full h-full bg-indigo-500/30 rounded-full animate-ping" />
                            <div className="relative w-2 h-2 bg-indigo-400 rounded-full shadow-[0_0_10px_rgba(99,102,241,0.5)]" />
                        </div>
                        <span className="text-xs font-medium text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-400 animate-pulse tracking-wide">
                            THINKING...
                        </span>
                    </div>
                )}

                {/* Input Area */}
                <div className="p-4 border-t border-white/10 bg-[#0A0A0A]">
                    {/* Agent Mode Toggle */}
                    <div className="flex items-center gap-2 mb-2 text-xs">
                        {onToggleAgent && (
                            <button
                                onClick={onToggleAgent}
                                className={`px-2 py-1 rounded border transition-colors ${useAgent
                                    ? 'bg-orange-600/20 border-orange-500 text-orange-400'
                                    : 'bg-white/5 border-white/10 text-gray-500'
                                    }`}
                            >
                                {useAgent ? '🤖 Agent Mode' : '⚡ Fast Mode'}
                            </button>
                        )}
                    </div>

                    <div className="flex gap-3 items-end">
                        <textarea
                            ref={textareaRef}
                            value={input}
                            onChange={(e) => onInputChange(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="Ask a question..."
                            rows={1}
                            className="flex-1 bg-[#1A1A1A] border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 focus:border-indigo-500/50 text-sm resize-none min-h-[46px] max-h-[200px] customized-scrollbar transition-all shadow-inner"
                        />
                        <button
                            onClick={onSend}
                            disabled={loading || !input.trim()}
                            className="h-[46px] px-5 bg-gradient-to-r from-indigo-600 to-indigo-700 text-white rounded-xl hover:from-indigo-500 hover:to-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-indigo-500/20 flex items-center justify-center group"
                        >
                            {loading ? (
                                <Loader2 className="w-5 h-5 animate-spin" />
                            ) : (
                                <Send className="w-5 h-5 group-hover:translate-x-0.5 transition-transform" />
                            )}
                        </button>
                    </div>
                </div>
            </div>
        </>
    );
};
