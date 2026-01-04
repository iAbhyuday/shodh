import { useState, useEffect, useRef } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { Plus } from 'lucide-react';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

// Set worker source
pdfjs.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.js';

interface PDFViewerProps {
    pdfUrl: string;
    isDarkMode?: boolean;
    scale?: number;
    onAddToNotes?: (text: string) => void;
}

export const PDFViewer: React.FC<PDFViewerProps> = ({ pdfUrl, isDarkMode = false, scale = 1.0, onAddToNotes }) => {
    const [numPages, setNumPages] = useState<number>(0);
    const [error, setError] = useState<string | null>(null);
    const [loadingProgress, setLoadingProgress] = useState<number>(0);

    // Text Selection Tooltip State
    const [tooltip, setTooltip] = useState<{ visible: boolean; x: number; y: number; text: string }>({
        visible: false,
        x: 0,
        y: 0,
        text: ''
    });

    const containerRef = useRef<HTMLDivElement>(null);

    function onDocumentLoadSuccess({ numPages }: { numPages: number }) {
        setNumPages(numPages);
        setError(null);
    }

    function onDocumentLoadError(err: Error) {
        console.error("PDF Load Error:", err);
        setError("Failed to load PDF. " + err.message);
    }

    function onDocumentLoadProgress({ loaded, total }: { loaded: number; total: number }) {
        if (total > 0) {
            const percent = Math.round((loaded / total) * 100);
            setLoadingProgress(percent);
        }
    }

    // Handle Text Selection
    useEffect(() => {
        const handleMouseUp = () => {
            const selection = window.getSelection();

            // Basic validation: Check if selection exists and is not empty
            if (!selection || selection.toString().trim() === '') {
                setTooltip(prev => ({ ...prev, visible: false }));
                return;
            }

            // Check if selection is within the PDF container
            // We can check commonAncestorContainer, but for simplicity, we just check if it's visible.
            // A more robust check is to see if the selection node is inside containerRef.
            const range = selection.getRangeAt(0);
            const container = containerRef.current;

            if (container && container.contains(range.commonAncestorContainer)) {
                const rect = range.getBoundingClientRect();

                // Calculate relative position? Rect is absolute viewport coords.
                // We'll use fixed positioning for the tooltip which is easier.

                // Position above the selection
                const x = rect.left + (rect.width / 2); // Center horizontally
                const y = rect.top - 10; // Slightly above

                setTooltip({
                    visible: true,
                    x,
                    y,
                    text: selection.toString().trim()
                });
            } else {
                setTooltip(prev => ({ ...prev, visible: false }));
            }
        };

        // Also handle mousedown to clear tooltip if clicking elsewhere
        const handleMouseDown = () => {
            // Optional: Clear tooltip immediately on new click
        };

        document.addEventListener('mouseup', handleMouseUp);
        return () => {
            document.removeEventListener('mouseup', handleMouseUp);
        };
    }, []);

    const handleAddClick = (e: React.MouseEvent) => {
        e.stopPropagation();
        e.preventDefault(); // Prevent text deselection?
        if (onAddToNotes && tooltip.text) {
            onAddToNotes(tooltip.text);
            // Hide after adding
            setTooltip(prev => ({ ...prev, visible: false }));
            // Clear selection?
            window.getSelection()?.removeAllRanges();
        }
    };

    return (
        <div ref={containerRef} className="h-full w-full overflow-y-auto bg-[#1A1A1A] flex flex-col items-center p-8 gap-8 relative">
            {error && (
                <div className="text-red-400 p-4 border border-red-500/50 rounded bg-red-900/20">
                    {error}
                </div>
            )}

            <Document
                file={pdfUrl}
                onLoadSuccess={onDocumentLoadSuccess}
                onLoadError={onDocumentLoadError}
                onLoadProgress={onDocumentLoadProgress}
                loading={
                    <div className="flex flex-col items-center justify-center p-12 gap-4 h-[50vh]">
                        <div className="text-indigo-400 text-sm font-bold uppercase tracking-widest animate-pulse">
                            Loading PDF...
                        </div>
                        <div className="w-64 h-1 bg-white/10 rounded-full overflow-hidden">
                            <div
                                className="h-full bg-indigo-500 transition-all duration-300 ease-out shadow-[0_0_10px_rgba(99,102,241,0.5)]"
                                style={{ width: `${loadingProgress}%` }}
                            />
                        </div>
                        <div className="text-gray-500 text-xs font-mono">
                            {loadingProgress}%
                        </div>
                    </div>
                }
                error={
                    <div className="flex items-center justify-center p-12 text-red-400">
                        Failed to load PDF.
                    </div>
                }
            >
                {/* Render all pages properly */}
                {Array.from(new Array(numPages), (el, index) => (
                    <Page
                        key={`page_${index + 1}`}
                        pageNumber={index + 1}
                        renderAnnotationLayer={true}
                        renderTextLayer={true}
                        className={`shadow-2xl mb-8 transition-all duration-300 ${isDarkMode ? 'invert hue-rotate-180 brightness-75 contrast-125' : ''}`}
                        width={800 * scale} // Target width, can be made responsive
                        loading={<div className="h-[1000px] bg-white/5 animate-pulse mb-8" style={{ width: 800 * scale }} />}
                    />
                ))}
            </Document>

            {/* Floating Selection Tooltip */}
            {tooltip.visible && onAddToNotes && (
                <button
                    onClick={handleAddClick}
                    className="fixed z-50 bg-[#0A0A0A] border border-indigo-500/30 text-indigo-400 text-xs font-bold px-3 py-1.5 rounded-full shadow-xl flex items-center gap-1.5 animate-in fade-in zoom-in duration-200 hover:bg-indigo-600 hover:text-white transition-colors -translate-x-1/2 -translate-y-full"
                    style={{ left: tooltip.x, top: tooltip.y }}
                >
                    <Plus className="w-3.5 h-3.5" />
                    Add to Notes
                </button>
            )}
        </div>
    );
};
