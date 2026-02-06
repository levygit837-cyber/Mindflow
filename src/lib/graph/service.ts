import { listNotes, getNoteLinks } from "@/lib/notes/service";
import type { GraphData, GraphNode, GraphEdge } from "@/types/graph";

// Fibonacci sphere distribution for even spacing
function fibonacciSphere(count: number, radius: number): [number, number, number][] {
  const points: [number, number, number][] = [];
  const goldenAngle = Math.PI * (3 - Math.sqrt(5));

  for (let i = 0; i < count; i++) {
    const y = 1 - (i / (count - 1 || 1)) * 2; // -1 to 1
    const radiusAtY = Math.sqrt(1 - y * y);
    const theta = goldenAngle * i;

    const x = Math.cos(theta) * radiusAtY;
    const z = Math.sin(theta) * radiusAtY;

    // Scale to fit inside sphere (leave some margin)
    const scale = radius * 0.85;
    points.push([x * scale, y * scale, z * scale]);
  }

  return points;
}

export function buildGraphData(): GraphData {
  const notes = listNotes({ limit: 500 });
  const links = getNoteLinks();

  const positions = fibonacciSphere(notes.length, 5);

  const nodes: GraphNode[] = notes.map((note, i) => ({
    id: note.id,
    title: note.title,
    emoji: note.emoji,
    tags: note.tags,
    color: note.color,
    position: positions[i] || [0, 0, 0],
    wordCount: note.wordCount,
  }));

  const edges: GraphEdge[] = links.map((link) => ({
    id: link.id,
    sourceId: link.sourceId,
    targetId: link.targetId,
    label: link.label,
  }));

  return { nodes, edges };
}
