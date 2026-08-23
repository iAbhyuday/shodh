'use client';

import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';

export interface Citation {
    index?: number;
    paper_id?: string;
    title?: string;
    section?: string;
    content?: string;
    page_number?: number | null;
    score?: number;
}

/** Short label for a chip: the paper's title, trimmed to stay inline-friendly. */
function sourceLabel(cit?: Citation): string {
    if (!cit) return 'Source';
    const raw = cit.title || cit.paper_id || 'Source';
    return raw.length > 28 ? `${raw.slice(0, 27)}…` : raw;
}

/** Initials shown in the chip's avatar circle. */
function sourceInitial(cit?: Citation): string {
    const raw = (cit?.title || cit?.paper_id || '?').trim();
    return raw.charAt(0).toUpperCase() || '?';
}

/**
 * One inline citation chip: avatar + source name (+N when a single claim is
 * backed by several passages). Click toggles the supporting snippets.
 */
const CitationChip: React.FC<{ citations: Citation[] }> = ({ citations }) => {
    const [open, setOpen] = useState(false);
    const primary = citations[0];
    const extra = citations.length - 1;

    return (
        <span className="relative inline-block align-baseline">
            <button
                type="button"
                onClick={() => setOpen(!open)}
                aria-expanded={open}
                aria-label={`Source: ${sourceLabel(primary)}${extra > 0 ? ` and ${extra} more` : ''}`}
                className="mx-1 inline-flex items-center gap-1.5 rounded-full bg-white/10 hover:bg-white/20 border border-white/10 pl-1 pr-2.5 py-0.5 align-middle transition-colors cursor-pointer"
            >
                <span className="flex h-4 w-4 items-center justify-center rounded-full bg-neutral-900 text-[9px] font-bold text-gray-300 ring-1 ring-white/20">
                    {sourceInitial(primary)}
                </span>
                <span className="text-[11px] font-medium text-gray-300 whitespace-nowrap">
                    {sourceLabel(primary)}
                    {extra > 0 && <span className="text-gray-500"> +{extra}</span>}
                </span>
            </button>

            {open && (
                <span className="absolute left-0 top-full z-20 mt-1 block w-[min(26rem,80vw)] rounded-xl border border-white/10 bg-neutral-900 p-3 shadow-2xl">
                    {citations.map((cit, i) => (
                        <span key={i} className="mb-3 block last:mb-0">
                            <span className="mb-1 flex items-center justify-between gap-2">
                                <span className="truncate text-[11px] font-semibold text-blue-400">
                                    {cit.title || cit.paper_id}
                                </span>
                                {cit.section && cit.section.toLowerCase() !== 'unknown' && (
                                    <span className="shrink-0 rounded bg-white/10 px-1.5 py-0.5 text-[9px] uppercase tracking-wide text-gray-400">
                                        {cit.section}
                                    </span>
                                )}
                            </span>
                            <span className="block max-h-32 overflow-y-auto text-[11px] leading-relaxed text-gray-400">
                                {cit.content}
                            </span>
                        </span>
                    ))}
                </span>
            )}
        </span>
    );
};

/**
 * Renders assistant markdown, replacing inline [n] / [n][m] citation markers
 * with source chips resolved against `citations`.
 *
 * Markers are rewritten to a private-use placeholder before markdown parsing so
 * they survive as text nodes, then swapped for chips during rendering.
 */
const MARKER = /\[(\d+)\](?:\s*\[(\d+)\])*/g;
const PLACEHOLDER_OPEN = '';
const PLACEHOLDER_CLOSE = '';

export const CitedMarkdown: React.FC<{ content: string; citations?: Citation[] }> = ({
    content,
    citations = [],
}) => {
    const byIndex = new Map<number, Citation>();
    citations.forEach((c, i) => byIndex.set(c.index ?? i + 1, c));

    // No sources to resolve against: render plain markdown untouched.
    if (byIndex.size === 0) {
        return <ReactMarkdown>{content}</ReactMarkdown>;
    }

    const encoded = content.replace(MARKER, (match) => {
        const nums = Array.from(match.matchAll(/\d+/g)).map((m) => Number(m[0]));
        const known = nums.filter((n) => byIndex.has(n));
        // Leave unknown markers as literal text rather than inventing a source.
        if (known.length === 0) return match;
        return `${PLACEHOLDER_OPEN}${known.join(',')}${PLACEHOLDER_CLOSE}`;
    });

    const renderWithChips = (node: React.ReactNode): React.ReactNode => {
        if (typeof node === 'string') {
            if (!node.includes(PLACEHOLDER_OPEN)) return node;
            const parts = node.split(new RegExp(`${PLACEHOLDER_OPEN}([\\d,]+)${PLACEHOLDER_CLOSE}`, 'g'));
            return parts.map((part, i) => {
                // Odd indices are the captured marker groups.
                if (i % 2 === 1) {
                    const cits = part
                        .split(',')
                        .map((n) => byIndex.get(Number(n)))
                        .filter(Boolean) as Citation[];
                    return <CitationChip key={i} citations={cits} />;
                }
                return <React.Fragment key={i}>{part}</React.Fragment>;
            });
        }
        if (Array.isArray(node)) {
            return (node as React.ReactNode[]).map((n: React.ReactNode, i: number) => (
                <React.Fragment key={i}>{renderWithChips(n)}</React.Fragment>
            ));
        }
        return node;
    };

    const withChips = (props: { children?: React.ReactNode }) => renderWithChips(props.children);

    return (
        <ReactMarkdown
            components={{
                p: ({ children }) => <p>{renderWithChips(children)}</p>,
                li: ({ children }) => <li>{renderWithChips(children)}</li>,
                td: ({ children }) => <td>{renderWithChips(children)}</td>,
                strong: ({ children }) => <strong>{withChips({ children })}</strong>,
                em: ({ children }) => <em>{withChips({ children })}</em>,
            }}
        >
            {encoded}
        </ReactMarkdown>
    );
};

/**
 * Collapsed-by-default source list shown under an answer.
 *
 * The inline chips are the primary citation affordance; this is the "show your
 * work" backup, so it stays out of the way until asked for. Rendering it
 * expanded pushes the answer off-screen and reads as noise.
 */
export const SourceList: React.FC<{ citations?: Citation[]; accent?: string }> = ({
    citations = [],
    accent = 'text-blue-400',
}) => {
    const [open, setOpen] = useState(false);
    if (citations.length === 0) return null;

    return (
        <div className="mt-3 w-full border-t border-white/5 pt-2">
            <button
                type="button"
                onClick={() => setOpen(!open)}
                aria-expanded={open}
                className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wide text-gray-500 transition-colors hover:text-gray-300"
            >
                <span className={`transition-transform ${open ? 'rotate-90' : ''}`}>›</span>
                {citations.length} source{citations.length === 1 ? '' : 's'}
            </button>

            {open && (
                <div className="mt-2 flex flex-col gap-1.5">
                    {citations.map((cit, i) => (
                        <div
                            key={i}
                            className="flex items-start gap-2 rounded-lg border border-white/5 bg-white/[0.03] p-2 text-xs"
                        >
                            <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-white/10 text-[9px] font-bold text-gray-300">
                                {cit.index ?? i + 1}
                            </span>
                            <div className="min-w-0 flex-1">
                                <div className="flex items-center justify-between gap-2">
                                    <span className={`truncate text-[11px] font-semibold ${accent}`}>
                                        {cit.title || cit.paper_id}
                                    </span>
                                    {/* Hide meaningless section labels rather than showing "UNKNOWN". */}
                                    {cit.section && cit.section.toLowerCase() !== 'unknown' && (
                                        <span className="shrink-0 rounded bg-white/10 px-1.5 py-0.5 text-[9px] uppercase tracking-wide text-gray-400">
                                            {cit.section}
                                        </span>
                                    )}
                                </div>
                                {cit.content && (
                                    <p className="mt-1 line-clamp-2 text-[11px] leading-relaxed text-gray-500">
                                        {cit.content}
                                    </p>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default CitedMarkdown;
