import React from 'react';
import { Plus, Bookmark, Network, Trash2, X } from 'lucide-react';

type Project = {
    id: number;
    name: string;
    description: string | null;
    research_dimensions: string | null;
    created_at: string;
    paper_count: number;
};

interface LibraryViewProps {
    projects: Project[];
    isCreatingProject: boolean;
    setIsCreatingProject: (val: boolean) => void;
    newProjectName: string;
    setNewProjectName: (val: string) => void;
    newProjectDimensions: string;
    setNewProjectDimensions: (val: string) => void;
    onCreateProject: () => void;
    onQuickRead: (paper: Paper) => void;
    onDeepRead: (paper: Paper) => void;
    onVisualize: (paper: Paper) => void;
    onSelectProject: (project: Project | null) => void;
    onDeleteProject: (projectId: number) => void;
    onFetchBookmarks: () => void;
}

const LibraryView: React.FC<LibraryViewProps> = ({
    projects,
    isCreatingProject,
    setIsCreatingProject,
    newProjectName,
    setNewProjectName,
    newProjectDimensions,
    setNewProjectDimensions,
    onCreateProject,
    onSelectProject,
    onDeleteProject,
    onFetchBookmarks
}) => {
    return (
        <div className="max-w-5xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-700">
            <div className="flex justify-between items-center mb-10">
                <div>
                    <h2 className="text-3xl font-bold text-white mb-2 tracking-tight">Synthesis Vault</h2>
                    <p className="text-gray-500 text-sm">Organize and process your research into synthesized intelligence.</p>
                </div>
                <button
                    onClick={() => setIsCreatingProject(true)}
                    className="flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white text-sm font-bold rounded-2xl hover:bg-indigo-500 transition-all shadow-xl shadow-indigo-500/20 active:scale-95"
                >
                    <Plus className="w-5 h-5" />
                    New Project
                </button>
            </div>

            {isCreatingProject && (
                <div className="mb-10 p-8 glass rounded-3xl border border-indigo-500/30 flex flex-col gap-6 animate-in fade-in slide-in-from-top-6 duration-500">
                    <div className="flex gap-4">
                        <div className="flex-1 space-y-2">
                            <label className="text-[10px] font-bold text-gray-500 uppercase tracking-widest ml-1">Project Name</label>
                            <input
                                autoFocus
                                type="text"
                                placeholder="e.g., Deep RL in Robotics"
                                value={newProjectName}
                                onChange={(e) => setNewProjectName(e.target.value)}
                                className="w-full bg-[#0a0a0b] border border-white/5 rounded-2xl px-6 py-4 text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all"
                            />
                        </div>
                        <div className="flex items-end gap-2">
                            <button
                                onClick={onCreateProject}
                                disabled={!newProjectName.trim()}
                                className="px-8 py-4 bg-indigo-600 text-white font-bold rounded-2xl hover:bg-indigo-500 transition-all shadow-xl shadow-indigo-500/20 active:scale-95 disabled:opacity-50 disabled:active:scale-100"
                            >
                                Create Project
                            </button>
                            <button
                                onClick={() => setIsCreatingProject(false)}
                                className="p-4 bg-neutral-800 text-gray-400 rounded-2xl hover:bg-neutral-700 hover:text-white transition-colors"
                            >
                                <X className="w-6 h-6" />
                            </button>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <label className="text-[10px] font-bold text-gray-500 uppercase tracking-widest ml-1">Research Dimensions & Preliminary Info</label>
                        <textarea
                            placeholder="What are the key goals, themes, or specific questions you want to explore in this project? This helps the AI guide your research."
                            value={newProjectDimensions}
                            onChange={(e) => setNewProjectDimensions(e.target.value)}
                            className="w-full bg-[#0a0a0b] border border-white/5 rounded-2xl px-6 py-4 text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all min-h-[120px] resize-none"
                        />
                    </div>
                </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                {/* Default Uncategorized View */}
                <div
                    onClick={() => {
                        onSelectProject(null);
                        onFetchBookmarks();
                    }}
                    className="p-8 glass rounded-3xl border border-white/5 hover:border-white/20 transition-all cursor-pointer group relative overflow-hidden h-48 flex flex-col justify-end"
                >
                    <div className="absolute top-6 right-6 p-4 bg-neutral-800 rounded-2xl group-hover:bg-neutral-700 transition-colors">
                        <Bookmark className="w-6 h-6 text-gray-400 group-hover:text-white transition-colors" />
                    </div>
                    <div>
                        <h3 className="text-xl font-bold text-white mb-1">All Bookmarks</h3>
                        <p className="text-sm text-gray-500">Uncategorized papers</p>
                    </div>
                </div>

                {projects.map((project) => (
                    <div
                        key={project.id}
                        onClick={() => onSelectProject(project)}
                        className="p-8 glass rounded-3xl border border-white/5 hover:border-indigo-500/30 transition-all cursor-pointer group relative overflow-hidden h-48 flex flex-col justify-end"
                    >
                        <div className="absolute -top-4 -right-4 p-8 opacity-5 group-hover:opacity-10 transition-opacity">
                            <Network className="w-32 h-32 text-indigo-500" />
                        </div>
                        <div className="absolute top-6 right-6 flex gap-2">
                            <div className="p-4 bg-indigo-600/10 rounded-2xl border border-indigo-500/20 group-hover:bg-indigo-600/20 transition-colors">
                                <Network className="w-6 h-6 text-indigo-400 group-hover:text-indigo-300 transition-colors" />
                            </div>
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    if (confirm(`Delete project "${project.name}"?`)) {
                                        onDeleteProject(project.id);
                                    }
                                }}
                                className="p-4 bg-red-600/10 rounded-2xl border border-red-500/20 hover:bg-red-600/30 transition-colors opacity-0 group-hover:opacity-100"
                                title="Delete Project"
                            >
                                <Trash2 className="w-6 h-6 text-red-400 hover:text-red-300 transition-colors" />
                            </button>
                        </div>
                        <div>
                            <h3 className="text-xl font-bold text-white mb-1">{project.name}</h3>
                            <p className="text-sm text-gray-500">
                                {project.paper_count} {project.paper_count === 1 ? 'paper' : 'papers'}
                            </p>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default LibraryView;
