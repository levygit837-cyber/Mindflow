"use client";

import { useEffect } from "react";
import { useGraphStore } from "@/stores/graph-store";

export function useGraphData() {
  const { graphData, loading, fetchGraphData, selectedNodeIds, toggleNodeSelection, clearSelection, setHoveredNode, getSelectedNodes } = useGraphStore();

  useEffect(() => {
    fetchGraphData();
  }, [fetchGraphData]);

  return {
    graphData,
    loading,
    selectedNodeIds,
    toggleNodeSelection,
    clearSelection,
    setHoveredNode,
    getSelectedNodes,
    refetch: fetchGraphData,
  };
}
