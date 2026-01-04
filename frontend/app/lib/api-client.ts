// Centralized API client for Shodh
// Replaces inline fetch() calls scattered across page.tsx

import { API_URL } from './env';
import type { Paper, Project, PaginatedPapersResponse, Conversation, ChatMessage, SortOption } from './types';

// --- Helper Functions ---

async function fetchApi<T>(
    endpoint: string,
    options: RequestInit & { params?: Record<string, string | string[]> } = {}
): Promise<T> {
    const { params, ...fetchOptions } = options;

    let url = `${API_URL}${endpoint}`;

    if (params) {
        const searchParams = new URLSearchParams();
        Object.entries(params).forEach(([key, value]) => {
            if (Array.isArray(value)) {
                value.forEach(v => searchParams.append(key, v));
            } else if (value !== undefined && value !== '') {
                searchParams.append(key, value);
            }
        });
        url += `?${searchParams.toString()}`;
    }

    const response = await fetch(url, {
        ...fetchOptions,
        headers: {
            'Content-Type': 'application/json',
            ...fetchOptions.headers,
        },
    });

    if (!response.ok) {
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
}

// --- Papers API ---

export const papersApi = {
    getFeed: (page: number = 1, limit: number = 50): Promise<PaginatedPapersResponse> =>
        fetchApi('/feed', { params: { page: String(page), limit: String(limit) } }),

    search: (params: {
        q?: string;
        page?: number;
        limit?: number;
        sort?: SortOption;
        tags?: string[];
    }): Promise<PaginatedPapersResponse> =>
        fetchApi('/search', {
            params: {
                q: params.q || '',
                page: String(params.page || 1),
                limit: String(params.limit || 50),
                sort: params.sort || 'date_desc',
                tags: params.tags || [],
            },
        }),

    toggleFavorite: (paper: Paper): Promise<void> =>
        fetchApi('/favorite', {
            method: 'POST',
            body: JSON.stringify({
                paper_id: paper.id,
                title: paper.title,
                summary: paper.abstract,
                authors: paper.authors,
                url: paper.url,
                published_date: paper.published_date,
            }),
        }),

    toggleSave: (paper: Paper, notes: string): Promise<void> =>
        fetchApi('/save', {
            method: 'POST',
            body: JSON.stringify({
                paper_id: paper.id,
                title: paper.title,
                summary: paper.abstract,
                notes,
                authors: paper.authors,
                url: paper.url,
                published_date: paper.published_date,
                github_url: paper.github_url || null,
                project_page: paper.project_page || null,
                mindmap_json: null,
            }),
        }),

    getSaved: (): Promise<Paper[]> => fetchApi('/library/saved'),

    getFavorites: (): Promise<Paper[]> => fetchApi('/library/favorites'),

    getInsights: (paperId: string): Promise<{ insights: string }> =>
        fetchApi(`/insights/${paperId}`),

    getIngestionStatus: (paperId: string): Promise<{ ingestion_status: string }> =>
        fetchApi(`/ingestion-status/${paperId}`),
};

// --- Projects API ---

export const projectsApi = {
    list: (): Promise<Project[]> => fetchApi('/projects'),

    get: (projectId: number): Promise<{ papers: Paper[] }> =>
        fetchApi(`/projects/${projectId}`),

    create: (name: string, researchDimensions?: string): Promise<Project> =>
        fetchApi('/projects', {
            method: 'POST',
            body: JSON.stringify({
                name,
                research_dimensions: researchDimensions,
            }),
        }),

    delete: (projectId: number): Promise<void> =>
        fetchApi(`/projects/${projectId}`, { method: 'DELETE' }),

    addPaper: (projectId: number, paperId: string, title?: string): Promise<void> =>
        fetchApi(`/projects/${projectId}/add-paper`, {
            method: 'POST',
            body: JSON.stringify({ paper_id: paperId, title }),
        }),

    removePaper: (projectId: number, paperId: string): Promise<void> =>
        fetchApi(`/projects/${projectId}/paper/${paperId}`, { method: 'DELETE' }),
};

// --- Conversations API ---

export const conversationsApi = {
    list: (params: { paper_id?: string; project_id?: number }): Promise<Conversation[]> => {
        const queryParams: Record<string, string> = {};
        if (params.paper_id) queryParams.paper_id = params.paper_id;
        if (params.project_id) queryParams.project_id = String(params.project_id);
        return fetchApi('/conversations', { params: queryParams });
    },

    getMessages: (conversationId: number): Promise<ChatMessage[]> =>
        fetchApi(`/conversations/${conversationId}/messages`),
};

// --- Chat API (returns Response for streaming) ---

export const chatApi = {
    sendMessage: async (payload: {
        message: string;
        conversation_id?: number | null;
        paper_id?: string;
        project_id?: number;
        history?: ChatMessage[];
        use_agent?: boolean;
    }): Promise<Response> => {
        const endpoint = payload.project_id ? '/project-chat' : '/chat';
        const response = await fetch(`${API_URL}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        if (!response.ok) {
            throw new Error(`Chat API Error: ${response.status}`);
        }
        return response;
    },
};

// --- Ingestion API ---

export const ingestionApi = {
    getActiveJobs: (): Promise<Array<{
        paper_id: string;
        title: string;
        status: string;
        progress: number;
    }>> => fetchApi('/ingestion/jobs'),
};

// --- Ideas & Visualization API ---

export const ideasApi = {
    generate: (paperId: string): Promise<{ ideas: string[] }> =>
        fetchApi('/generate_ideas', {
            method: 'POST',
            body: JSON.stringify({ paper_id: paperId }),
        }),

    visualize: (paperId: string): Promise<{ mindmap: unknown }> =>
        fetchApi('/visualize', {
            method: 'POST',
            body: JSON.stringify({ paper_id: paperId }),
        }),
};
