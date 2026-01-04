"use client"

import React, { useState, useEffect, use } from 'react';
import { DeepReadView } from '../../components/DeepReadView';
import { useRouter } from 'next/navigation';

export default function PaperPage({ params }: { params: Promise<{ id: string }> }) {
    // Unwrap params in Next.js 15+
    const resolvedParams = use(params);
    const paperId = resolvedParams.id;
    const router = useRouter();

    const [paper, setPaper] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function fetchPaper() {
            try {
                // Fetch full metadata (including ArXiv fallback if needed)
                const res = await fetch(`/api/paper/${paperId}/metadata`);

                if (res.ok) {
                    const data = await res.json();
                    setPaper(data);
                } else {
                    // Fallback defaults
                    setPaper({
                        id: paperId,
                        title: `arXiv:${paperId}`,
                        ingestion_status: null,
                        authors: [],
                        abstract: '',
                        user_notes: ''
                    });
                }
            } catch (e) {
                console.error(e);
                setPaper({
                    id: paperId,
                    title: `arXiv:${paperId}`,
                    ingestion_status: null
                });
            } finally {
                setLoading(false);
            }
        }

        if (paperId) fetchPaper();
    }, [paperId]);

    const handleBack = () => {
        router.push('/');
    };

    if (loading || !paper) {
        return <div className="h-screen bg-black flex items-center justify-center text-white">Loading Paper...</div>;
    }

    return (
        <DeepReadView
            paperId={paperId}
            paperMetadata={paper}
            onBack={handleBack}
        />
    );
}
