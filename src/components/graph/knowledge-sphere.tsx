"use client";

import { useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import { NoteNode } from "./note-node";
import { Connections } from "./connections";
import type { GraphData, GraphNode } from "@/types/graph";

interface SceneProps {
  graphData: GraphData;
  selectedNodeIds: Set<string>;
  onToggleNode: (nodeId: string) => void;
  hoveredNodeId: string | null;
  onHoverNode: (nodeId: string | null) => void;
}

function RotatingGroup({ children }: { children: React.ReactNode }) {
  const groupRef = useRef<THREE.Group>(null);

  useFrame((_, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.05;
      groupRef.current.rotation.x = Math.sin(Date.now() * 0.0003) * 0.05;
    }
  });

  return <group ref={groupRef}>{children}</group>;
}

function WireframeSphere() {
  return (
    <mesh>
      <sphereGeometry args={[5, 32, 32]} />
      <meshBasicMaterial color="#334155" wireframe transparent opacity={0.15} />
    </mesh>
  );
}

function Scene({ graphData, selectedNodeIds, onToggleNode, hoveredNodeId, onHoverNode }: SceneProps) {
  const selectedNodes = graphData.nodes.filter((n) => selectedNodeIds.has(n.id));

  return (
    <>
      <ambientLight intensity={0.4} />
      <pointLight position={[10, 10, 10]} intensity={0.8} />
      <pointLight position={[-10, -10, -10]} intensity={0.3} />

      <RotatingGroup>
        <WireframeSphere />
        {graphData.nodes.map((node) => (
          <NoteNode
            key={node.id}
            node={node}
            isSelected={selectedNodeIds.has(node.id)}
            isHovered={hoveredNodeId === node.id}
            onClick={() => onToggleNode(node.id)}
            onHover={(hovered) => onHoverNode(hovered ? node.id : null)}
          />
        ))}
        <Connections selectedNodes={selectedNodes} />
      </RotatingGroup>

      <OrbitControls
        autoRotate={false}
        enableDamping
        dampingFactor={0.05}
        minDistance={3}
        maxDistance={20}
      />
    </>
  );
}

interface KnowledgeSphereProps {
  graphData: GraphData;
  selectedNodeIds: Set<string>;
  onToggleNode: (nodeId: string) => void;
  hoveredNodeId: string | null;
  onHoverNode: (nodeId: string | null) => void;
}

export function KnowledgeSphere(props: KnowledgeSphereProps) {
  return (
    <Canvas camera={{ position: [0, 0, 12], fov: 50 }} style={{ background: "transparent" }}>
      <Scene {...props} />
    </Canvas>
  );
}
