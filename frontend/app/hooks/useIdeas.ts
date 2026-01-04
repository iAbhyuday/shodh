// Hook for ideas and visualization generation
import { useCallback } from 'react';
import { ideasApi } from '../lib/api-client';
import type { Paper, MindMapNode } from '../lib/types';

interface UseIdeasOptions {
    onOpenIdeas: (paper: Paper) => void;
    onOpenVis: (paper: Paper) => void;
    onSetIdeas: (ideas: string[]) => void;
    onSetMindMapData: (data: MindMapNode | null) => void;
    onSetGenerating: (generating: boolean) => void;
}

export function useIdeas({
    onOpenIdeas,
    onOpenVis,
    onSetIdeas,
    onSetMindMapData,
    onSetGenerating,
}: UseIdeasOptions) {

    const generateIdeas = useCallback(async (paper: Paper) => {
        onOpenIdeas(paper);
        try {
            const data = await ideasApi.generate(paper.id);
            onSetIdeas(data.ideas || ["No ideas generated."]);
        } catch (e) {
            console.error(e);
            onSetIdeas(["Error generating ideas."]);
        } finally {
            onSetGenerating(false);
        }
    }, [onOpenIdeas, onSetIdeas, onSetGenerating]);

    const visualize = useCallback(async (paper: Paper) => {
        onOpenVis(paper);
        try {
            const data = await ideasApi.visualize(paper.id);
            onSetMindMapData((data.mindmap as MindMapNode) || null);
        } catch (e) {
            console.error(e);
            onSetMindMapData(null);
        } finally {
            onSetGenerating(false);
        }
    }, [onOpenVis, onSetMindMapData, onSetGenerating]);

    return {
        generateIdeas,
        visualize,
    };
}
