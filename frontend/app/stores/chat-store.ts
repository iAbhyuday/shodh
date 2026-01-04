// Chat Store - manages conversations, messages, and streaming chat
import { create } from 'zustand';
import { conversationsApi, chatApi } from '../lib/api-client';
import type { ChatMessage, Conversation } from '../lib/types';

interface ChatState {
    // State
    messages: ChatMessage[];
    conversations: Conversation[];
    activeConversationId: number | null;
    chatInput: string;
    loading: boolean;
    useAgentMode: boolean;

    // Actions
    setChatInput: (input: string) => void;
    setActiveConversationId: (id: number | null) => void;
    setUseAgentMode: (use: boolean) => void;
    toggleAgentMode: () => void;
    addMessage: (message: ChatMessage) => void;
    updateLastMessage: (updates: Partial<ChatMessage>) => void;
    appendToLastMessage: (content: string) => void;
    fetchConversations: (params: { paperId?: string; projectId?: number }) => Promise<void>;
    loadConversation: (conversationId: number) => Promise<void>;
    startNewChat: () => void;
    sendMessage: (params: {
        message: string;
        paperId?: string;
        projectId?: number;
    }) => Promise<void>;
}

export const useChatStore = create<ChatState>((set, get) => ({
    // Initial state
    messages: [],
    conversations: [],
    activeConversationId: null,
    chatInput: "",
    loading: false,
    useAgentMode: false,

    // Setters
    setChatInput: (input) => set({ chatInput: input }),
    setActiveConversationId: (id) => set({ activeConversationId: id }),
    setUseAgentMode: (use) => set({ useAgentMode: use }),
    toggleAgentMode: () => set((state) => ({ useAgentMode: !state.useAgentMode })),

    // Message manipulation
    addMessage: (message) =>
        set((state) => ({ messages: [...state.messages, message] })),

    updateLastMessage: (updates) =>
        set((state) => {
            const messages = [...state.messages];
            const lastIndex = messages.length - 1;
            if (lastIndex >= 0 && messages[lastIndex].role === 'assistant') {
                messages[lastIndex] = { ...messages[lastIndex], ...updates };
            }
            return { messages };
        }),

    appendToLastMessage: (content) =>
        set((state) => {
            const messages = [...state.messages];
            const lastIndex = messages.length - 1;
            if (lastIndex >= 0 && messages[lastIndex].role === 'assistant') {
                messages[lastIndex] = {
                    ...messages[lastIndex],
                    content: messages[lastIndex].content + content,
                };
            }
            return { messages };
        }),

    // Fetch conversations for a paper or project
    fetchConversations: async ({ paperId, projectId }) => {
        try {
            const data = await conversationsApi.list({
                paper_id: paperId,
                project_id: projectId,
            });
            set({ conversations: data });
        } catch (e) {
            console.error("Failed to fetch conversations:", e);
        }
    },

    // Load messages for a conversation
    loadConversation: async (conversationId) => {
        try {
            const messages = await conversationsApi.getMessages(conversationId);
            set({
                messages: messages.map((m) => ({
                    role: m.role,
                    content: m.content,
                    citations: m.citations,
                })),
                activeConversationId: conversationId,
            });
        } catch (e) {
            console.error("Failed to load conversation:", e);
        }
    },

    // Start a new chat
    startNewChat: () =>
        set({ messages: [], activeConversationId: null }),

    // Send a message with streaming response
    sendMessage: async ({ message, paperId, projectId }) => {
        const { messages, activeConversationId, useAgentMode, fetchConversations } = get();

        if (!message.trim() || get().loading) return;

        // Add user message
        set((state) => ({
            messages: [...state.messages, { role: 'user', content: message }],
            chatInput: "",
            loading: true,
        }));

        // Add placeholder for assistant
        set((state) => ({
            messages: [...state.messages, { role: 'assistant', content: '', citations: [] }],
        }));

        try {
            const payload = {
                message,
                conversation_id: activeConversationId,
                paper_id: paperId,
                project_id: projectId,
                history: messages.slice(-10),
                use_agent: useAgentMode,
            };

            const response = await chatApi.sendMessage(payload);

            if (!response.body) throw new Error("No response body");

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let isFirstChunk = true;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const text = decoder.decode(value, { stream: true });
                buffer += text;

                // First chunk contains metadata
                if (isFirstChunk && buffer.includes('\n')) {
                    const splitIndex = buffer.indexOf('\n');
                    const metaLine = buffer.slice(0, splitIndex);
                    const remaining = buffer.slice(splitIndex + 1);

                    try {
                        const data = JSON.parse(metaLine);
                        if (data.conversation_id && !activeConversationId) {
                            set({ activeConversationId: data.conversation_id });
                            // Refresh conversations list
                            if (projectId) {
                                await fetchConversations({ projectId });
                            } else if (paperId) {
                                await fetchConversations({ paperId });
                            }
                        }
                        if (data.citations) {
                            get().updateLastMessage({ citations: data.citations });
                        }
                    } catch (parseError) {
                        console.error("Error parsing metadata:", parseError);
                    }
                    buffer = remaining;
                    isFirstChunk = false;
                }

                // Stream content
                if (!isFirstChunk && buffer.length > 0) {
                    const contentChunk = buffer;
                    buffer = '';
                    get().appendToLastMessage(contentChunk);
                }
            }
        } catch (e) {
            console.error("Chat error:", e);
            get().appendToLastMessage('\n\n[Sorry, I encountered an error. Please try again.]');
        } finally {
            set({ loading: false });
        }
    },
}));
