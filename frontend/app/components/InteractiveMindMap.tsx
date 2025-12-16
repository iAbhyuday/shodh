"use client";
import React, { useCallback, useEffect } from 'react';
import {
    ReactFlow,
    Background,
    Controls,
    useNodesState,
    useEdgesState,
    Position,
    MarkerType,
    ReactFlowProvider,
    useReactFlow,
    Handle,
    BackgroundVariant
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from 'dagre';

// Types for our hierarchical JSON
type MindMapNode = {
    id: string;
    label: string;
    children?: MindMapNode[];
};

interface InteractiveMindMapProps {
    data: MindMapNode;
}

const nodeWidth = 250;
const nodeHeight = 120;

// Custom Node Component for "NotebookLM" feel
// Custom Node Component for "NotebookLM" feel
const MindMapNodeComponent = ({ data }: any) => {
    return (
        <div className="relative group w-[250px]">
            {/* Gradient Border Layer */}
            <div
                className={`rounded-xl p-[1px] bg-gradient-to-br from-white/30 via-white/10 to-transparent transition-all duration-300 ${data.hasChildren ? 'group-hover:from-blue-400 group-hover:to-blue-900 cursor-pointer' : 'cursor-default'}`}
            >
                {/* Inner Content Layer */}
                <div className="bg-neutral-900 rounded-xl px-4 py-3 h-full relative z-10">
                    {/* Hidden handles for connected look */}
                    <Handle type="target" position={Position.Left} className="w-1 h-1 !bg-transparent !border-none" />

                    <div className="flex justify-between items-start gap-2">
                        <div className="font-medium text-sm leading-snug break-words whitespace-normal text-gray-100">{data.label}</div>
                        {data.hasChildren && (
                            <span className={`text-xs mt-1 transition-colors ${data.hasChildren ? 'group-hover:text-blue-300 text-neutral-400' : 'text-neutral-500'}`}>
                                {data.isExpanded ? '−' : '+'}
                            </span>
                        )}
                    </div>

                    <Handle type="source" position={Position.Right} className="w-1 h-1 !bg-transparent !border-none" />
                </div>
            </div>
        </div>
    );
};
const nodeTypes = { mindmap: MindMapNodeComponent };

// Layout function using Dagre
const getLayoutedElements = (nodes: any[], edges: any[], direction = 'LR') => {
    const dagreGraph = new dagre.graphlib.Graph();
    dagreGraph.setDefaultEdgeLabel(() => ({}));

    // Increased separation for cleaner layout
    dagreGraph.setGraph({ rankdir: direction, ranksep: 100, nodesep: 30 });

    nodes.forEach((node) => {
        dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
    });

    edges.forEach((edge) => {
        dagreGraph.setEdge(edge.source, edge.target);
    });

    dagre.layout(dagreGraph);

    const layoutedNodes = nodes.map((node) => {
        const nodeWithPosition = dagreGraph.node(node.id);
        return {
            ...node,
            targetPosition: direction === 'LR' ? Position.Left : Position.Top,
            sourcePosition: direction === 'LR' ? Position.Right : Position.Bottom,
            position: {
                x: nodeWithPosition.x - nodeWidth / 2,
                y: nodeWithPosition.y - nodeHeight / 2,
            },
        };
    });

    return { nodes: layoutedNodes, edges };
};

// Flatten JSON to Nodes/Edges
const processData = (root: MindMapNode) => {
    const nodes: any[] = [];
    const edges: any[] = [];

    // Check for empty data
    if (!root || !root.id) return { nodes: [], edges: [] };

    const traverse = (node: MindMapNode, parentId?: string) => {
        nodes.push({
            id: node.id,
            type: 'mindmap', // Use our custom component
            data: { label: node.label },
            position: { x: 0, y: 0 },
        });

        if (parentId) {
            edges.push({
                id: `e-${parentId}-${node.id}`,
                source: parentId,
                target: node.id,
                type: 'default', // Bezier is default
                style: { stroke: '#52525b', strokeWidth: 2 },
            });
        }

        if (node.children) {
            node.children.forEach(child => traverse(child, node.id));
        }
    };

    traverse(root);
    return { nodes, edges };
};

// Inner component to access ReactFlow hooks
const Flow = ({ data }: InteractiveMindMapProps) => {
    const [nodes, setNodes, onNodesChange] = useNodesState<any>([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState<any>([]);
    const { fitView } = useReactFlow();

    // State to track expanded nodes
    const [expandedIds, setExpandedIds] = React.useState<Set<string>>(new Set(['root']));

    // Recalculate visible graph when data or expanded state changes
    useEffect(() => {
        if (!data) return;

        // 1. Traverse and filter based on expansion (Re-run every time to get current structure)
        const visibleNodes: any[] = [];
        const visibleEdges: any[] = [];

        const traverse = (node: MindMapNode, parentId?: string) => {
            // Add node
            visibleNodes.push({
                id: node.id,
                type: 'mindmap',
                data: {
                    label: node.label,
                    hasChildren: !!node.children?.length,
                    isExpanded: expandedIds.has(node.id)
                },
                position: { x: 0, y: 0 },
            });

            // Add edge from parent
            if (parentId) {
                visibleEdges.push({
                    id: `e-${parentId}-${node.id}`,
                    source: parentId,
                    target: node.id,
                    type: 'default',
                    style: { stroke: '#52525b', strokeWidth: 2 },
                });
            }

            // Recurse ONLY if expanded
            if (expandedIds.has(node.id) && node.children) {
                node.children.forEach(child => traverse(child, node.id));
            }
        };

        traverse(data);

        // 2. Compute Layout for visible elements
        const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
            visibleNodes,
            visibleEdges
        );

        setNodes(layoutedNodes);
        setEdges(layoutedEdges);

        // Fit view nicely on every layout change (expansion)
        // Using a timeout to ensure nodes are rendered
        setTimeout(() => {
            window.requestAnimationFrame(() => {
                fitView({ padding: 0.2, duration: 500 });
            });
        }, 50);

    }, [data, expandedIds, fitView, setNodes, setEdges]);

    // Reset expansion when data changes (new paper)
    useEffect(() => {
        setExpandedIds(new Set(['root']));
    }, [data]);

    const onNodeClick = useCallback((event: any, node: any) => {
        if (!node.data.hasChildren) return;

        setExpandedIds(prev => {
            const next = new Set(prev);
            if (next.has(node.id)) {
                next.delete(node.id);
            } else {
                next.add(node.id);
            }
            return next;
        });
    }, []);

    return (
        <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            nodeTypes={nodeTypes}
            minZoom={0.1}
            maxZoom={4}
            nodesDraggable={true}
            nodesConnectable={false}
            style={{ backgroundColor: '#000000' }}
            proOptions={{ hideAttribution: true }}
        >
            <Background color="#71717a" gap={20} size={1} variant={BackgroundVariant.Dots} />
            <Controls className="!bg-black/50 !border-white/10 !fill-white" />
        </ReactFlow>
    );
};

// Export wrapped component
const InteractiveMindMap: React.FC<InteractiveMindMapProps> = (props) => {
    return (
        <div className="w-full bg-black rounded-xl overflow-hidden border border-white/5 shadow-inner" style={{ width: '100%', height: '600px' }}>
            <ReactFlowProvider>
                <Flow {...props} />
            </ReactFlowProvider>
        </div>
    );
};

export default InteractiveMindMap;
