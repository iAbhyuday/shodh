// Shared TypeScript types for the Shodh frontend

export type Paper = {
    id: string;
    title: string;
    abstract: string;
    source?: string;
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
    project_ids?: string[];
    ingestion_status?: string;
};

export type Project = {
    id: string;
    name: string;
    description: string | null;
    research_dimensions: string | null;
    created_at: string;
    paper_count: number;
};

export type Citation = {
    content: string;
    section: string;
    score: number;
    section_title?: string;
    page_number?: number;
    summary?: string;
};

export type ChatMessage = {
    role: 'user' | 'assistant';
    content: string;
    citations?: Citation[];
};

export type Conversation = {
    id: string;
    paper_id?: string;
    project_id?: string;
    title: string;
    created_at: string;
    message_count: number;
};

export type IngestionStatus = {
    status: string;
    chunk_count: number | null;
    title?: string;
    progress?: number;
    step?: string;
    error?: string;
};

export type SortOption = "date_desc" | "date_asc" | "title_asc" | "title_desc";

export type ViewType = 'explore' | 'favourites' | 'bookmarks' | 'assistant';

export type ProjectView = 'papers' | 'synthesis';

// API Response types
export type PaginatedPapersResponse = {
    papers: Paper[];
    total_pages: number;
    total: number;
    tags?: string[];
};

// MindMap types
export type MindMapNode = {
    id: string;
    label: string;
    children?: MindMapNode[];
};

