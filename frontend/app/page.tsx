"use client";
import React, { useState, useEffect } from 'react';
import { Search, BookOpen, ExternalLink, Lightbulb, Network, Heart, Bookmark, RefreshCw, Hash, List, Code, Compass, MessageSquare, Star, Send, ArrowLeft, Loader2, Quote, Plus, ChevronLeft, ChevronRight, FolderArchive, Folders, Settings, Trash2, X } from 'lucide-react';
import InteractiveMindMap from './components/InteractiveMindMap';
import ReactMarkdown from 'react-markdown';
import DiscoverView from './components/DiscoverView';
import LibraryView from './components/LibraryView';
import ProjectView from './components/ProjectView';
import ReaderPanel from './components/ReaderPanel';
import AssistantView from './components/AssistantView';
import SettingsModal from './components/SettingsModal';

// API Base URL
const API_URL = "http://localhost:8000/api";

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
  github_url?: string;  // Optional GitHub link
  project_page?: string;  // Optional project page
  thumbnail?: string;  // Optional thumbnail image URL
  project_ids?: number[]; // IDs of projects this paper belongs to
  ingestion_status?: string;
};

type Project = {
  id: number;
  name: string;
  description: string | null;
  research_dimensions: string | null;
  created_at: string;
  paper_count: number;
};

export default function Home() {
  /* State */
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [feed, setFeed] = useState<Paper[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  // Navigation
  const [activeView, setActiveView] = useState<'explore' | 'favourites' | 'bookmarks' | 'assistant'>('explore');

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [availableTags, setAvailableTags] = useState<string[]>([]);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [sortBy, setSortBy] = useState<"date_desc" | "date_asc" | "title_asc" | "title_desc">("date_desc");


  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalPapers, setTotalPapers] = useState(0);

  const [activePaper, setActivePaper] = useState<Paper | null>(null);
  const [ideas, setIdeas] = useState<string[]>([]);
  const [mindMapData, setMindMapData] = useState<any>(null);

  const [viewMode, setViewMode] = useState<'ideas' | 'vis' | 'none'>('none');
  const [generating, setGenerating] = useState(false);

  // Scroll tracking for sticky header
  const [scrolled, setScrolled] = useState(false);

  // Ingestion status tracking for saved papers
  const [ingestionStatus, setIngestionStatus] = useState<Record<string, {
    status: string;
    chunk_count: number | null;
    title?: string;
  }>>({});
  const ingestionStatusRef = React.useRef(ingestionStatus);

  useEffect(() => {
    ingestionStatusRef.current = ingestionStatus;
  }, [ingestionStatus]);

  // Chat/Assistant state
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null);
  const [chatMessages, setChatMessages] = useState<{
    role: 'user' | 'assistant',
    content: string,
    citations?: {
      content: string,
      section: string,
      score: number,
      section_title?: string,
      page_number?: number
    }[]
  }[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [useAgentMode, setUseAgentMode] = useState(false);  // Toggle for Agentic vs Contextual RAG

  // Conversation persistence state
  const [conversations, setConversations] = useState<{
    id: number;
    paper_id: string;
    title: string;
    created_at: string;
    message_count: number;
  }[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null);

  // Quick Study Panel state
  const [studyPanelPaper, setStudyPanelPaper] = useState<Paper | null>(null);
  const [studyInsights, setStudyInsights] = useState<string>("");
  const [isLoadingInsights, setIsLoadingInsights] = useState(false);
  const [activeProjectMenu, setActiveProjectMenu] = useState<string | null>(null); // paper.id

  const fetchQuickInsights = async (paperId: string) => {
    setIsLoadingInsights(true);
    setStudyInsights("");
    try {
      const res = await fetch(`${API_URL}/insights/${paperId}`);
      if (res.ok) {
        const data = await res.json();
        setStudyInsights(data.insights);
      }
    } catch (e) {
      console.error("Failed to fetch insights", e);
    } finally {
      setIsLoadingInsights(false);
    }
  };

  // Projects state
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [projectView, setProjectView] = useState<'papers' | 'synthesis'>('papers');
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [newProjectDimensions, setNewProjectDimensions] = useState("");

  const fetchProjects = async () => {
    try {
      const res = await fetch(`${API_URL}/projects`);
      if (res.ok) {
        const data = await res.json();
        setProjects(data);
      }
    } catch (e) {
      console.error("Failed to fetch projects", e);
    }
  };

  const createProject = async () => {
    if (!newProjectName.trim()) return;
    try {
      const res = await fetch(`${API_URL}/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newProjectName,
          research_dimensions: newProjectDimensions
        })
      });
      if (res.ok) {
        setNewProjectName("");
        setNewProjectDimensions("");
        setIsCreatingProject(false);
        fetchProjects();
      }
    } catch (e) {
      console.error("Failed to create project", e);
    }
  };

  const deleteProject = async (projectId: number) => {
    try {
      const res = await fetch(`${API_URL}/projects/${projectId}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        fetchProjects();
        // If we were viewing this project, close it
        if (selectedProject?.id === projectId) {
          setSelectedProject(null);
        }
      }
    } catch (e) {
      console.error("Failed to delete project", e);
    }
  };

  const addPaperToProject = async (projectId: number, paperId: string, paperTitle?: string) => {
    // Check if paper is already in project (if we have feed data)
    const paper = feed.find(p => p.id === paperId) || activePaper;
    const isAlreadyInProject = paper?.project_ids?.includes(projectId);

    try {
      if (isAlreadyInProject) {
        // Remove from project
        const res = await fetch(`${API_URL}/projects/${projectId}/paper/${paperId}`, {
          method: 'DELETE',
        });
        if (res.ok) {
          // Optimistically update feed
          setFeed(prev => prev.map(p => p.id === paperId ? {
            ...p,
            project_ids: p.project_ids?.filter(id => id !== projectId)
          } : p));
          // If current view is project view, refreshing might remove it from view
          if (activeView === 'bookmarks' && selectedProject?.id === projectId) {
            fetchProjectPapers(projectId);
          }
          fetchProjects();
        }
      } else {
        // Add to project
        const res = await fetch(`${API_URL}/projects/${projectId}/add-paper`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            paper_id: paperId,
            title: paperTitle || paper?.title
          })
        });
        if (res.ok) {
          fetchProjects(); // Update counts

          // Optimistically update
          setFeed(prev => prev.map(p => p.id === paperId ? {
            ...p,
            project_ids: [...(p.project_ids || []), projectId]
          } : p));

          // Trigger immediate polling only if not already completed/ingested
          // We don't know for sure here without response data, but assuming backend logic handles it.
          // We just set monitor for visibility.
          const title = paperTitle || feed.find(p => p.id === paperId)?.title;

          // Only show monitor if we think it needs ingestion (backend decides, but we can't see backend decision easily without parsing response message)
          // But user requirement 2 says "ingestion should not happen again".
          // Monitor should probably only show if receiving specific "triggered" signal or we check status.
          // For now, we'll poll status from backend to be sure.

          const statusRes = await fetch(`${API_URL}/ingestion-status/${paperId}`);
          if (statusRes.ok) {
            const statusData = await statusRes.json();
            if (statusData.ingestion_status !== 'completed') {
              setIngestionStatus(prev => ({
                ...prev,
                [paperId]: { status: statusData.ingestion_status || 'pending', chunk_count: 0, title }
              }));
            }
          }
        }
      }
    } catch (e) {
      console.error("Failed to update project paper", e);
    }
  };

  const fetchProjectPapers = async (projectId: number) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/projects/${projectId}`);
      if (res.ok) {
        const data = await res.json();
        setFeed(data.papers);
      }
    } catch (e) {
      console.error("Failed to fetch project papers", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 100);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    fetchProjects();
  }, []);

  useEffect(() => {
    if (activeView === 'bookmarks') {
      if (selectedProject) {
        fetchProjectPapers(selectedProject.id);
      } else {
        fetchBookmarks();
      }
    } else if (activeView === 'favourites') {
      fetchFavorites();
    } else if (activeView === 'explore') {
      fetchFeed();
    }
  }, [currentPage, activeView, selectedProject]);

  // Custom polling effect for projects
  useEffect(() => {
    if (activeView === 'bookmarks' && !selectedProject) {
      const interval = setInterval(fetchProjects, 10000);
      return () => clearInterval(interval);
    }
  }, [activeView, selectedProject]);

  // Sync ingestion status from feed
  useEffect(() => {
    setIngestionStatus(prev => {
      const next = { ...prev };
      let changed = false;
      feed.forEach(p => {
        const status = p.ingestion_status;
        if (status && ['pending', 'processing', 'downloading', 'indexing'].includes(status)) {
          if (!next[p.id] || next[p.id].status !== status) {
            next[p.id] = { status, chunk_count: null, title: p.title };
            changed = true;
          }
        }
      });
      return changed ? next : prev;
    });
  }, [feed]);

  // Poll ingestion status for papers that are being processed
  useEffect(() => {
    const pollStatus = async () => {
      const currentStatus = ingestionStatusRef.current;
      const activeIngestions = Object.entries(currentStatus)
        .filter(([_, info]) => ['pending', 'downloading', 'parsing', 'indexing', 'processing'].includes(info.status))
        .map(([id]) => id);

      // Determine which papers to poll
      const papersToPoll = activeIngestions;

      if (papersToPoll.length === 0) return;

      for (const paperId of papersToPoll) {
        try {
          const res = await fetch(`${API_URL}/ingestion-status/${paperId}?t=${Date.now()}`);
          if (res.ok) {
            const data = await res.json();
            setIngestionStatus(prev => {
              // Only update if status or count changed
              if (prev[paperId]?.status === data.ingestion_status && prev[paperId]?.chunk_count === data.chunk_count) {
                return prev;
              }
              return {
                ...prev,
                [paperId]: {
                  ...prev[paperId],
                  status: data.ingestion_status || 'unknown',
                  chunk_count: data.chunk_count,
                  // Preserve title if we have it
                  title: prev[paperId]?.title || feed.find(p => p.id === paperId)?.title
                }
              };
            });
          }
        } catch (e) {
          console.error('Failed to poll status', e);
        }
      }
    };

    const interval = setInterval(pollStatus, 3000);
    return () => clearInterval(interval);
  }, [activeView, feed]); // Stable dependencies

  // Handle clicking outside to close project menu
  useEffect(() => {
    if (!activeProjectMenu) return;

    const handleGlobalClick = () => {
      setActiveProjectMenu(null);
    };

    // Delay adding listener to prevent immediate closure on toggle click
    const timeout = setTimeout(() => {
      window.addEventListener('click', handleGlobalClick);
    }, 10);

    return () => {
      clearTimeout(timeout);
      window.removeEventListener('click', handleGlobalClick);
    };
  }, [activeProjectMenu]);

  // Fetch conversations for a paper or project
  const fetchConversations = async (paperId?: string, projectId?: number) => {
    try {
      const params = new URLSearchParams();
      if (paperId) params.append('paper_id', paperId);
      if (projectId) params.append('project_id', projectId.toString());

      const res = await fetch(`${API_URL}/conversations?${params.toString()}`);
      if (res.ok) {
        const data = await res.json();
        setConversations(data);
      }
    } catch (e) {
      console.error('Failed to fetch conversations:', e);
    }
  };

  // Load messages for a conversation
  const loadConversation = async (convId: number) => {
    try {
      const res = await fetch(`${API_URL}/conversations/${convId}/messages`);
      if (res.ok) {
        const messages = await res.json();
        setChatMessages(messages.map((m: any) => ({
          role: m.role,
          content: m.content,
          citations: m.citations
        })));
        setActiveConversationId(convId);
      }
    } catch (e) {
      console.error('Failed to load conversation:', e);
    }
  };

  // Create new chat
  const startNewChat = () => {
    setChatMessages([]);
    setActiveConversationId(null);
  };

  // Auto-reload conversation when returning to synthesis view
  useEffect(() => {
    if (activeView === 'bookmarks' && selectedProject && projectView === 'synthesis') {
      // If we have an active conversation but no messages, reload them
      if (activeConversationId && chatMessages.length === 0 && !chatLoading) {
        loadConversation(activeConversationId);
      }
    }
  }, [activeView, selectedProject, projectView, activeConversationId, chatMessages.length, chatLoading]);

  // Send chat message
  const sendChatMessage = async () => {
    // Context identification
    const isProjectSynthesis = activeView === 'bookmarks' && selectedProject && projectView === 'synthesis';
    const paperContext = selectedPaper;
    const projectContext = selectedProject;

    if (!chatInput.trim() || chatLoading) return;
    if (!paperContext && !isProjectSynthesis) return;

    const userMessage = chatInput.trim();
    setChatInput('');
    setChatMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setChatLoading(true);

    // Placeholder for assistant message
    setChatMessages(prev => [...prev, {
      role: 'assistant',
      content: '',
      citations: []
    }]);

    try {
      const payload: any = {
        message: userMessage,
        conversation_id: activeConversationId,
        history: chatMessages.slice(-10), // Keep history lean
        use_agent: useAgentMode
      };

      if (isProjectSynthesis && projectContext) {
        payload.project_id = projectContext.id;
      } else if (paperContext) {
        payload.paper_id = paperContext.id;
      }

      const endpoint = isProjectSynthesis ? '/project-chat' : '/chat';
      const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok || !response.body) throw new Error('Chat failed');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let isFirstChunk = true;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value, { stream: true });
        buffer += text;

        if (isFirstChunk && buffer.includes('\n')) {
          const splitIndex = buffer.indexOf('\n');
          const metaLine = buffer.slice(0, splitIndex);
          const remaining = buffer.slice(splitIndex + 1);

          try {
            const data = JSON.parse(metaLine);
            if (data.conversation_id && !activeConversationId) {
              setActiveConversationId(data.conversation_id);
              // Refresh Sidebar based on current context
              if (isProjectSynthesis && projectContext) {
                fetchConversations(undefined, projectContext.id);
              } else if (paperContext) {
                fetchConversations(paperContext.id);
              }
            }
            if (data.citations) {
              setChatMessages(prev => {
                const newArr = [...prev];
                const lastIndex = newArr.length - 1;
                if (lastIndex >= 0 && newArr[lastIndex].role === 'assistant') {
                  newArr[lastIndex] = { ...newArr[lastIndex], citations: data.citations };
                }
                return newArr;
              });
            }
          } catch (e) {
            console.error("Error parsing metadata:", e);
          }
          buffer = remaining;
          isFirstChunk = false;
        }

        if (!isFirstChunk && buffer.length > 0) {
          const contentChunk = buffer;
          buffer = '';
          setChatMessages(prev => {
            const newArr = [...prev];
            const lastIndex = newArr.length - 1;
            if (lastIndex >= 0 && newArr[lastIndex].role === 'assistant') {
              newArr[lastIndex] = { ...newArr[lastIndex], content: newArr[lastIndex].content + contentChunk };
            }
            return newArr;
          });
        }
      }
    } catch (e) {
      console.error('Chat error:', e);
      setChatMessages(prev => {
        const newArr = [...prev];
        const lastMsg = newArr[newArr.length - 1];
        if (lastMsg.role === 'assistant') {
          lastMsg.content += '\n\n[Sorry, I encountered an error. Please try again.]';
        }
        return newArr;
      });
    } finally {
      setChatLoading(false);
    }
  };

  // Start discussion with a paper
  const startDiscussion = (paper: Paper) => {
    setSelectedPaper(paper);
    setChatMessages([]);
    setChatInput('');
    setActiveView('assistant');
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1); // Reset to page 1 on new search
    fetchFeed();
  };

  const handleTagClick = (tag: string) => {
    // Check if tag is already selected
    const isSelected = selectedTags.includes(tag);
    let newTags = isSelected
      ? selectedTags.filter(t => t !== tag)
      : [...selectedTags, tag];

    // Update state
    setSelectedTags(newTags);

    // If we are in "Search Mode" (searchQuery exists) OR if we have tags (Filtering Mode), we need to fetch.
    // Logic:
    // If searchQuery exists -> It's a search Refinement.
    // If searchQuery is empty -> It's a Tag Browse.
    // In both cases, we want to fetch with the new tags.
    // However, if we deselected the last tag and no query, we should probably go back to feed?
    // Actually, fetchFeed logic below handles routing to /search if query OR tags exist.

    // We rely on useEffect to trigger the fetch if tags changed. But useEffect currently checks invalid deps.
    // Only if searchQuery is set? No, we want tag browsing too.
  };

  // Re-fetch when sort or tags change
  useEffect(() => {
    // If we have a query OR tags, we are in "Search/Browse" mode -> Trigger Fetch
    // If we have neither, we are in "Feed" mode -> Trigger Fetch (to go back to daily feed)
    // Actually, we can just always fetch when these change?
    // YES.
    setCurrentPage(1);
    fetchFeed();
  }, [sortBy, selectedTags]); // Intentionally removed searchQuery from deps to avoid auto-search on type

  const fetchFeed = async (options?: { queryOverride?: string }) => {
    setLoading(true);
    setError(false);
    try {
      // Build Query
      const params = new URLSearchParams({ limit: "50", page: currentPage.toString() });

      const effectiveQuery = options?.queryOverride ?? searchQuery;

      // Determine endpoint: use /search if query OR tags exist
      let endpoint = "/feed";
      if (effectiveQuery || selectedTags.length > 0) {
        endpoint = "/search";
        if (effectiveQuery) params.append("q", effectiveQuery);
        params.append("sort", sortBy);
        selectedTags.forEach(t => params.append("tags", t));
      }

      const res = await fetch(`${API_URL}${endpoint}?${params.toString()}`);
      if (!res.ok) throw new Error("API Error");
      const data = await res.json();

      // Handle paginated response
      setFeed(data.papers || []);
      setTotalPages(data.total_pages || 1);
      setTotalPapers(data.total || 0);

      // Update facets only if we are searching (and maybe not filtering to narrow down?)
      // Actually simple rule: Update facets from response if present.
      if (data.tags) {
        setAvailableTags(data.tags);
      }
    } catch (e) {
      console.error("Failed to fetch feed", e);
      setError(true);
    }
    setLoading(false);
  };

  const fetchBookmarks = async () => {
    setLoading(true);
    setFeed([]); // Clear existing feed to prevent showing stale "Explore" data
    setError(false);
    try {
      const res = await fetch(`${API_URL}/library/saved`);
      if (!res.ok) throw new Error("API Error");
      const data = await res.json();

      // Bookmarks endpoint returns array directly
      setFeed(data || []);
      setTotalPages(1); // No pagination for bookmarks yet
      setTotalPapers(data.length || 0);
    } catch (e) {
      console.error("Failed to fetch bookmarks", e);
      setError(true);
      setFeed([]); // Ensure empty on error
    }
    setLoading(false);
  };

  const fetchFavorites = async () => {
    setLoading(true);
    setFeed([]);
    setError(false);
    try {
      const res = await fetch(`${API_URL}/library/favorites`);
      if (!res.ok) throw new Error("API Error");
      const data = await res.json();
      setFeed(data || []);
      setTotalPages(1);
      setTotalPapers(data.length || 0);
    } catch (e) {
      console.error("Failed to fetch favorites", e);
      setError(true);
      setFeed([]);
    }
    setLoading(false);
  };



  const goToPage = (page: number) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  /* ... toggleFavorite etc ... */

  const toggleFavorite = async (paper: Paper) => {
    // Optimistic Update
    const newValue = !paper.is_favorited;
    setFeed(prev => prev.map(p => p.id === paper.id ? { ...p, is_favorited: newValue } : p));

    try {
      await fetch(`${API_URL}/favorite`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          paper_id: paper.id,
          title: paper.title,
          summary: paper.abstract,
          authors: paper.authors,
          url: paper.url,
          published_date: paper.published_date
        })
      });
    } catch (e) {
      console.error("Failed to toggle favorite", e);
      // Revert
      setFeed(prev => prev.map(p => p.id === paper.id ? { ...p, is_favorited: !newValue } : p));
    }
  };

  const toggleSaved = async (paper: Paper) => {
    // Optimistic Update
    const newValue = !paper.is_saved;
    setFeed(prev => prev.map(p => p.id === paper.id ? { ...p, is_saved: newValue } : p));

    try {
      // Format summary as notes (bullet points for sentences)
      const formatAsNotes = (text: string) => {
        if (!text) return "";
        const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 10);
        return sentences.map(s => `• ${s.trim()}`).join('\n');
      };

      await fetch(`${API_URL}/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          paper_id: paper.id,
          title: paper.title,
          summary: paper.abstract,
          notes: formatAsNotes(paper.abstract),  // Formatted bullet points
          authors: paper.authors,
          url: paper.url,
          published_date: paper.published_date,
          github_url: paper.github_url || null,
          project_page: paper.project_page || null,
          mindmap_json: null  // Will be generated on-demand
        })
      });
      if (newValue) {
        // Trigger a small toast or log that ingestion started
        console.log("Saving paper with full metadata:", paper.id);
      }
    } catch (e) {
      console.error("Failed to toggle save", e);
      setFeed(prev => prev.map(p => p.id === paper.id ? { ...p, is_saved: !newValue } : p));
    }
  };

  const generateIdeas = async (paper: Paper) => {
    setActivePaper(paper);
    setViewMode('ideas');
    setGenerating(true);
    setIdeas([]);
    try {
      const res = await fetch(`${API_URL}/generate_ideas`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paper_id: paper.id })
      });
      const data = await res.json();
      setIdeas(data.ideas || ["No ideas generated."]);
    } catch (e) {
      console.error(e);
      setIdeas(["Error generating ideas."]);
    }
    setGenerating(false);
  };

  const visualize = async (paper: Paper) => {
    setActivePaper(paper);
    setViewMode('vis');
    setGenerating(true);
    setMindMapData(null);
    try {
      const res = await fetch(`${API_URL}/visualize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paper_id: paper.id })
      });
      const data = await res.json();
      setMindMapData(data.mindmap || null);
    } catch (e) {
      console.error(e);
      setMindMapData(null);
    }
    setGenerating(false);
  };

  const closeModal = () => {
    setViewMode('none');
    setActivePaper(null);
  };

  // Helper: validate thumbnail URL before attempting to render image
  const isValidUrl = (s?: string) => {
    if (!s) return false;
    try {
      // eslint-disable-next-line no-new
      new URL(s);
      return true;
    } catch (_) {
      return false;
    }
  };

  const IngestionMonitor = () => {
    const activeTasks = Object.entries(ingestionStatus)
      .filter(([_, info]) => ['pending', 'downloading', 'parsing', 'indexing', 'processing'].includes(info.status))
      .map(([id, info]) => ({ id, ...info }));

    if (activeTasks.length === 0) return null;

    return (
      <div className="fixed bottom-6 right-6 z-[120] flex flex-col gap-3 max-w-sm">
        {(() => {
          const SHOW_LIMIT = 3;
          // If we have more than limit, show limit-1 and a summary card
          const shouldStack = activeTasks.length > SHOW_LIMIT;
          const tasksToShow = shouldStack ? activeTasks.slice(0, SHOW_LIMIT - 1) : activeTasks;
          const remaining = activeTasks.length - tasksToShow.length;

          return (
            <>
              {tasksToShow.map((task) => (
                <div key={task.id} className="bg-neutral-900/90 backdrop-blur-xl border border-white/10 rounded-2xl p-4 shadow-2xl animate-in slide-in-from-right-10 duration-500">
                  <div className="flex items-center gap-4">
                    <div className="relative">
                      <RefreshCw className="w-5 h-5 text-indigo-400 animate-spin" />
                      <div className="absolute inset-0 bg-indigo-400/20 blur-lg animate-pulse" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-bold text-white truncate mb-1">
                        {task.title || 'Unknown Paper'}
                      </p>
                      <div className="flex items-center justify-between text-[10px] uppercase tracking-widest font-bold">
                        <span className="text-indigo-400 animate-pulse">{task.status}</span>
                        {task.chunk_count ? (
                          <span className="text-gray-500">{task.chunk_count} chunks</span>
                        ) : null}
                      </div>
                    </div>
                  </div>
                  <div className="mt-3 h-1 w-full bg-white/5 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-indigo-600 to-indigo-400 transition-all duration-1000 ease-in-out"
                      style={{
                        width: task.status === 'completed' ? '100%' :
                          task.status === 'indexing' ? '85%' :
                            task.status === 'parsing' ? '60%' :
                              task.status === 'downloading' ? '30%' : '10%'
                      }}
                    />
                  </div>
                </div>
              ))}
              {shouldStack && (
                <div className="bg-neutral-900/90 backdrop-blur-xl border border-white/10 rounded-2xl p-4 shadow-2xl animate-in slide-in-from-right-10 duration-500 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="bg-indigo-500/20 p-2 rounded-full">
                      <RefreshCw className="w-4 h-4 text-indigo-400 animate-spin" />
                    </div>
                    <div>
                      <p className="text-xs font-bold text-white">
                        Processing {remaining} more papers...
                      </p>
                      <p className="text-[10px] text-gray-500">Background ingestion active</p>
                    </div>
                  </div>
                </div>
              )}
            </>
          );
        })()}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-black text-gray-100 font-sans">
      <header className="bg-black/80 backdrop-blur-md border-b border-white/10 sticky top-0 z-[100]">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <BookOpen className="text-white w-6 h-6" />
            <h1 className="text-xl font-bold text-white">
              Shodh (शोध)
            </h1>
          </div>
          <button onClick={() => fetchFeed()} className="p-2 hover:bg-neutral-800 rounded-full transition text-gray-400 hover:text-white" title="Refresh Feed">
            <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </header>

      {/* Sidebar Navigation */}
      {/* Sidebar Navigation */}
      <aside
        className={`fixed left-0 top-16 h-[calc(100vh-4rem)] bg-neutral-900 border-r border-white/10 flex flex-col transition-all duration-300 ease-in-out z-[90] ${sidebarOpen ? 'w-64' : 'w-16'
          }`}
      >
        <nav className="flex-1 space-y-2 p-2">
          <button
            onClick={() => {
              setActiveView('explore');
              setSelectedProject(null);
              setCurrentPage(1);
            }}
            title="Research Discovery"
            className={`w-full flex items-center py-3 rounded-lg transition-all ${sidebarOpen ? 'gap-3 px-3' : 'justify-center px-2'} ${activeView === 'explore'
              ? 'bg-indigo-600 text-white font-semibold shadow-lg shadow-indigo-500/20'
              : 'text-gray-400 hover:bg-neutral-800 hover:text-white'
              }`}
          >
            <Compass className="w-5 h-5 flex-shrink-0" />
            <span className={`transition-opacity duration-200 ${sidebarOpen ? 'opacity-100' : 'opacity-0 w-0 overflow-hidden'}`}>
              Research Discovery
            </span>
          </button>

          <button
            onClick={() => {
              setActiveView('favourites');
              setSelectedProject(null);
              setCurrentPage(1);
            }}
            title="Personal Collection"
            className={`w-full flex items-center py-3 rounded-lg transition-all ${sidebarOpen ? 'gap-3 px-3' : 'justify-center px-2'} ${activeView === 'favourites'
              ? 'bg-indigo-600 text-white font-semibold shadow-lg shadow-indigo-500/20'
              : 'text-gray-400 hover:bg-neutral-800 hover:text-white'
              }`}
          >
            <Heart className="w-5 h-5 flex-shrink-0" />
            <span className={`transition-opacity duration-200 ${sidebarOpen ? 'opacity-100' : 'opacity-0 w-0 overflow-hidden'}`}>
              Personal Collection
            </span>
          </button>

          <button
            onClick={() => {
              setActiveView('bookmarks');
              setSelectedProject(null);
              setCurrentPage(1);
            }}
            title="Synthesis Hub"
            className={`w-full flex items-center py-3 rounded-lg transition-all ${sidebarOpen ? 'gap-3 px-3' : 'justify-center px-2'} ${activeView === 'bookmarks' && !selectedProject
              ? 'bg-indigo-600 text-white font-semibold shadow-lg shadow-indigo-500/20'
              : 'text-gray-400 hover:bg-neutral-800 hover:text-white'
              }`}
          >
            <FolderArchive className="w-5 h-5 flex-shrink-0" />
            <span className={`transition-opacity duration-200 ${sidebarOpen ? 'opacity-100' : 'opacity-0 w-0 overflow-hidden'}`}>
              Synthesis Hub
            </span>
          </button>

          {/* Recent Projects Section */}
          {sidebarOpen && projects.length > 0 && (
            <div className="mt-4 px-3 py-2">
              <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-2 px-1">
                Recent Projects
              </p>
              <div className="space-y-1">
                {projects.slice(0, 5).map(proj => (
                  <button
                    key={proj.id}
                    onClick={() => {
                      setSelectedProject(proj);
                      setSidebarOpen(false);
                      setActiveView('bookmarks');
                    }}
                    className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-sm transition-colors ${selectedProject?.id === proj.id
                      ? 'bg-indigo-600/20 text-indigo-400 font-medium'
                      : 'text-gray-400 hover:bg-white/5 hover:text-gray-200'
                      }`}
                  >
                    <div className={`w-1.5 h-1.5 rounded-full ${selectedProject?.id === proj.id ? 'bg-indigo-500' : 'bg-neutral-600'}`} />
                    <span className="truncate">{proj.name}</span>
                  </button>
                ))}
                {projects.length > 5 && (
                  <button
                    onClick={() => {
                      setActiveView('bookmarks');
                      setSelectedProject(null);
                    }}
                    className="w-full text-left px-2 py-1 text-xs text-indigo-400 hover:text-indigo-300 transition-colors mt-1"
                  >
                    See all projects ({projects.length})
                  </button>
                )}
              </div>
            </div>
          )}
        </nav>

        {/* Sidebar Toggle */}
        <div className="p-2 border-t border-white/10 space-y-1">
          <button
            onClick={() => setIsSettingsOpen(true)}
            className={`w-full flex items-center gap-3 px-3 py-3 rounded-lg text-gray-400 hover:bg-neutral-800 hover:text-white transition-all ${!sidebarOpen ? 'justify-center' : ''}`}
            title="Settings"
          >
            <Settings className="w-5 h-5" />
            <span className={`transition-opacity duration-200 ${sidebarOpen ? 'opacity-100' : 'opacity-0 w-0 overflow-hidden'}`}>
              Settings
            </span>
          </button>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className={`w-full flex items-center gap-3 px-3 py-3 rounded-lg text-gray-400 hover:bg-neutral-800 hover:text-white transition-all ${!sidebarOpen ? 'justify-center' : ''}`}
          >
            {sidebarOpen ? <ChevronLeft className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
            <span className={`transition-opacity duration-200 ${sidebarOpen ? 'opacity-100' : 'opacity-0 w-0 overflow-hidden'}`}>
            </span>
          </button>
        </div>
      </aside>

      <main
        className={`transition-all duration-300 ease-in-out ${sidebarOpen ? 'ml-64' : 'ml-16'
          } ${activeView === 'assistant' ? 'p-0' : 'px-4 py-8'}`}
      >
        {activeView === 'explore' || activeView === 'favourites' ? (
          <DiscoverView
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
            showSearch={activeView === 'explore'}
            onSearch={handleSearch}

            loading={loading}
            error={error}
            feed={feed.filter((p) => (activeView === 'favourites' ? p.is_favorited : true))}
            onStudy={(p) => setStudyPanelPaper(p)}
            onVisualize={visualize}
            onAddPaperToProject={(projId, paperId) => {
              const p = feed.find(p => p.id === paperId);
              addPaperToProject(projId, paperId, p?.title);
            }}
            onToggleFavorite={toggleFavorite}
            projects={projects}
            activeProjectMenu={activeProjectMenu}
            setActiveProjectMenu={setActiveProjectMenu}
            ingestionStatus={ingestionStatus}
            totalPages={totalPages}
            currentPage={currentPage}
            goToPage={(p) => {
              setCurrentPage(p);
              fetchFeed();
            }}
            totalPapers={totalPapers}
            onRetry={fetchFeed}
            title={activeView === 'favourites' ? "Personal Collection" : "Research Discovery"}
            subtitle={activeView === 'favourites' ? "A curated space for your most valued research papers." : "Explore the global frontier of research publications."}

            availableTags={availableTags}
            selectedTags={selectedTags}
            setSelectedTags={setSelectedTags}
            sortBy={sortBy}
            setSortBy={setSortBy}
            onTagClick={handleTagClick}
          />
        ) : (
          <>
            {activeView === 'assistant' ? (
              <AssistantView
                selectedPaper={selectedPaper}
                conversations={conversations}
                activeConversationId={activeConversationId}
                chatMessages={chatMessages}
                chatInput={chatInput}
                chatLoading={chatLoading}
                useAgentMode={useAgentMode}
                onStartNewChat={startNewChat}
                onLoadConversation={loadConversation}
                onBackToLibrary={() => {
                  setActiveView('bookmarks');
                  setSelectedPaper(null);
                  setConversations([]);
                  setChatMessages([]);
                  setActiveConversationId(null);
                }}
                onSetChatInput={setChatInput}
                onSendChatMessage={sendChatMessage}
                onToggleAgentMode={() => setUseAgentMode(!useAgentMode)}
              />
            ) : activeView === 'bookmarks' && !selectedProject ? (
              <LibraryView
                projects={projects}
                isCreatingProject={isCreatingProject}
                setIsCreatingProject={setIsCreatingProject}
                newProjectName={newProjectName}
                setNewProjectName={setNewProjectName}
                newProjectDimensions={newProjectDimensions}
                setNewProjectDimensions={setNewProjectDimensions}
                onCreateProject={createProject}
                onSelectProject={(p) => {
                  setSelectedProject(p);
                  if (p) setSidebarOpen(false);
                }}
                onDeleteProject={deleteProject}
                onFetchBookmarks={fetchBookmarks}
              />
            ) : (
              <ProjectView
                project={selectedProject!}
                onClose={() => setSelectedProject(null)}
                projectView={projectView}
                setProjectView={setProjectView}
                feed={feed}
                onStudy={(p) => {
                  setStudyPanelPaper(p);
                  fetchQuickInsights(p.id);
                }}
                onVisualize={visualize}
                onFetchConversations={fetchConversations}
                conversations={conversations}
                activeConversationId={activeConversationId}
                onLoadConversation={loadConversation}
                chatMessages={chatMessages}
                chatInput={chatInput}
                setChatInput={setChatInput}
                onSendChatMessage={sendChatMessage}
                chatLoading={chatLoading}
                onStartNewChat={startNewChat}
                activeProjectMenu={activeProjectMenu}
                setActiveProjectMenu={setActiveProjectMenu}
                ingestionStatus={ingestionStatus}
                onAddPaperToProject={addPaperToProject}
                useAgentMode={useAgentMode}
                onToggleAgentMode={() => setUseAgentMode(!useAgentMode)}
              />
            )}
          </>
        )}

        {/* Modal Overlay */}
        {
          viewMode !== 'none' && activePaper && (
            <div className="fixed inset-0 bg-black/90 backdrop-blur-md z-50 flex items-center justify-center p-4">
              <div className="bg-neutral-900 border border-white/10 rounded-2xl shadow-2xl w-full max-w-5xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in duration-200">
                {/* Modal Header */}
                <div className="p-6 border-b border-white/10 flex justify-between items-center bg-black/40">
                  <div className="flex-1 pr-4">
                    <h3 className="text-xl font-bold text-white truncate">{activePaper.title}</h3>
                    <p className="text-sm text-gray-500 mt-1">
                      {viewMode === 'ideas' ? 'Research Hypotheses & New Directions' : 'Interactive Knowledge Graph'}
                    </p>
                  </div>
                  <button onClick={closeModal} className="text-gray-400 hover:text-white transition">
                    ✕
                  </button>
                </div>

                {/* Modal Body */}
                <div className="p-0 overflow-hidden flex-1 relative min-h-[500px]">
                  {generating ? (
                    <div className="h-full w-full flex flex-col items-center justify-center bg-zinc-900 z-10 min-h-[500px]">
                      <div className="w-16 h-16 border-4 border-white border-t-transparent rounded-full animate-spin mb-6"></div>
                      <p className="text-white font-medium text-lg animate-pulse">
                        {viewMode === 'vis' ? 'Building mindmap...' : 'Forging research ideas...'}
                      </p>
                    </div>
                  ) : (
                    <div className="h-full overflow-y-auto p-8 custom-scrollbar">
                      {viewMode === 'ideas' && (
                        <div className="space-y-6">
                          <h4 className="text-lg font-semibold text-white flex items-center mb-6">
                            Hypotheses & Future Directions
                          </h4>
                          <div className="grid gap-6">
                            {ideas.map((idea, idx) => (
                              <div key={idx} className="bg-black p-6 rounded-xl border border-white/10 relative">
                                <div className="absolute top-0 left-0 w-1 h-full bg-white rounded-l-xl"></div>
                                <p className="text-gray-300 leading-relaxed pl-2">{idea}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {viewMode === 'vis' && (
                        <div className="h-full flex flex-col min-h-[500px]">
                          {mindMapData ? (
                            <InteractiveMindMap data={mindMapData} />
                          ) : (
                            <div className="flex flex-col items-center justify-center h-full text-red-400">
                              <p>Failed to load visualization.</p>
                              <p className="text-xs text-gray-500 mt-2">Try re-generating or check backend logs.</p>
                              <p className="text-xs text-gray-600 mt-2">Note: To visualize properly, ensure the paper is Saved.</p>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )
        }
        {/* Reader Mode Side Drawer */}
        <ReaderPanel
          paper={studyPanelPaper}
          onClose={() => setStudyPanelPaper(null)}
          insights={studyInsights}
          isLoading={isLoadingInsights}
          ingestionStatus={ingestionStatus}
          onOpenAssistant={(p) => {
            setSelectedPaper(p);
            setActiveView('assistant');
            setStudyPanelPaper(null);
          }}
          isProjectView={!!selectedProject}
          projects={projects}
          activeProjectMenu={activeProjectMenu}
          setActiveProjectMenu={setActiveProjectMenu}
          onAddPaperToProject={addPaperToProject}
          onCreateProject={() => {
            setActiveView('bookmarks');
            setIsCreatingProject(true);
          }}
        />
      </main>
      <IngestionMonitor />
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />
    </div>
  );
}
