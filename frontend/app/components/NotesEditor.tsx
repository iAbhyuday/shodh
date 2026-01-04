"use client"

import React, { useState, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import { Save } from 'lucide-react';

interface NotesEditorProps {
    paperId: string;
    notes: string;
    onChange: (notes: string) => void;
    onSave?: () => void;
}

export const NotesEditor: React.FC<NotesEditorProps> = ({ paperId, notes, onChange, onSave }) => {
    const [isSaving, setIsSaving] = useState(false);
    const [lastSaved, setLastSaved] = useState<Date | null>(null);

    // Debounce save logic
    // We need to track the *previous* saved content to know if we should save
    // Or just save whatever is passed after 2s of "silence".
    // Since 'notes' updates frequently (on every keystroke), we need a ref to track the last SAVED version.
    // Actually, simpler: Use a useEffect that triggers save 2s after `notes` changes.

    useEffect(() => {
        const timeoutId = setTimeout(() => {
            // We can't easily check against "initialNotes" anymore since that concept is gone.
            // We should just save if it's not empty? Or we can optimistically save.
            // Ideally we check if it CHANGED from the DB version. 
            // For now, let's just save. The backend can handle "no change" if needed, 
            // or we assume if the user typed, we save.
            // To prevent save on mount, we can use a ref.
            handleSave();
        }, 2000);

        return () => clearTimeout(timeoutId);
    }, [notes]);

    // Prevent initial save on mount? 
    // Yes, we should probably useRef to track "mounted" or "dirty".
    const isDirty = React.useRef(false);
    useEffect(() => {
        if (isDirty.current) {
            // Only set timer if dirty
        } else {
            isDirty.current = true; // First render passed
        }
    }, [notes]);

    // Re-implementing save to use the prop 'notes'
    const handleSave = async () => {
        // Simple optimization: Don't save if empty string? (Unless clearing notes)

        setIsSaving(true);
        try {
            const response = await fetch('/api/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    paper_id: paperId,
                    user_notes: notes
                })
            });
            if (response.ok) {
                setLastSaved(new Date());
                if (onSave) onSave();
            }
        } catch (error) {
            console.error("Failed to save notes:", error);
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div className="flex flex-col h-full bg-[#1A1A1A] text-gray-200">
            {/* Toolbar */}
            <div className="flex items-center justify-between p-2 border-b border-white/10 text-xs text-gray-400">
                <span className="font-medium text-gray-300">MARKDOWN</span>
                <div className="flex items-center gap-2">
                    {isSaving ? (
                        <span className="animate-pulse text-indigo-400">Saving...</span>
                    ) : lastSaved ? (
                        <span>Saved {lastSaved.toLocaleTimeString()}</span>
                    ) : null}
                    <button
                        onClick={handleSave}
                        className="p-1 hover:bg-white/10 rounded transition-colors"
                        title="Save Now"
                    >
                        <Save className="w-4 h-4" />
                    </button>
                </div>
            </div>

            {/* Editor Area */}
            <textarea
                className="flex-1 w-full bg-transparent p-4 resize-none focus:outline-none font-mono text-sm leading-relaxed customized-scrollbar placeholder:text-gray-700"
                placeholder="# My Research Notes\n\n- Key insight 1\n- question to explore..."
                value={notes}
                onChange={(e) => onChange(e.target.value)}
            />
        </div>
    );
};
