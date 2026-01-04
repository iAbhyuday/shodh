// Papers Store - manages feed, search, pagination, and paper actions
import { create } from 'zustand';
import { papersApi } from '../lib/api-client';
import type { Paper, SortOption } from '../lib/types';

interface PapersState {
    // State
    feed: Paper[];
    loading: boolean;
    error: boolean;
    searchQuery: string;
    availableTags: string[];
    selectedTags: string[];
    sortBy: SortOption;
    currentPage: number;
    totalPages: number;
    totalPapers: number;

    // Actions
    setSearchQuery: (query: string) => void;
    setSelectedTags: (tags: string[]) => void;
    setSortBy: (sort: SortOption) => void;
    setCurrentPage: (page: number) => void;
    fetchFeed: (options?: { queryOverride?: string }) => Promise<void>;
    fetchBookmarks: () => Promise<void>;
    fetchFavorites: () => Promise<void>;
    toggleFavorite: (paper: Paper) => Promise<void>;
    toggleSave: (paper: Paper) => Promise<void>;
    updatePaperInFeed: (paperId: string, updates: Partial<Paper>) => void;
}

// Helper to format abstract as notes
const formatAsNotes = (text: string): string => {
    if (!text) return "";
    const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 10);
    return sentences.map(s => `• ${s.trim()}`).join('\n');
};

export const usePapersStore = create<PapersState>((set, get) => ({
    // Initial state
    feed: [],
    loading: false,
    error: false,
    searchQuery: "",
    availableTags: [],
    selectedTags: [],
    sortBy: "date_desc",
    currentPage: 1,
    totalPages: 1,
    totalPapers: 0,

    // Setters
    setSearchQuery: (query) => set({ searchQuery: query }),
    setSelectedTags: (tags) => set({ selectedTags: tags }),
    setSortBy: (sort) => set({ sortBy: sort }),
    setCurrentPage: (page) => set({ currentPage: page }),

    // Update a paper in the feed
    updatePaperInFeed: (paperId, updates) =>
        set(state => ({
            feed: state.feed.map(p =>
                p.id === paperId ? { ...p, ...updates } : p
            )
        })),

    // Fetch feed or search results
    fetchFeed: async (options) => {
        const { searchQuery, selectedTags, sortBy, currentPage } = get();
        set({ loading: true, error: false });

        try {
            const effectiveQuery = options?.queryOverride ?? searchQuery;

            // Use search endpoint if query or tags exist
            if (effectiveQuery || selectedTags.length > 0) {
                const data = await papersApi.search({
                    q: effectiveQuery,
                    page: currentPage,
                    limit: 50,
                    sort: sortBy,
                    tags: selectedTags,
                });
                set({
                    feed: data.papers || [],
                    totalPages: data.total_pages || 1,
                    totalPapers: data.total || 0,
                    availableTags: data.tags || get().availableTags,
                });
            } else {
                const data = await papersApi.getFeed(currentPage, 50);
                set({
                    feed: data.papers || [],
                    totalPages: data.total_pages || 1,
                    totalPapers: data.total || 0,
                    availableTags: data.tags || get().availableTags,
                });
            }
        } catch (e) {
            console.error("Failed to fetch feed", e);
            set({ error: true });
        } finally {
            set({ loading: false });
        }
    },

    // Fetch saved papers (bookmarks)
    fetchBookmarks: async () => {
        set({ loading: true, feed: [], error: false });
        try {
            const data = await papersApi.getSaved();
            set({
                feed: data || [],
                totalPages: 1,
                totalPapers: data.length || 0,
            });
        } catch (e) {
            console.error("Failed to fetch bookmarks", e);
            set({ error: true, feed: [] });
        } finally {
            set({ loading: false });
        }
    },

    // Fetch favorited papers
    fetchFavorites: async () => {
        set({ loading: true, feed: [], error: false });
        try {
            const data = await papersApi.getFavorites();
            set({
                feed: data || [],
                totalPages: 1,
                totalPapers: data.length || 0,
            });
        } catch (e) {
            console.error("Failed to fetch favorites", e);
            set({ error: true, feed: [] });
        } finally {
            set({ loading: false });
        }
    },

    // Toggle favorite with optimistic update
    toggleFavorite: async (paper) => {
        const newValue = !paper.is_favorited;
        get().updatePaperInFeed(paper.id, { is_favorited: newValue });

        try {
            await papersApi.toggleFavorite(paper);
        } catch (e) {
            console.error("Failed to toggle favorite", e);
            // Revert on failure
            get().updatePaperInFeed(paper.id, { is_favorited: !newValue });
        }
    },

    // Toggle save with optimistic update
    toggleSave: async (paper) => {
        const newValue = !paper.is_saved;
        get().updatePaperInFeed(paper.id, { is_saved: newValue });

        try {
            await papersApi.toggleSave(paper, formatAsNotes(paper.abstract));
            if (newValue) {
                console.log("Saving paper with full metadata:", paper.id);
            }
        } catch (e) {
            console.error("Failed to toggle save", e);
            // Revert on failure
            get().updatePaperInFeed(paper.id, { is_saved: !newValue });
        }
    },
}));
