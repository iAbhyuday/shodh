"use client";
import React, { useState, useEffect } from 'react';
import { Search, BookOpen, ExternalLink, Lightbulb, Network, Heart, Bookmark, RefreshCw, Hash, List, Code, Compass, MessageSquare, Star, Send, ArrowLeft, Loader2, Quote, Plus } from 'lucide-react';
import InteractiveMindMap from './components/InteractiveMindMap';
import ReactMarkdown from 'react-markdown';

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
};

export default function Home() {
  /* State */
  const [feed, setFeed] = useState<Paper[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  // Navigation
  const [activeView, setActiveView] = useState<'explore' | 'favourites' | 'bookmarks' | 'assistant'>('explore');

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [date, setDate] = useState(""); // YYYY-MM-DD

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
  }>>({});

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

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 100);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    fetchFeed();
  }, [date, currentPage]); // Refetch when date or page changes

  // Poll ingestion status for saved papers
  useEffect(() => {
    if (activeView !== 'bookmarks') return;

    const savedPapers = feed.filter(p => p.is_saved);
    if (savedPapers.length === 0) return;

    const pollStatus = async () => {
      for (const paper of savedPapers) {
        try {
          const res = await fetch(`${API_URL}/ingestion-status/${paper.id}`);
          if (res.ok) {
            const data = await res.json();
            setIngestionStatus(prev => ({
              ...prev,
              [paper.id]: { status: data.ingestion_status || 'unknown', chunk_count: data.chunk_count }
            }));
          }
        } catch (e) {
          console.error('Failed to poll status', e);
        }
      }
    };

    pollStatus();
    const interval = setInterval(pollStatus, 3000); // Poll every 3 seconds
    return () => clearInterval(interval);
  }, [activeView, feed]);

  // Fetch conversations for a paper
  const fetchConversations = async (paperId: string) => {
    try {
      const res = await fetch(`${API_URL}/conversations/${paperId}`);
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

  // Fetch conversations when paper is selected
  useEffect(() => {
    if (selectedPaper) {
      fetchConversations(selectedPaper.id);
    }
  }, [selectedPaper]);

  // Send chat message
  const sendChatMessage = async () => {
    if (!chatInput.trim() || !selectedPaper || chatLoading) return;

    const userMessage = chatInput.trim();
    setChatInput('');
    setChatMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setChatLoading(true);

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          paper_id: selectedPaper.id,
          message: userMessage,
          conversation_id: activeConversationId,
          history: chatMessages,
          use_agent: useAgentMode
        })
      });

      if (!res.ok) throw new Error('Chat failed');
      const data = await res.json();

      // Update conversation ID if new conversation was created
      if (data.conversation_id && !activeConversationId) {
        setActiveConversationId(data.conversation_id);
        fetchConversations(selectedPaper.id);  // Refresh sidebar
      }

      setChatMessages(prev => [...prev, {
        role: 'assistant',
        content: data.response,
        citations: data.citations
      }]);
    } catch (e) {
      console.error('Chat error:', e);
      setChatMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' }]);
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

  const fetchFeed = async () => {
    setLoading(true);
    setError(false);
    try {
      // Build Query
      const params = new URLSearchParams({ limit: "20", page: currentPage.toString() });
      if (date) params.append("date", date);
      if (searchQuery) params.append("q", searchQuery);

      const res = await fetch(`${API_URL}/feed?${params.toString()}`);
      if (!res.ok) throw new Error("API Error");
      const data = await res.json();

      // Handle paginated response
      setFeed(data.papers || []);
      setTotalPages(data.total_pages || 1);
      setTotalPapers(data.total || 0);
    } catch (e) {
      console.error("Failed to fetch feed", e);
      setError(true);
    }
    setLoading(false);
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1); // Reset to page 1 on new search
    fetchFeed();
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

  return (
    <div className="min-h-screen bg-black text-gray-100 font-sans">
      <header className="bg-black/80 backdrop-blur-md border-b border-white/10 sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <BookOpen className="text-white w-6 h-6" />
            <h1 className="text-xl font-bold text-white">
              Shodh (शोध)
            </h1>
          </div>
          <button onClick={fetchFeed} className="p-2 hover:bg-neutral-800 rounded-full transition text-gray-400 hover:text-white" title="Refresh Feed">
            <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </header>

      {/* Sidebar Navigation */}
      <aside className="fixed left-0 top-16 h-screen w-64 bg-neutral-900 border-r border-white/10 p-4 z-10">
        <nav className="space-y-2">
          <button
            onClick={() => {
              setActiveView('explore');
              setCurrentPage(1);
            }}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${activeView === 'explore'
              ? 'bg-white text-black font-semibold'
              : 'text-gray-400 hover:bg-neutral-800 hover:text-white'
              }`}
          >
            <Compass className="w-5 h-5" />
            <span>Explore</span>
          </button>

          <button
            onClick={() => {
              setActiveView('favourites');
              setCurrentPage(1);
            }}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${activeView === 'favourites'
              ? 'bg-white text-black font-semibold'
              : 'text-gray-400 hover:bg-neutral-800 hover:text-white'
              }`}
          >
            <Star className="w-5 h-5" />
            <span>Favourites</span>
          </button>

          <button
            onClick={() => {
              setActiveView('bookmarks');
              setCurrentPage(1);
            }}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${activeView === 'bookmarks'
              ? 'bg-white text-black font-semibold'
              : 'text-gray-400 hover:bg-neutral-800 hover:text-white'
              }`}
          >
            <Bookmark className="w-5 h-5" />
            <span>Bookmarks</span>
          </button>

          <button
            onClick={() => setActiveView('assistant')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${activeView === 'assistant'
              ? 'bg-white text-black font-semibold'
              : 'text-gray-400 hover:bg-neutral-800 hover:text-white'
              }`}
          >
            <MessageSquare className="w-5 h-5" />
            <span>Assistant</span>
          </button>
        </nav>
      </aside>

      <main className="ml-64 px-4 py-8">
        {/* Filters - Only on Explore */}
        {activeView === 'explore' && (
          <section className="mb-8 text-center sticky top-16 z-10 bg-black/50 backdrop-blur-xl p-4 rounded-2xl border border-white/5 shadow-2xl transition-all duration-300">
            <form onSubmit={handleSearch} className="max-w-xl mx-auto flex flex-col sm:flex-row gap-3">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input
                  type="text"
                  placeholder="Search keywords..."
                  className="w-full bg-neutral-900 border border-white/10 rounded-lg py-2.5 pl-10 pr-4 text-sm text-white focus:ring-2 focus:ring-white/20 outline-none transition"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
              <div className="relative">
                <input
                  type="date"
                  className="bg-neutral-900 border border-white/10 rounded-lg py-2.5 px-4 text-sm text-gray-300 focus:ring-2 focus:ring-white/20 outline-none transition cursor-pointer"
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                  max={new Date().toISOString().split('T')[0]} // Max today
                />
              </div>
              <button type="submit" className="bg-white text-black font-semibold py-2.5 px-6 rounded-lg hover:bg-gray-200 transition text-sm">
                Filter
              </button>
            </form>
          </section>
        )}

        {/* Feed Section */}
        <section>


          {loading && feed.length === 0 ? (
            <div className="max-w-2xl mx-auto flex flex-col gap-8">
              {/* Skeleton Loading Cards */}
              {[1, 2, 3].map((i) => (
                <div key={i} className="bg-neutral-900 rounded-2xl border border-white/5 p-8 animate-pulse">
                  <div className="flex justify-between items-start mb-4">
                    <div className="flex-1 space-y-3">
                      <div className="h-6 bg-neutral-800 rounded w-3/4"></div>
                      <div className="h-4 bg-neutral-800 rounded w-1/2"></div>
                    </div>
                    <div className="h-6 w-20 bg-neutral-800 rounded ml-4"></div>
                  </div>
                  <div className="space-y-2 mb-4">
                    <div className="h-3 bg-neutral-800 rounded w-full"></div>
                    <div className="h-3 bg-neutral-800 rounded w-full"></div>
                    <div className="h-3 bg-neutral-800 rounded w-4/5"></div>
                  </div>
                  <div className="flex gap-2 mb-4">
                    <div className="h-6 w-16 bg-neutral-800 rounded"></div>
                    <div className="h-6 w-16 bg-neutral-800 rounded"></div>
                    <div className="h-6 w-16 bg-neutral-800 rounded"></div>
                  </div>
                  <div className="flex gap-2">
                    <div className="h-10 w-10 bg-neutral-800 rounded-full"></div>
                    <div className="h-10 w-10 bg-neutral-800 rounded-full"></div>
                    <div className="h-10 w-10 bg-neutral-800 rounded-full"></div>
                  </div>
                </div>
              ))}
            </div>
          ) : error ? (
            <div className="text-center py-20 text-red-400 bg-red-900/10 rounded-xl border border-red-900/20">
              <p className="text-lg font-semibold">Unable to connect to Shodh Server.</p>
              <p className="text-sm mt-2 text-gray-500">Please ensure the backend is running.</p>
              <button onClick={fetchFeed} className="mt-6 px-6 py-2 bg-neutral-800 text-white rounded-full hover:bg-neutral-700 transition border border-white/10">
                Retry Connection
              </button>
            </div>
          ) : (
            <>
              {/* Assistant View - Paper Q&A */}
              {activeView === 'assistant' ? (
                <div className="flex gap-4 h-[calc(100vh-12rem)]">
                  {/* Conversation Sidebar */}
                  {selectedPaper && (
                    <div className="w-64 flex-shrink-0 flex flex-col bg-neutral-900 rounded-xl border border-white/10 p-4">
                      <button
                        onClick={startNewChat}
                        className="w-full flex items-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-500 transition mb-4"
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
                              onClick={() => loadConversation(conv.id)}
                              className={`w-full text-left p-3 rounded-lg transition ${activeConversationId === conv.id
                                ? 'bg-white/10 border border-white/20'
                                : 'hover:bg-white/5 border border-transparent'
                                }`}
                            >
                              <div className="text-sm font-medium text-white line-clamp-2">
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
                  <div className="flex-1 flex flex-col">
                    {selectedPaper ? (
                      <>
                        {/* Paper Header */}
                        <div className="flex items-center gap-4 mb-4 p-4 bg-neutral-900 rounded-xl border border-white/10">
                          <button
                            onClick={() => {
                              setActiveView('bookmarks');
                              setSelectedPaper(null);
                              setConversations([]);
                              setChatMessages([]);
                              setActiveConversationId(null);
                            }}
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
                        <div className="flex-1 overflow-y-auto space-y-4 mb-4 p-4">
                          {chatMessages.length === 0 && (
                            <div className="text-center text-gray-500 py-10">
                              <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-50" />
                              <p>Ask a question about this paper</p>
                            </div>
                          )}
                          {chatMessages.map((msg, idx) => (
                            <div
                              key={idx}
                              className="flex gap-4 p-6 border-b border-white/5 hover:bg-white/5 transition-colors"
                            >
                              <div className="flex-shrink-0 mt-1">
                                {msg.role === 'user' ? (
                                  <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
                                    <span className="text-xs font-bold text-white">U</span>
                                  </div>
                                ) : (
                                  <div className="w-8 h-8 rounded-full bg-orange-600 flex items-center justify-center">
                                    <span className="text-xs font-bold text-white">AI</span>
                                  </div>
                                )}
                              </div>

                              <div className="flex-1 min-w-0">
                                <div className="mb-1">
                                  <span className="font-semibold text-sm text-gray-200">
                                    {msg.role === 'user' ? 'You' : 'Shodh Assistant'}
                                  </span>
                                </div>

                                {msg.role === 'user' ? (
                                  <p className="text-gray-300 whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                                ) : (
                                  <div className="prose prose-invert prose-p:leading-relaxed prose-pre:bg-black/50 prose-pre:border prose-pre:border-white/10 max-w-none text-gray-300">
                                    <ReactMarkdown>{msg.content}</ReactMarkdown>

                                    {/* Citations */}
                                    {msg.citations && msg.citations.length > 0 && (
                                      <div className="mt-6 pt-4 border-t border-white/10">
                                        <p className="text-xs font-medium text-gray-400 mb-2 flex items-center gap-2">
                                          <Quote className="w-3 h-3" />
                                          References
                                        </p>
                                        <div className="flex gap-2 overflow-x-auto pb-2">
                                          {msg.citations.slice(0, 3).map((cit, i) => (
                                            <div key={i} className="min-w-[220px] max-w-[220px] p-3 bg-black/20 rounded border border-white/5 text-xs flex flex-col gap-1">
                                              <div className="flex justify-between items-start">
                                                <span className="font-medium text-blue-400 line-clamp-1 uppercase text-[10px] tracking-wider">
                                                  {cit.section}
                                                </span>
                                                {cit.page_number && (
                                                  <span className="text-gray-500 text-[10px]">
                                                    Page {cit.page_number}
                                                  </span>
                                                )}
                                              </div>

                                              {cit.section_title && (
                                                <div className="font-semibold text-gray-300 line-clamp-1">
                                                  {cit.section_title}
                                                </div>
                                              )}

                                              <div className="text-gray-500 line-clamp-3 italic mt-1 bg-white/5 p-1 rounded">
                                                "{cit.content}"
                                              </div>
                                            </div>
                                          ))}
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                )}
                              </div>
                            </div>
                          ))}
                          {chatLoading && (
                            <div className="flex justify-start">
                              <div className="bg-neutral-800 p-4 rounded-2xl">
                                <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
                              </div>
                            </div>
                          )}
                        </div>

                        {/* Chat Input */}
                        <div className="flex flex-col gap-2 p-4 bg-neutral-900 rounded-xl border border-white/10">
                          {/* Agent Mode Toggle */}
                          <div className="flex items-center gap-2 text-xs text-gray-400">
                            <button
                              onClick={() => setUseAgentMode(!useAgentMode)}
                              className={`px-3 py-1.5 rounded-full border transition-all ${useAgentMode
                                ? 'bg-orange-600/20 border-orange-500 text-orange-400'
                                : 'bg-neutral-800 border-white/10 text-gray-500'
                                }`}
                            >
                              {useAgentMode ? '🤖 Agent Mode' : '⚡ Fast Mode'}
                            </button>
                            <span>{useAgentMode ? 'Multi-step reasoning (slower)' : 'Quick contextual answers'}</span>
                          </div>

                          <div className="flex gap-3">
                            <input
                              type="text"
                              value={chatInput}
                              onChange={(e) => setChatInput(e.target.value)}
                              onKeyDown={(e) => e.key === 'Enter' && sendChatMessage()}
                              placeholder="Ask about this paper..."
                              className="flex-1 bg-neutral-800 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                            <button
                              onClick={sendChatMessage}
                              disabled={chatLoading || !chatInput.trim()}
                              className="px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition"
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
                          onClick={() => setActiveView('bookmarks')}
                          className="px-6 py-3 bg-white text-black font-semibold rounded-lg hover:bg-gray-200 transition"
                        >
                          Go to Bookmarks
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="max-w-2xl mx-auto flex flex-col gap-8">
                  {/* Filter feed based on active view */}
                  {feed
                    .filter(paper => {
                      if (activeView === 'favourites') return paper.is_favorited;
                      if (activeView === 'bookmarks') return paper.is_saved;
                      return true; // 'explore' shows all
                    })
                    .map((paper) => {
                      const metrics = paper.metrics || {};
                      const tags = Array.isArray(metrics.tags) ? metrics.tags : [];
                      // Core idea is nice, but we'll focus on the summary/abstract as "Content"
                      const content = paper.abstract;

                      // Content Formatter: "Notes Style" -> Split sentences and bullet them
                      const NoteContent = ({ text }: { text: string }) => {
                        const [expanded, setExpanded] = useState(false);
                        // Split by sentences roughly
                        const sentences = text.match(/[^.!?]+[.!?]+/g) || [text];
                        const visibleSentences = expanded ? sentences : sentences.slice(0, 3);

                        return (
                          <div className="text-gray-300 text-base leading-relaxed space-y-2">
                            <ul className="list-disc pl-4 space-y-1 marker:text-gray-600">
                              {visibleSentences.map((s, i) => (
                                <li key={i}>{s.trim()}</li>
                              ))}
                            </ul>
                            {sentences.length > 3 && (
                              <button
                                onClick={() => setExpanded(!expanded)}
                                className="text-sm text-blue-400 hover:text-blue-300 mt-2 font-medium"
                              >
                                {expanded ? "See Less" : "See More"}
                              </button>
                            )}
                          </div>
                        );
                      };

                      return (
                        <div key={paper.id} className="bg-neutral-900 rounded-2xl border border-white/5 hover:border-white/20 transition-all duration-300 overflow-hidden shadow-lg group">
                          {/* Thumbnail */}
                          {paper.thumbnail && isValidUrl(paper.thumbnail) ? (
                            <div className="relative w-full h-48 bg-neutral-800 overflow-hidden">
                              <img
                                src={paper.thumbnail}
                                alt={paper.title}
                                className="w-full h-full object-cover object-top group-hover:scale-105 transition-transform duration-300"
                              />
                              {/* Date Badge */}
                              <span className="absolute top-2 right-2 text-xs font-mono text-white bg-black/60 backdrop-blur-sm border border-white/20 px-2 py-1 rounded">
                                {new Date(paper.published_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
                              </span>
                            </div>
                          ) : null}

                          <div className="p-6">
                            {/* Header: Title + Date shown when no valid thumbnail */}
                            {(!paper.thumbnail || !isValidUrl(paper.thumbnail)) && (
                              <div className="mb-4">
                                <div className="flex justify-between items-start">
                                  <h3 className="text-xl font-bold text-white leading-tight group-hover:text-blue-400 transition-colors">
                                    <a href={paper.url} target="_blank" rel="noreferrer">{paper.title}</a>
                                  </h3>
                                  {/* Date Badge */}
                                  <span className="flex-shrink-0 ml-3 text-xs font-mono text-gray-500 border border-white/10 px-2 py-1 rounded">
                                    {new Date(paper.published_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
                                  </span>
                                </div>
                                <p className="text-sm text-gray-500 mt-1">{paper.authors}</p>
                              </div>
                            )}

                            {/* Content: Notes Format */}
                            <div className="mb-6">
                              <NoteContent text={content} />
                            </div>

                            {/* Hashtags (Bottom) */}
                            {tags.length > 0 && (
                              <div className="flex flex-wrap gap-2 mb-4 pt-4 border-t border-white/5">
                                {tags.slice(0, 5).map((tag: string, idx: number) => (
                                  <span key={idx} className="text-xs text-blue-400 hover:text-blue-300 cursor-pointer">
                                    #{tag.replace(/\s+/g, '')}
                                  </span>
                                ))}
                              </div>
                            )}

                            {/* Ingestion Status - Only on Bookmarks */}
                            {activeView === 'bookmarks' && paper.is_saved && (
                              <div className="mb-4 p-3 bg-neutral-800/50 rounded-lg border border-white/5">
                                {(() => {
                                  const status = ingestionStatus[paper.id];
                                  if (!status || status.status === 'pending') {
                                    return (
                                      <div className="flex items-center gap-2 text-yellow-500">
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        <span className="text-sm">Queued for indexing...</span>
                                      </div>
                                    );
                                  } else if (status.status === 'downloading') {
                                    return (
                                      <div className="flex items-center gap-2 text-blue-400">
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        <span className="text-sm">Downloading PDF...</span>
                                      </div>
                                    );
                                  } else if (status.status === 'parsing') {
                                    return (
                                      <div className="flex items-center gap-2 text-purple-400">
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        <span className="text-sm">Parsing document...</span>
                                      </div>
                                    );
                                  } else if (status.status === 'indexing') {
                                    return (
                                      <div className="flex items-center gap-2 text-cyan-400">
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        <span className="text-sm">Indexing {status.chunk_count || ''} chunks...</span>
                                      </div>
                                    );
                                  } else if (status.status === 'completed') {
                                    return (
                                      <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-2 text-green-400">
                                          <span className="text-sm">✓ Ready ({status.chunk_count} chunks)</span>
                                        </div>
                                        <button
                                          onClick={() => startDiscussion(paper)}
                                          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-500 transition"
                                        >
                                          <MessageSquare className="w-4 h-4" />
                                          Discuss
                                        </button>
                                      </div>
                                    );
                                  } else if (status.status === 'failed') {
                                    return (
                                      <div className="flex items-center gap-2 text-red-400">
                                        <span className="text-sm">❌ Ingestion failed</span>
                                      </div>
                                    );
                                  }
                                  return null;
                                })()}
                              </div>
                            )}

                            {/* Actions */}
                            <div className="flex items-center justify-between mt-2">
                              <div className="flex gap-2">
                                <a
                                  href={paper.url}
                                  target="_blank"
                                  rel="noreferrer"
                                  title="Read Paper"
                                  className="p-2.5 rounded-full bg-neutral-800 text-gray-400 hover:bg-white hover:text-black transition-all duration-200"
                                >
                                  <ExternalLink className="w-5 h-5" />
                                </a>

                                <button
                                  onClick={() => generateIdeas(paper)}
                                  title="Generate Research Ideas"
                                  className="p-2.5 rounded-full bg-neutral-800 text-gray-400 hover:bg-blue-500 hover:text-white transition-all duration-200"
                                >
                                  <Lightbulb className="w-5 h-5" />
                                </button>

                                <button
                                  onClick={() => visualize(paper)}
                                  title="Visualize Mindmap"
                                  className="p-2.5 rounded-full bg-neutral-800 text-gray-400 hover:bg-purple-500 hover:text-white transition-all duration-200"
                                >
                                  <Network className="w-5 h-5" />
                                </button>

                                {/* GitHub/Code Link Button */}
                                {(paper.github_url || paper.project_page) && (
                                  <a
                                    href={paper.github_url || paper.project_page}
                                    target="_blank"
                                    rel="noreferrer"
                                    title={paper.github_url ? "View Code on GitHub" : "View Project Page"}
                                    className="p-2.5 rounded-full bg-neutral-800 text-gray-400 hover:bg-green-500 hover:text-white transition-all duration-200"
                                  >
                                    <Code className="w-5 h-5" />
                                  </a>
                                )}
                              </div>

                              <div className="flex gap-2">
                                <button
                                  onClick={() => toggleFavorite(paper)}
                                  title={paper.is_favorited ? "Remove from Favorites" : "Add to Favorites"}
                                  className={`p-2.5 rounded-full transition-all duration-200 ${paper.is_favorited
                                    ? 'bg-red-500/20 text-red-500 hover:bg-red-500 hover:text-white'
                                    : 'bg-neutral-800 text-gray-400 hover:bg-red-500 hover:text-white'}`}
                                >
                                  <Heart className={`w-5 h-5 ${paper.is_favorited ? 'fill-current' : ''}`} />
                                </button>

                                <button
                                  onClick={() => toggleSaved(paper)}
                                  title={paper.is_saved ? "Unsave" : "Save to Personal Library"}
                                  className={`p-2.5 rounded-full transition-all duration-200 ${paper.is_saved
                                    ? 'bg-blue-500/20 text-blue-500 hover:bg-blue-500 hover:text-white'
                                    : 'bg-neutral-800 text-gray-400 hover:bg-blue-500 hover:text-white'}`}
                                >
                                  <Bookmark className={`w-5 h-5 ${paper.is_saved ? 'fill-current' : ''}`} />
                                </button>
                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                </div>
              )}
            </>
          )}

          {/* Pagination Controls - Only on Explore */}
          {!loading && !error && activeView === 'explore' && totalPages > 1 && (
            <div className="max-w-2xl mx-auto mt-12 flex items-center justify-center gap-3">
              <button
                onClick={() => goToPage(currentPage - 1)}
                disabled={currentPage === 1}
                className="px-4 py-2 rounded-lg bg-neutral-800 text-white hover:bg-neutral-700 disabled:opacity-30 disabled:cursor-not-allowed transition border border-white/10"
              >
                Previous
              </button>

              <div className="flex gap-2">
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  // Show first page, last page, and pages around current
                  let pageNum;
                  if (totalPages <= 5) {
                    pageNum = i + 1;
                  } else if (currentPage <= 3) {
                    pageNum = i + 1;
                  } else if (currentPage >= totalPages - 2) {
                    pageNum = totalPages - 4 + i;
                  } else {
                    pageNum = currentPage - 2 + i;
                  }

                  return (
                    <button
                      key={i}
                      onClick={() => goToPage(pageNum)}
                      className={`px-4 py-2 rounded-lg transition border ${currentPage === pageNum
                        ? 'bg-white text-black border-white'
                        : 'bg-neutral-800 text-gray-400 hover:bg-neutral-700 border-white/10'
                        }`}
                    >
                      {pageNum}
                    </button>
                  );
                })}
              </div>

              <button
                onClick={() => goToPage(currentPage + 1)}
                disabled={currentPage === totalPages}
                className="px-4 py-2 rounded-lg bg-neutral-800 text-white hover:bg-neutral-700 disabled:opacity-30 disabled:cursor-not-allowed transition border border-white/10"
              >
                Next
              </button>

              <span className="ml-4 text-sm text-gray-500">
                Page {currentPage} of {totalPages} ({totalPapers} papers)
              </span>
            </div>
          )}
        </section>
      </main>

      {/* Modal Overlay */}
      {viewMode !== 'none' && activePaper && (
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
      )}
    </div>
  );
}
