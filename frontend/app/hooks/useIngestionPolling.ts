// Hook for polling ingestion status from the backend
import { useEffect, useRef, useCallback } from 'react';
import { ingestionApi, papersApi } from '../lib/api-client';
import type { IngestionStatus, Paper } from '../lib/types';

const POLL_INTERVAL = 3000; // 3 seconds

interface UseIngestionPollingOptions {
    feed: Paper[];
    onStatusUpdate: (statuses: Record<string, IngestionStatus>) => void;
}

export function useIngestionPolling({ feed, onStatusUpdate }: UseIngestionPollingOptions) {
    const statusRef = useRef<Record<string, IngestionStatus>>({});

    // Sync ingestion status from feed
    useEffect(() => {
        const next = { ...statusRef.current };
        let changed = false;

        feed.forEach(p => {
            const status = p.ingestion_status;
            if (status && ['pending', 'processing', 'downloading', 'indexing'].includes(status)) {
                if (!next[p.id] || next[p.id].status !== status) {
                    next[p.id] = { status, chunk_count: null, title: p.title };
                    changed = true;
                }
            }
        });

        if (changed) {
            statusRef.current = next;
            onStatusUpdate(next);
        }
    }, [feed, onStatusUpdate]);

    // Poll active jobs from ingestion manager
    useEffect(() => {
        const pollJobs = async () => {
            try {
                const jobs = await ingestionApi.getActiveJobs();
                const next = { ...statusRef.current };
                let changed = false;

                jobs.forEach((job) => {
                    const current = next[job.paper_id];
                    if (!current || current.status !== job.status || current.chunk_count !== job.progress) {
                        next[job.paper_id] = {
                            status: job.status,
                            chunk_count: job.progress,
                            title: job.title,
                        };
                        changed = true;
                    }
                });

                if (changed) {
                    statusRef.current = next;
                    onStatusUpdate(next);
                }
            } catch (e) {
                console.error("Failed to poll jobs", e);
            }
        };

        const interval = setInterval(pollJobs, POLL_INTERVAL);
        return () => clearInterval(interval);
    }, [onStatusUpdate]);

    // Check status for a specific paper
    const checkPaperStatus = useCallback(async (paperId: string, title?: string) => {
        try {
            const data = await papersApi.getIngestionStatus(paperId);
            if (data.ingestion_status !== 'completed') {
                const next = {
                    ...statusRef.current,
                    [paperId]: {
                        status: data.ingestion_status || 'pending',
                        chunk_count: 0,
                        title
                    },
                };
                statusRef.current = next;
                onStatusUpdate(next);
            }
        } catch (e) {
            console.error("Failed to check paper status", e);
        }
    }, [onStatusUpdate]);

    return {
        ingestionStatus: statusRef.current,
        checkPaperStatus,
    };
}
