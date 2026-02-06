"use client";

import dynamic from "next/dynamic";
import { useGraphData } from "@/hooks/use-graph-data";
import { GraphSidebar } from "@/components/graph/graph-sidebar";

const KnowledgeSphere = dynamic(
  () => import("@/components/graph/knowledge-sphere").then((m) => m.KnowledgeSphere),
  { ssr: false }
);

export default function GraphPage() {
  const {
    graphData,
    loading,
    selectedNodeIds,
    toggleNodeSelection,
    clearSelection,
    setHoveredNode,
    getSelectedNodes,
  } = useGraphData();

  const hoveredNodeId = null; // simplified for now

  if (loading || !graphData) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        Loading graph...
      </div>
    );
  }

  if (graphData.nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        <div className="text-center">
          <p className="text-lg font-medium">No notes yet</p>
          <p className="text-sm mt-1">Create some notes to see them in the knowledge graph</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      <div className="flex-1 relative">
        <KnowledgeSphere
          graphData={graphData}
          selectedNodeIds={selectedNodeIds}
          onToggleNode={toggleNodeSelection}
          hoveredNodeId={hoveredNodeId}
          onHoverNode={setHoveredNode}
        />
      </div>
      <GraphSidebar selectedNodes={getSelectedNodes()} onClear={clearSelection} />
    </div>
  );
}
