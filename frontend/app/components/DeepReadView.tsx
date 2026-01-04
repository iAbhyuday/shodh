"use client"

import React, { useState, useEffect, useRef } from 'react';
import { ArrowLeft, MessageSquare, BookOpen, PenTool, Layout, Share2, PanelLeftClose, PanelRightClose } from 'lucide-react';
import dynamic from 'next/dynamic';
import { NotesEditor } from './NotesEditor';
import { ChatPanel } from './ChatPanel';
import { ShodhLogo } from './ShodhLogo';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const PDFViewer = dynamic(() => import('./PDFViewer').then(mod => mod.PDFViewer), {
    ssr: false,
    loading: () => <div className="flex items-center justify-center p-12 text-gray-400">Loading PDF Viewer...</div>
});

import { Sidebar } from './Sidebar';

import { RefreshCw, Bell, Globe, FileText, Info, Sparkles, Moon, Sun, ZoomIn, ZoomOut } from 'lucide-react';
import { useRouter } from 'next/navigation';

const API_URL = "http://localhost:8000/api";

type Project = {
    id: number;
    name: string;
};

// Reuse types from AssistantView or import them if shared
interface Message {
    role: 'user' | 'assistant';
    content: string;
    citations?: any[];
}

interface DeepReadViewProps {
    paperId: string;
    paperMetadata: any;
    onBack: () => void;
}

export const DeepReadView: React.FC<DeepReadViewProps> = ({ paperId, paperMetadata, onBack }) => {
    const router = useRouter();

    // App Shell State
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [activeView, setActiveView] = useState('deepread');
    const [projects, setProjects] = useState<Project[]>([]);
    const [selectedProject, setSelectedProject] = useState<Project | null>(null);

    // Fetch projects for sidebar
    useEffect(() => {
        fetch(`${API_URL}/projects`)
            .then(res => res.json())
            .then(data => setProjects(data))
            .catch(err => console.error("Failed to fetch projects", err));
    }, []);

    // Handle Sidebar Navigation
    const handleSidebarNav = (view: string) => {
        if (view !== 'deepread') {
            router.push('/');
        }
    };

    // Original DeepRead State
    const [activeTab, setActiveTab] = useState<'chat' | 'notes'>('chat');
    const [leftPanelWidth, setLeftPanelWidth] = useState(60); // Percentage

    // Left Panel Tabs
    const [primaryTab, setPrimaryTab] = useState<'pdf' | 'info' | 'insights'>('pdf');
    const [isDarkMode, setIsDarkMode] = useState(false);
    const [scale, setScale] = useState(1.0);





    // Notes State (Lifted from NotesEditor)
    const [notes, setNotes] = useState<string>("");

    // Sync notes with metadata on load
    useEffect(() => {
        if (paperMetadata?.user_notes) setNotes(paperMetadata.user_notes);
        else if (paperMetadata?.notes) setNotes(paperMetadata.notes);
    }, [paperMetadata?.user_notes, paperMetadata?.notes]);

    const handleAddToNotes = (text: string) => {
        setNotes(prev => {
            const separator = prev.trim() ? "\n\n" : "";
            return `${prev.trim()}${separator}> ${text}`;
        });
        setActiveTab('notes'); // Switch to notes tab to show the addition
    };

    // Chat State
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);

    const handleSend = async () => {
        if (!input.trim() || loading) return;

        const userMsg = input;
        setInput("");
        setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
        setLoading(true);

        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    paper_id: paperId,
                    message: userMsg,
                    history: messages.slice(-6) // Keep context limited
                })
            });

            if (!res.ok) throw new Error("Chat failed");

            // Handle Stream
            const reader = res.body?.getReader();
            const decoder = new TextDecoder();

            setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

            let buffer = '';
            while (reader) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                buffer += chunk;

                setMessages(prev => {
                    const newArr = [...prev];
                    const last = newArr[newArr.length - 1];
                    if (last.role === 'assistant') {
                        if (buffer.startsWith('{')) {
                            const newline = buffer.indexOf('\n');
                            if (newline > -1) {
                                const content = buffer.slice(newline + 1);
                                last.content += content;
                                buffer = '';
                            }
                        } else {
                            last.content += chunk;
                            buffer = '';
                        }
                    }
                    return newArr;
                });
            }
        } catch (e) {
            console.error(e);
            setMessages(prev => [...prev, { role: 'assistant', content: "[Error generating response]" }]);
        } finally {
            setLoading(false);
        }
    };

    // PDF URL Strategy
    // STRICT MODE: Always Direct from ArXiv per user request.
    const pdfUrl = `https://arxiv.org/pdf/${paperId}`;

    return (
        <div className="min-h-screen bg-black text-gray-100 font-sans">
            {/* Header */}
            <header className="bg-black/80 backdrop-blur-md border-b border-white/10 sticky top-0 z-[100] h-16">
                <div className="max-w-7xl mx-auto px-4 h-full flex justify-between items-center">
                    <div className="flex items-center space-x-2 cursor-pointer" onClick={() => router.push('/')}>
                        <ShodhLogo className="w-6 h-6" />
                        <h1 className="text-xl font-bold text-white">Shodh (शोध)</h1>
                    </div>
                </div>
            </header>

            {/* Sidebar */}
            <Sidebar
                sidebarOpen={sidebarOpen}
                setSidebarOpen={setSidebarOpen}
                activeView={activeView}
                setActiveView={handleSidebarNav}
                onResetProject={() => setSelectedProject(null)}
                projects={projects}
                selectedProject={selectedProject}
                onSelectProject={setSelectedProject}
                onOpenSettings={() => { }}
            />

            {/* Main DeepRead Layout (adjusted for sidebar) */}
            <main
                className={`transition-all duration-300 ease-in-out ${sidebarOpen ? 'ml-64' : 'ml-16'} h-[calc(100vh-4rem)] flex overflow-hidden`}
            >
                {/* Left Panel: PDF Reader */}
                <div
                    className="flex flex-col border-r border-white/10 transition-all duration-300 relative bg-[#0A0A0A]"
                    style={{ width: `${leftPanelWidth}%` }}
                >
                    {/* Top Toolbar */}
                    <div className="h-12 border-b border-white/10 flex items-center px-4 justify-between bg-[#0A0A0A]">
                        <div className="flex items-center gap-2">
                            <button
                                onClick={onBack}
                                className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded-md transition"
                                title="Back to Library"
                            >
                                <ArrowLeft className="w-5 h-5" />
                            </button>
                            <div className="w-[1px] h-4 bg-white/10 mx-1" />

                            {/* Tabs */}
                            <div className="flex items-center bg-white/5 rounded-lg p-1 gap-1">
                                <button
                                    onClick={() => setPrimaryTab('pdf')}
                                    className={`flex items-center gap-2 px-3 py-1 rounded-md text-xs font-medium transition-colors ${primaryTab === 'pdf' ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-white'}`}
                                >
                                    <FileText className="w-3.5 h-3.5" />
                                    PDF
                                </button>
                                <button
                                    onClick={() => setPrimaryTab('info')}
                                    className={`flex items-center gap-2 px-3 py-1 rounded-md text-xs font-medium transition-colors ${primaryTab === 'info' ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-white'}`}
                                >
                                    <Info className="w-3.5 h-3.5" />
                                    Info
                                </button>
                                <button
                                    onClick={() => setPrimaryTab('insights')}
                                    className={`flex items-center gap-2 px-3 py-1 rounded-md text-xs font-medium transition-colors ${primaryTab === 'insights' ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-white'}`}
                                >
                                    <Sparkles className="w-3.5 h-3.5" />
                                    Insights
                                </button>
                            </div>
                        </div>

                        {/* Right Actions */}
                        <div className="flex items-center gap-2">
                            {primaryTab === 'pdf' && (
                                <>
                                    <div className="flex items-center bg-white/5 rounded-lg p-1 mr-2">
                                        <button
                                            onClick={() => setScale(s => Math.max(0.5, s - 0.1))}
                                            className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded-md transition"
                                            title="Zoom Out"
                                        >
                                            <ZoomOut className="w-4 h-4" />
                                        </button>
                                        <span className="text-xs w-12 text-center text-gray-400 font-mono">
                                            {Math.round(scale * 100)}%
                                        </span>
                                        <button
                                            onClick={() => setScale(s => Math.min(2.0, s + 0.1))}
                                            className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded-md transition"
                                            title="Zoom In"
                                        >
                                            <ZoomIn className="w-4 h-4" />
                                        </button>
                                    </div>

                                    <button
                                        onClick={() => setIsDarkMode(!isDarkMode)}
                                        className={`p-1.5 rounded-md transition ${isDarkMode ? 'text-yellow-400 bg-yellow-500/10' : 'text-gray-400 hover:text-white hover:bg-white/10'}`}
                                        title="Toggle Dark Mode"
                                    >
                                        {isDarkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
                                    </button>
                                </>
                            )}
                        </div>
                    </div>

                    {/* Content Area */}
                    <div className="flex-1 overflow-y-auto relative bg-[#1A1A1A]">
                        {primaryTab === 'pdf' && (
                            <PDFViewer
                                pdfUrl={pdfUrl}
                                isDarkMode={isDarkMode}
                                scale={scale}
                                onAddToNotes={handleAddToNotes}
                            />
                        )}

                        {primaryTab === 'info' && (
                            <div className="p-8 max-w-3xl mx-auto space-y-6">
                                <h1 className="text-3xl font-bold text-white leading-tight">{paperMetadata?.title || `Paper ${paperId}`}</h1>
                                <div className="space-y-4">
                                    <div className="flex flex-wrap gap-2 text-sm text-gray-400">
                                        <span className="bg-white/5 px-2 py-1 rounded">Published: {paperMetadata?.published_date || 'Unknown'}</span>
                                        {paperMetadata?.authors && <span className="bg-white/5 px-2 py-1 rounded">Authors: {paperMetadata.authors}</span>}
                                    </div>
                                    <p className="text-gray-300 leading-relaxed font-serif text-lg">
                                        {paperMetadata?.abstract || paperMetadata?.summary || "No abstract available."}
                                    </p>
                                </div>
                                {paperMetadata?.url && (
                                    <a href={paperMetadata.url} target="_blank" rel="noopener" className="inline-flex items-center gap-2 text-indigo-400 hover:underline">
                                        View Source <Globe className="w-3 h-3" />
                                    </a>
                                )}
                            </div>
                        )}

                        {primaryTab === 'insights' && (
                            <div className="p-8 max-w-3xl mx-auto">
                                <div className="bg-gradient-to-br from-indigo-900/20 to-purple-900/20 p-6 rounded-xl border border-indigo-500/30">
                                    <h2 className="text-2xl font-bold text-white mb-4 flex items-center gap-2">
                                        <Sparkles className="w-6 h-6 text-yellow-400" />
                                        AI Insights
                                    </h2>
                                    {paperMetadata?.notes || paperMetadata?.user_notes ? (
                                        <div className="prose prose-invert max-w-none text-sm">
                                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                {paperMetadata.notes || paperMetadata.user_notes}
                                            </ReactMarkdown>
                                        </div>
                                    ) : (
                                        <div className="text-center py-12 text-gray-500">
                                            <Sparkles className="w-12 h-12 mx-auto mb-4 opacity-20" />
                                            <p>No AI insights generated yet.</p>
                                            <p className="text-sm mt-2">Chat with the assistant to generate deeper understanding.</p>
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                {/* Drag Handle */}
                <div className="w-1 bg-[#1A1A1A] hover:bg-indigo-500 transition-colors cursor-col-resize z-20" />

                {/* Right Panel: Tools */}
                <div
                    className="flex flex-col bg-[#0A0A0A]"
                    style={{ width: `${100 - leftPanelWidth}%` }}
                >
                    {/* Tab Header */}
                    <div className="flex items-center border-b border-white/10 bg-[#0A0A0A]">
                        <button
                            onClick={() => setActiveTab('chat')}
                            className={`flex-1 flex items-center justify-center gap-2 py-3 text-sm font-medium transition-colors ${activeTab === 'chat'
                                ? 'text-indigo-400 border-b-2 border-indigo-500'
                                : 'text-gray-500 hover:text-gray-300'
                                }`}
                        >
                            <MessageSquare className="w-4 h-4" />
                            AI Assistant
                        </button>
                        <button
                            onClick={() => setActiveTab('notes')}
                            className={`flex-1 flex items-center justify-center gap-2 py-3 text-sm font-medium transition-colors ${activeTab === 'notes'
                                ? 'text-emerald-400 border-b-2 border-emerald-500'
                                : 'text-gray-500 hover:text-gray-300'
                                }`}
                        >
                            <PenTool className="w-4 h-4" />
                            My Notes
                        </button>
                        <button className="px-4 text-gray-500 hover:text-indigo-400 transition">
                            <Share2 className="w-4 h-4" />
                        </button>
                    </div>

                    {/* Tab Content */}
                    <div className="flex-1 overflow-hidden relative">
                        {activeTab === 'chat' ? (
                            <ChatPanel
                                messages={messages}
                                input={input}
                                loading={loading}
                                onInputChange={setInput}
                                onSend={handleSend}
                            />
                        ) : (
                            <NotesEditor
                                paperId={paperId}
                                notes={notes}
                                onChange={setNotes}
                            />
                        )}
                    </div>
                </div>
            </main >
        </div >
    );
};
