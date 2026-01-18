"use client";

import React from 'react';
import { Sparkles, Plus, Loader2 } from 'lucide-react';

interface UpgradeBannerProps {
    onAddToProject: () => void;
    isIngesting?: boolean;
    ingestionProgress?: string;
}

/**
 * Banner shown in Deep Read when paper is not ingested.
 * Prompts user to add paper to a project for full RAG analysis.
 */
export const UpgradeBanner: React.FC<UpgradeBannerProps> = ({
    onAddToProject,
    isIngesting = false,
    ingestionProgress
}) => {
    if (isIngesting) {
        return (
            <div className="bg-gradient-to-r from-indigo-900/30 to-purple-900/30 border border-indigo-500/30 rounded-lg p-3 mx-4 mt-3">
                <div className="flex items-center gap-3">
                    <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />
                    <div className="flex-1">
                        <p className="text-sm text-white font-medium">
                            Ingesting paper...
                        </p>
                        <p className="text-xs text-gray-400">
                            {ingestionProgress || "Processing PDF for full analysis"}
                        </p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="bg-gradient-to-r from-amber-900/20 to-orange-900/20 border border-amber-500/30 rounded-lg p-3 mx-4 mt-3">
            <div className="flex items-center gap-3">
                <Sparkles className="w-5 h-5 text-amber-400" />
                <div className="flex-1">
                    <p className="text-sm text-white">
                        <span className="font-medium">Limited Mode</span>
        
                    </p>
                </div>
                <button
                    onClick={onAddToProject}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-600/80 hover:bg-amber-600 text-white text-xs font-medium rounded-md transition-colors"
                >
                    <Plus className="w-3.5 h-3.5" />
                    Add to Project
                </button>
            </div>
        </div>
    );
};
