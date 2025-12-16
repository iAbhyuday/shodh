"use client";
import React, { useState, useEffect } from 'react';
import { Search, BookOpen, ExternalLink, Lightbulb, Network, Heart, Bookmark, RefreshCw, Hash, List, Code, Compass, MessageSquare, Star } from 'lucide-react';
import InteractiveMindMap from './components/InteractiveMindMap';

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
              {/* Assistant View */}
              {activeView === 'assistant' ? (
                <div className="max-w-2xl mx-auto text-center py-20">
                  <MessageSquare className="w-16 h-16 mx-auto mb-4 text-gray-600" />
                  <h3 className="text-2xl font-bold text-white mb-2">Research Assistant</h3>
                  <p className="text-gray-400 mb-6">AI-powered research companion (Coming Soon)</p>
                  <div className="bg-neutral-900 border border-white/10 rounded-xl p-6 text-left">
                    <p className="text-sm text-gray-500">
                      Future features:
                    </p>
                    <ul className="mt-3 space-y-2 text-sm text-gray-400">
                      <li>• Ask questions about your saved papers</li>
                      <li>• Get summaries and insights</li>
                      <li>• Generate literature review drafts</li>
                      <li>• Discover connections between papers</li>
                    </ul>
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
                          <div className="p-6">
                            {/* Header: Title + Date */}
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
