"use client";

import { useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";
import type { GraphNode } from "@/types/graph";

interface NoteNodeProps {
  node: GraphNode;
  isSelected: boolean;
  isHovered: boolean;
  onClick: () => void;
  onHover: (hovered: boolean) => void;
}

export function NoteNode({ node, isSelected, isHovered, onClick, onHover }: NoteNodeProps) {
  const meshRef = useRef<THREE.Mesh>(null);
  const [scale, setScale] = useState(1);

  useFrame((_, delta) => {
    if (!meshRef.current) return;

    // Animate scale
    const targetScale = isSelected ? 1.8 : isHovered ? 1.3 : 1.0;
    const newScale = THREE.MathUtils.lerp(scale, targetScale, delta * 8);
    setScale(newScale);
    meshRef.current.scale.setScalar(newScale);

    // Pulse animation for selected nodes
    if (isSelected) {
      const pulse = 1 + Math.sin(Date.now() * 0.003) * 0.1;
      meshRef.current.scale.multiplyScalar(pulse);
    }
  });

  const baseColor = node.color || "#6366f1";
  const emissiveIntensity = isSelected ? 0.8 : isHovered ? 0.3 : 0;

  return (
    <group position={node.position}>
      <mesh
        ref={meshRef}
        onClick={(e) => {
          e.stopPropagation();
          onClick();
        }}
        onPointerOver={(e) => {
          e.stopPropagation();
          onHover(true);
          document.body.style.cursor = "pointer";
        }}
        onPointerOut={() => {
          onHover(false);
          document.body.style.cursor = "auto";
        }}
      >
        <sphereGeometry args={[0.15, 16, 16]} />
        <meshStandardMaterial
          color={isSelected ? "#818cf8" : baseColor}
          emissive={isSelected ? "#818cf8" : baseColor}
          emissiveIntensity={emissiveIntensity}
          roughness={0.3}
          metalness={0.1}
        />
      </mesh>

      {(isHovered || isSelected) && (
        <Html distanceFactor={10} style={{ pointerEvents: "none" }}>
          <div className="bg-popover text-popover-foreground px-2 py-1 rounded text-xs whitespace-nowrap border shadow-md">
            {node.emoji} {node.title}
          </div>
        </Html>
      )}
    </group>
  );
}
