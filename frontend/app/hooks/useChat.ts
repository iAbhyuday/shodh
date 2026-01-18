
import { useState, useCallback, useRef, useEffect } from 'react';
import { chatApi, conversationsApi } from '../lib/api-client';
import type { ChatMessage, Conversation } from '../lib/types';

export type ChatMode = 'rag' | 'abstract' | 'agent';

export const useChat = (selectedPaperId: string | null) => {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [useAgentMode, setUseAgentMode] = useState(false);
    const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
    const [jobId, setJobId] = useState<string | null>(null);

    // Track chat mode: 'rag' (full), 'abstract' (limited), 'agent'
    const [chatMode, setChatMode] = useState<ChatMode>('rag');

    // Load messages when conversation changes
    const loadConversation = useCallback(async (conversationId: string) => {
        setLoading(true);
        try {
            const history = await conversationsApi.getMessages(conversationId);
            setMessages(history);
            setActiveConversationId(conversationId);
        } catch (error) {
            console.error("Failed to load conversation:", error);
        } finally {
            setLoading(false);
        }
    }, []);

    // Start new conversation
    const startNewChat = useCallback(() => {
        setActiveConversationId(null);
        setMessages([]);
        setInput('');
        setChatMode('rag'); // Reset mode on new chat
    }, []);

    // Polling effect for background jobs
    useEffect(() => {
        if (!jobId || !activeConversationId) return;

        console.log(`Starting polling for job ${jobId} in conversation ${activeConversationId}`);
        const pollInterval = setInterval(async () => {
            try {
                const history = await conversationsApi.getMessages(activeConversationId);
                const lastMsg = history[history.length - 1];

                // Check if assistant has responded
                if (lastMsg && lastMsg.role === 'assistant') {
                    setMessages(history);
                    setLoading(false);
                    setJobId(null); // Stop polling
                    clearInterval(pollInterval);
                }
            } catch (error) {
                console.error("Polling error:", error);
            }
        }, 2000); // Poll every 2 seconds

        // Timeout after 5 minutes
        const timeout = setTimeout(() => {
            if (jobId) {
                setLoading(false);
                setJobId(null);
                clearInterval(pollInterval);
                alert("Agent job timed out. Please check back later.");
            }
        }, 300000);

        return () => {
            clearInterval(pollInterval);
            clearTimeout(timeout);
        };
    }, [jobId, activeConversationId]);

    const sendMessage = useCallback(async () => {
        if (!input.trim() || loading) return;

        const userMsg: ChatMessage = { role: 'user', content: input };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setLoading(true);

        try {
            const result = await chatApi.sendMessage({
                message: userMsg.content,
                conversation_id: activeConversationId,
                paper_id: selectedPaperId || undefined,
                history: messages, // Send partial history for context
                use_agent: useAgentMode,
                use_job: useAgentMode // Automatically use job if agent mode is on
            });

            // Handle Async Job Response
            if (result && result.job_id) {
                console.log("Job started:", result.job_id);
                setJobId(result.job_id);
                setActiveConversationId(result.conversation_id);
                setChatMode('agent');
                // Loading state remains true until polling finishes
                return;
            }

            // Handle Standard Streaming Response (Response object)
            if (result instanceof Response) {
                if (!result.body) return;

                const reader = result.body.getReader();
                const decoder = new TextDecoder();
                let assistantMsg: ChatMessage = { role: 'assistant', content: '', citations: [] };
                let isFirstChunk = true;
                let metadataBuffer = '';

                setMessages(prev => [...prev, assistantMsg]);

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    const chunk = decoder.decode(value);

                    // First chunk contains JSON metadata on first line
                    if (isFirstChunk) {
                        metadataBuffer += chunk;
                        const newlineIdx = metadataBuffer.indexOf('\n');
                        if (newlineIdx !== -1) {
                            try {
                                const metadata = JSON.parse(metadataBuffer.substring(0, newlineIdx));
                                // Set chat mode from metadata
                                if (metadata.mode) {
                                    setChatMode(metadata.mode as ChatMode);
                                    console.log('[Chat] Mode:', metadata.mode);
                                }
                                if (metadata.conversation_id) {
                                    setActiveConversationId(metadata.conversation_id);
                                }
                                // Extract citations from metadata
                                if (metadata.citations && Array.isArray(metadata.citations)) {
                                    assistantMsg.citations = metadata.citations;
                                    console.log('[Chat] Citations:', metadata.citations.length);
                                }
                            } catch (e) {
                                console.warn('Failed to parse metadata:', e);
                            }
                            // Add remaining content after metadata
                            assistantMsg.content += metadataBuffer.substring(newlineIdx + 1);
                            isFirstChunk = false;
                        }
                    } else {
                        assistantMsg.content += chunk;
                    }

                    setMessages(prev => {
                        const newMsgs = [...prev];
                        newMsgs[newMsgs.length - 1] = { ...assistantMsg };
                        return newMsgs;
                    });
                }
                setLoading(false);
            }

        } catch (error) {
            console.error("Failed to send message:", error);
            setLoading(false);
            setMessages(prev => [...prev, { role: 'assistant', content: "**Error:** Failed to send message. Please try again." }]);
        }
    }, [input, loading, activeConversationId, selectedPaperId, messages, useAgentMode]);

    return {
        messages,
        input,
        loading,
        useAgentMode,
        activeConversationId,
        chatMode, // Expose chat mode for UI
        setInput,
        setUseAgentMode,
        sendMessage,
        loadConversation,
        startNewChat
    };
};

