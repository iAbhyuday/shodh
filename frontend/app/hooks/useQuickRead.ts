// Hook for quick read/insights panel
import { useState, useCallback } from 'react';
import { papersApi } from '../lib/api-client';
import type { Paper } from '../lib/types';

export function useQuickRead() {
    const [quickReadPaper, setQuickReadPaper] = useState<Paper | null>(null);
    const [isQuickReadOpen, setIsQuickReadOpen] = useState(false);
    const [studyInsights, setStudyInsights] = useState("");
    const [isLoadingInsights, setIsLoadingInsights] = useState(false);

    const fetchQuickInsights = useCallback(async (paperId: string) => {
        setIsLoadingInsights(true);
        setStudyInsights("");
        try {
            const data = await papersApi.getInsights(paperId);
            setStudyInsights(data.insights);
        } catch (e) {
            console.error("Failed to fetch insights", e);
        } finally {
            setIsLoadingInsights(false);
        }
    }, []);

    const handleQuickRead = useCallback((paper: Paper) => {
        setQuickReadPaper(paper);
        setStudyInsights("");
        setIsQuickReadOpen(true);
        fetchQuickInsights(paper.id);
    }, [fetchQuickInsights]);

    const closeQuickRead = useCallback(() => {
        setIsQuickReadOpen(false);
    }, []);

    return {
        quickReadPaper,
        isQuickReadOpen,
        studyInsights,
        isLoadingInsights,
        handleQuickRead,
        closeQuickRead,
    };
}
