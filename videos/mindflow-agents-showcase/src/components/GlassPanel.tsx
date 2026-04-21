import type {CSSProperties, ReactNode} from "react";
import {COLORS, SHADOWS} from "../theme";

type GlassPanelProps = {
  children: ReactNode;
  style?: CSSProperties;
  glowColor?: string;
  padding?: number;
  radius?: number;
};

export const GlassPanel: React.FC<GlassPanelProps> = ({
  children,
  style,
  glowColor = "rgba(255,255,255,0.08)",
  padding = 24,
  radius = 28,
}) => {
  return (
    <div
      style={{
        position: "relative",
        borderRadius: radius,
        padding,
        overflow: "hidden",
        background: `linear-gradient(180deg, rgba(255,255,255,0.08), ${COLORS.panel})`,
        border: `1px solid ${COLORS.panelBorder}`,
        boxShadow: `${SHADOWS.panel}, 0 0 0 1px rgba(255,255,255,0.03) inset, 0 0 90px ${glowColor}`,
        backdropFilter: "blur(28px)",
        ...style,
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: "linear-gradient(120deg, rgba(255,255,255,0.08), transparent 36%)",
          pointerEvents: "none",
        }}
      />
      <div style={{position: "relative", width: "100%", height: "100%"}}>{children}</div>
    </div>
  );
};
