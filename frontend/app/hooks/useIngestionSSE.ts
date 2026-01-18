/**
 * SSE Hook for Real-time Ingestion Status Updates
 * 
 * Replaces HTTP polling with Server-Sent Events for instant push-based updates.
 * Uses EventSource API to connect to the backend SSE endpoint.
 */
import { useEffect, useRef, useCallback } from 'react';
import type { IngestionStatus } from '../lib/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
const SSE_RECONNECT_DELAY = 3000; // 3 seconds

interface SSEEvent {
    event: string;
    data: {
        paper_id: string;
        status: string;
        progress: number;
        step: string;
        title?: string;
        error?: string;
    };
    timestamp: string;
}

interface UseIngestionSSEOptions {
    onStatusUpdate: (paperId: string, status: IngestionStatus) => void;
    enabled?: boolean;
}

export function useIngestionSSE({ onStatusUpdate, enabled = true }: UseIngestionSSEOptions) {
    const eventSourceRef = useRef<EventSource | null>(null);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    const connect = useCallback(() => {
        // Skip SSE on server-side (EventSource is browser-only)
        if (typeof window === 'undefined') return;
        if (!enabled) return;

        // Clean up existing connection
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
        }

        const eventSource = new EventSource(`${API_URL}/events/ingestion`);
        eventSourceRef.current = eventSource;

        eventSource.onopen = () => {
            console.log('[SSE] Connected to ingestion events');
        };

        eventSource.onmessage = (event) => {
            try {
                const parsed: SSEEvent = JSON.parse(event.data);

                if (parsed.event === 'ingestion_status') {
                    const { paper_id, status, progress, step, title, error } = parsed.data;

                    onStatusUpdate(paper_id, {
                        status,
                        progress,
                        step,
                        title: title || '',
                        chunk_count: null,
                        error: error || undefined
                    });
                }
            } catch (e) {
                console.error('[SSE] Failed to parse event:', e);
            }
        };

        eventSource.onerror = (error) => {
            console.error('[SSE] Connection error:', error);
            eventSource.close();
            eventSourceRef.current = null;

            // Schedule reconnection
            if (enabled) {
                reconnectTimeoutRef.current = setTimeout(() => {
                    console.log('[SSE] Attempting reconnection...');
                    connect();
                }, SSE_RECONNECT_DELAY);
            }
        };
    }, [enabled, onStatusUpdate]);

    // Setup SSE connection (client-side only)
    useEffect(() => {
        if (typeof window === 'undefined') return;

        connect();

        return () => {
            // Cleanup on unmount
            if (eventSourceRef.current) {
                eventSourceRef.current.close();
                eventSourceRef.current = null;
            }
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
            }
        };
    }, [connect]);

    // Manual reconnect function
    const reconnect = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
        }
        connect();
    }, [connect]);

    return {
        reconnect,
        isConnected: typeof window !== 'undefined' && eventSourceRef.current?.readyState === EventSource.OPEN
    };
}

