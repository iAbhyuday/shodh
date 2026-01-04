import React, { useState } from 'react';
import { Bell, RefreshCw, X } from 'lucide-react';

type IngestionStatus = {
    status: string;
    chunk_count: number | null;
    title?: string;
};

type NotificationBellProps = {
    ingestionStatus: Record<string, IngestionStatus>;
};

export default function NotificationBell({ ingestionStatus }: NotificationBellProps) {
    const [isOpen, setIsOpen] = useState(false);

    // Filter active tasks
    const activeTasks = Object.entries(ingestionStatus)
        .filter(([_, info]) => ['pending', 'downloading', 'parsing', 'indexing', 'processing', 'failed'].includes(info.status))
        .map(([id, info]) => ({ id, ...info }));

    // Has active tasks?
    const hasActive = activeTasks.length > 0;

    return (
        <div className="relative z-[110]">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="relative p-2 hover:bg-neutral-800 rounded-full transition text-gray-400 hover:text-white"
                title="Notifications"
            >
                <Bell className={`w-5 h-5 ${hasActive ? 'text-indigo-400' : ''}`} />
                {hasActive && (
                    <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-indigo-500 rounded-full animate-pulse border border-black" />
                )}
            </button>

            {/* Dropdown Popover */}
            {isOpen && (
                <>
                    {/* Backdrop to close on click outside */}
                    <div className="fixed inset-0 z-[110]" onClick={() => setIsOpen(false)} />

                    <div className="absolute right-0 mt-2 w-80 bg-neutral-900 border border-white/10 rounded-xl shadow-2xl z-[120] overflow-hidden animate-in fade-in zoom-in-95 duration-200">
                        <div className="p-3 border-b border-white/10 flex justify-between items-center bg-black/40">
                            <h3 className="text-sm font-bold text-white">Activity</h3>
                            {hasActive && (
                                <span className="text-[10px] bg-indigo-500/20 text-indigo-400 px-1.5 py-0.5 rounded font-mono">
                                    {activeTasks.length} RUNNING
                                </span>
                            )}
                        </div>

                        <div className="max-h-80 overflow-y-auto custom-scrollbar p-2 space-y-2">
                            {activeTasks.length === 0 ? (
                                <div className="text-center py-8 text-gray-500 text-xs">
                                    <p>No active tasks.</p>
                                </div>
                            ) : (
                                activeTasks.map((task) => (
                                    <div key={task.id} className={`rounded-lg p-3 border ${task.status === 'failed' ? 'bg-red-500/10 border-red-500/30' : 'bg-white/5 border-white/5'}`}>
                                        <div className="flex items-center gap-3 mb-2">
                                            {task.status === 'failed' ? (
                                                <div className="w-3.5 h-3.5 rounded-full bg-red-500 flex items-center justify-center flex-shrink-0">
                                                    <X className="w-2.5 h-2.5 text-black" />
                                                </div>
                                            ) : (
                                                <RefreshCw className="w-3.5 h-3.5 text-indigo-400 animate-spin flex-shrink-0" />
                                            )}
                                            <div className="min-w-0 flex-1">
                                                <p className={`text-xs font-medium truncate ${task.status === 'failed' ? 'text-red-400' : 'text-white'}`} title={task.title}>
                                                    {task.title || 'Processing Paper...'}
                                                </p>
                                                <div className="flex justify-between items-center mt-0.5">
                                                    <span className={`text-[10px] uppercase ${task.status === 'failed' ? 'text-red-500' : 'text-gray-400'}`}>
                                                        {task.status === 'failed' ? 'Ingestion Failed' : task.status}
                                                    </span>
                                                    {task.chunk_count && (
                                                        <span className="text-[10px] text-gray-600 font-mono">{task.chunk_count} chunks</span>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                        {/* Progress Bar */}
                                        <div className="h-1 w-full bg-black/50 rounded-full overflow-hidden">
                                            <div
                                                className={`h-full transition-all duration-1000 ${task.status === 'failed' ? 'bg-red-500' : 'bg-gradient-to-r from-indigo-600 to-indigo-400'}`}
                                                style={{
                                                    width: task.status === 'completed' ? '100%' :
                                                        task.status === 'failed' ? '100%' :
                                                            task.status === 'indexing' ? '85%' :
                                                                task.status === 'parsing' ? '60%' :
                                                                    task.status === 'downloading' ? '30%' : '10%'
                                                }}
                                            />
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>

                        {hasActive && (
                            <div className="p-2 border-t border-white/10 bg-black/20 text-center">
                                <p className="text-[10px] text-gray-500">Do not close the tab while processing.</p>
                            </div>
                        )}
                    </div>
                </>
            )}
        </div>
    );
}
