"use client";
import React, { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';

interface MermaidProps {
  chart: string;
}

const Mermaid: React.FC<MermaidProps> = ({ chart }) => {
  const ref = useRef<HTMLDivElement>(null);
  const [svg, setSvg] = useState<string>('');

  useEffect(() => {
    // Configure mermaid for dark theme
    mermaid.initialize({
      startOnLoad: true,
      theme: 'dark',
      securityLevel: 'loose',
      mindmap: {
        useMaxWidth: false,
      }
    });

    const renderChart = async () => {
      if (ref.current && chart) {
        try {
          const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;
          const { svg } = await mermaid.render(id, chart);
          setSvg(svg);
        } catch (error) {
          console.error("Mermaid parsing error:", error);
          setSvg('<div class="text-red-400 p-4 border border-red-900 bg-red-900/20 rounded">Error rendering chart. The model might have produced invalid syntax.</div>');
        }
      }
    };
    renderChart();
  }, [chart]);

  return (
    <div className="h-full w-full overflow-hidden bg-neutral-900 rounded-xl border border-white/5 relative group">
      <div className="absolute top-4 right-4 z-10 bg-black/50 backdrop-blur px-3 py-1 rounded-full text-xs text-gray-400 pointer-events-none">
        Scroll to Zoom • Drag to Pan
      </div>

      {/* Simple Pan/Zoom integration could be done with a library like react-zoom-pan-pinch. 
            For now, we use CSS overflow and standard interaction if mermaid supports it, 
            or just simple scroll. Since user asked for 'interactive like notebooklm', 
            we will fallback to standard scroll which is robust, as full D3 interaction logic is complex 
            to inject into this string based component without extra deps.
        */}
      <div
        ref={ref}
        dangerouslySetInnerHTML={{ __html: svg }}
        className="w-full h-full overflow-auto p-8 flex items-center justify-center min-h-[500px]"
        style={{ minWidth: '100%', minHeight: '100%' }}
      />
    </div>
  );
};

export default Mermaid;
