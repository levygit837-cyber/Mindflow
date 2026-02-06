export interface GraphNode {
  id: string;
  title: string;
  emoji: string;
  tags: string[];
  color: string | null;
  position: [number, number, number];
  wordCount: number;
}

export interface GraphEdge {
  id: string;
  sourceId: string;
  targetId: string;
  label: string | null;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}
