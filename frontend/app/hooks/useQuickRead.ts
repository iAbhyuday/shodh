// Hook for quick read/insights panel
import { useState, useCallback } from 'react';
import { papersApi } from '../lib/api-client';
import type { Paper } from '../lib/types';
import { useUIStore } from '../stores';

export function useQuickRead() {
    // Panel state from global UI store
    const quickReadPaper = useUIStore((s) => s.quickReadPaper);
    const isQuickReadOpen = useUIStore((s) => s.isQuickReadOpen);
    const openQuickRead = useUIStore((s) => s.openQuickRead);
    const closeQuickRead = useUIStore((s) => s.closeQuickRead);

    // Insights state (local to avoid unnecessary re-renders elsewhere)
    const [studyInsights, setStudyInsights] = useState("");
    const [isLoadingInsights, setIsLoadingInsights] = useState(false);

    const fetchQuickInsights = useCallback(async (paperId: string, summary?: string) => {
        setIsLoadingInsights(true);
        setStudyInsights("");
        try {
            const data = await papersApi.getInsights(paperId, summary);
            setStudyInsights(data.insights);
        } catch (e) {
            console.error("Failed to fetch insights", e);
        } finally {
            setIsLoadingInsights(false);
        }
    }, []);

    const handleQuickRead = useCallback((paper: Paper) => {
        openQuickRead(paper);
        setStudyInsights("");
        fetchQuickInsights(paper.id, paper.abstract);
    }, [openQuickRead, fetchQuickInsights]);

    return {
        quickReadPaper,
        isQuickReadOpen,
        studyInsights,
        isLoadingInsights,
        handleQuickRead,
        closeQuickRead,
    };
}
