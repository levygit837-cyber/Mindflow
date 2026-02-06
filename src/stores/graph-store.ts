import { create } from "zustand";
import type { GraphData, GraphNode } from "@/types/graph";

interface GraphStore {
  graphData: GraphData | null;
  selectedNodeIds: Set<string>;
  hoveredNodeId: string | null;
  loading: boolean;
  fetchGraphData: () => Promise<void>;
  toggleNodeSelection: (nodeId: string) => void;
  clearSelection: () => void;
  setHoveredNode: (nodeId: string | null) => void;
  getSelectedNodes: () => GraphNode[];
}

export const useGraphStore = create<GraphStore>((set, get) => ({
  graphData: null,
  selectedNodeIds: new Set(),
  hoveredNodeId: null,
  loading: false,

  fetchGraphData: async () => {
    set({ loading: true });
    const res = await fetch("/api/graph");
    const data = await res.json();
    set({ graphData: data, loading: false });
  },

  toggleNodeSelection: (nodeId: string) => {
    set((state) => {
      const newSet = new Set(state.selectedNodeIds);
      if (newSet.has(nodeId)) {
        newSet.delete(nodeId);
      } else {
        newSet.add(nodeId);
      }
      return { selectedNodeIds: newSet };
    });
  },

  clearSelection: () => set({ selectedNodeIds: new Set() }),

  setHoveredNode: (nodeId) => set({ hoveredNodeId: nodeId }),

  getSelectedNodes: () => {
    const { graphData, selectedNodeIds } = get();
    if (!graphData) return [];
    return graphData.nodes.filter((n) => selectedNodeIds.has(n.id));
  },
}));
