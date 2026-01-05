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
            if (status && ['queued', 'pending', 'processing', 'downloading', 'indexing'].includes(status)) {
                if (!next[p.id] || next[p.id].status !== status) {
                    next[p.id] = {
                        status,
                        chunk_count: null,
                        title: p.title,
                        progress: status === 'completed' ? 100 : (status === 'queued' ? 0 : 5),
                        step: status === 'completed' ? 'completed' : (status === 'queued' ? 'queued' : 'starting')
                    };
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
                const activeJobIds = new Set<string>();

                // Update active jobs
                jobs.forEach((job) => {
                    activeJobIds.add(job.paper_id);
                    const current = next[job.paper_id];
                    if (!current || current.status !== job.status || current.progress !== job.progress || current.step !== job.step) {
                        next[job.paper_id] = {
                            status: job.status,
                            chunk_count: job.progress, // Keep for compat, but we prefer progress field
                            progress: job.progress,
                            step: job.step,
                            title: job.title,
                        };
                        changed = true;
                    }
                });

                // Check for jobs that disappeared (completed or failed)
                Object.keys(next).forEach((id) => {
                    if (!activeJobIds.has(id)) {
                        const current = next[id];
                        // If locally we think it's still running, but it's not in active list -> check final status
                        if (current && ['queued', 'pending', 'processing', 'downloading', 'parsing', 'indexing'].includes(current.status)) {
                            checkPaperStatus(id, current.title);
                        }
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
    }, [onStatusUpdate]); // checkPaperStatus is stable ref via useCallback? No, need to include it or rely on stable ref. 
    // It depends on onStatusUpdate.
    // But checkPaperStatus usage in effect requires it in deps. 
    // NOTE: Added checkPaperStatus to deps below or relying on eslint-disable? 
    // Better: add checkPaperStatus to deps.

    // Check status for a specific paper
    const checkPaperStatus = useCallback(async (paperId: string, title?: string) => {
        try {
            const data = await papersApi.getIngestionStatus(paperId);
            // Always update if status changed, including 'completed'
            const current = statusRef.current[paperId];
            if (!current || current.status !== data.ingestion_status) {
                const next = {
                    ...statusRef.current,
                    [paperId]: {
                        status: data.ingestion_status || 'pending',
                        chunk_count: current?.chunk_count || 0,
                        progress: data.progress !== undefined ? data.progress : (current?.progress || (data.ingestion_status === 'completed' ? 100 : 0)),
                        step: data.step !== undefined ? data.step : (current?.step || (data.ingestion_status === 'completed' ? 'completed' : 'processing')),
                        title: title || current?.title
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
