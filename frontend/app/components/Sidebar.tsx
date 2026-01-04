import React from 'react';
import { Compass, Heart, FolderArchive, Settings, ChevronLeft, ChevronRight } from 'lucide-react';

type Project = {
    id: number;
    name: string;
};

interface SidebarProps {
    sidebarOpen: boolean;
    setSidebarOpen: (isOpen: boolean) => void;
    activeView: string;
    setActiveView: (view: any) => void;
    onResetProject: () => void;
    projects: Project[];
    selectedProject: Project | null;
    onSelectProject: (project: Project) => void;
    onOpenSettings: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
    sidebarOpen,
    setSidebarOpen,
    activeView,
    setActiveView,
    onResetProject,
    projects,
    selectedProject,
    onSelectProject,
    onOpenSettings
}) => {
    return (
        <aside
            className={`fixed left-0 top-16 h-[calc(100vh-4rem)] bg-neutral-900 border-r border-white/10 flex flex-col transition-all duration-300 ease-in-out z-[90] ${sidebarOpen ? 'w-64' : 'w-16'}`}
        >
            <nav className="flex-1 space-y-2 p-2">
                <button
                    onClick={() => {
                        setActiveView('explore');
                        onResetProject();
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
                        onResetProject();
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
                        onResetProject();
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
                                        onSelectProject(proj);
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
                                        onResetProject();
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
                    onClick={onOpenSettings}
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
    );
};
