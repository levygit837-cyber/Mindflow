"use client";

import { Line } from "@react-three/drei";
import type { GraphNode } from "@/types/graph";

interface ConnectionsProps {
  selectedNodes: GraphNode[];
}

export function Connections({ selectedNodes }: ConnectionsProps) {
  if (selectedNodes.length < 2) return null;

  const lines: { from: [number, number, number]; to: [number, number, number] }[] = [];

  for (let i = 0; i < selectedNodes.length; i++) {
    for (let j = i + 1; j < selectedNodes.length; j++) {
      lines.push({
        from: selectedNodes[i].position,
        to: selectedNodes[j].position,
      });
    }
  }

  return (
    <>
      {lines.map((line, i) => (
        <Line
          key={i}
          points={[line.from, line.to]}
          color="#818cf8"
          lineWidth={1.5}
          dashed
          dashSize={0.2}
          gapSize={0.1}
          opacity={0.6}
          transparent
        />
      ))}
    </>
  );
}
