import type {CSSProperties} from "react";
import {interpolate, useCurrentFrame} from "remotion";
import {AGENTS, type AgentKey, COLORS, FONTS} from "../theme";
import {GlassPanel} from "./GlassPanel";

type PromptBubbleProps = {
  label: string;
  text: string;
  align?: "left" | "right";
  style?: CSSProperties;
};

export const PromptBubble: React.FC<PromptBubbleProps> = ({
  label,
  text,
  align = "right",
  style,
}) => {
  const bubbleColor = align === "right" ? "rgba(91, 106, 191, 0.22)" : "rgba(255,255,255,0.08)";

  return (
    <div
      style={{
        alignSelf: align === "right" ? "flex-end" : "flex-start",
        maxWidth: 460,
        borderRadius: 28,
        padding: "22px 24px",
        background: `linear-gradient(180deg, ${bubbleColor}, rgba(14,20,37,0.9))`,
        border: `1px solid ${align === "right" ? "rgba(91,106,191,0.34)" : COLORS.panelBorder}`,
        boxShadow: "0 16px 50px rgba(0,0,0,0.24)",
        ...style,
      }}
    >
      <div
        style={{
          color: COLORS.textMuted,
          fontFamily: FONTS.display,
          fontSize: 14,
          fontWeight: 600,
          letterSpacing: "0.12em",
          textTransform: "uppercase",
          marginBottom: 12,
        }}
      >
        {label}
      </div>
      <div
        style={{
          color: COLORS.textPrimary,
          fontFamily: FONTS.display,
          fontSize: 28,
          fontWeight: 500,
          lineHeight: 1.28,
          letterSpacing: "-0.03em",
        }}
      >
        {text}
      </div>
    </div>
  );
};

type StreamingPillProps = {
  agentType: AgentKey;
  text: string;
  style?: CSSProperties;
};

export const StreamingPill: React.FC<StreamingPillProps> = ({agentType, text, style}) => {
  const frame = useCurrentFrame();
  const agent = AGENTS[agentType];
  const waveA = interpolate(frame % 36, [0, 18, 35], [0.4, 1, 0.4], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const waveB = interpolate((frame + 10) % 36, [0, 18, 35], [0.4, 1, 0.4], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const waveC = interpolate((frame + 20) % 36, [0, 18, 35], [0.4, 1, 0.4], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 14,
        padding: "14px 18px",
        borderRadius: 999,
        border: `1px solid ${agent.color}44`,
        background: `linear-gradient(180deg, ${agent.accent}, rgba(11,16,29,0.94))`,
        ...style,
      }}
    >
      <div style={{display: "flex", gap: 8}}>
        {[waveA, waveB, waveC].map((value, index) => (
          <span
            key={index}
            style={{
              width: 10,
              height: 10,
              borderRadius: "50%",
              background: agent.color,
              opacity: value,
              transform: `scale(${0.8 + value * 0.4})`,
              boxShadow: `0 0 18px ${agent.color}`,
            }}
          />
        ))}
      </div>
      <span
        style={{
          color: agent.color,
          fontFamily: FONTS.display,
          fontSize: 18,
          fontWeight: 700,
          letterSpacing: "0.14em",
          textTransform: "uppercase",
        }}
      >
        {text}
      </span>
    </div>
  );
};

type ToolCallCardProps = {
  agentType: AgentKey;
  toolName: string;
  status: "running" | "success" | "queued";
  summary: string;
  style?: CSSProperties;
};

export const ToolCallCard: React.FC<ToolCallCardProps> = ({
  agentType,
  toolName,
  status,
  summary,
  style,
}) => {
  const agent = AGENTS[agentType];
  const statusLabel = {
    running: "running",
    success: "success",
    queued: "queued",
  }[status];

  const statusColor = {
    running: agent.color,
    success: COLORS.success,
    queued: COLORS.warning,
  }[status];

  return (
    <GlassPanel
      padding={18}
      radius={24}
      glowColor={agent.accent}
      style={{
        background: "linear-gradient(180deg, rgba(255,255,255,0.06), rgba(8,12,24,0.9))",
        ...style,
      }}
    >
      <div style={{display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12}}>
        <div style={{display: "flex", alignItems: "center", gap: 12}}>
          <div
            style={{
              width: 14,
              height: 14,
              borderRadius: "50%",
              background: agent.color,
              boxShadow: `0 0 16px ${agent.color}`,
            }}
          />
          <span
            style={{
              color: COLORS.textPrimary,
              fontFamily: FONTS.display,
              fontSize: 20,
              fontWeight: 700,
            }}
          >
            {toolName}
          </span>
        </div>
        <span
          style={{
            color: statusColor,
            border: `1px solid ${statusColor}55`,
            background: `${statusColor}18`,
            borderRadius: 999,
            padding: "6px 10px",
            fontFamily: FONTS.mono,
            fontSize: 12,
            fontWeight: 500,
            letterSpacing: "0.12em",
            textTransform: "uppercase",
          }}
        >
          {statusLabel}
        </span>
      </div>
      <div
        style={{
          color: COLORS.textSecondary,
          fontFamily: FONTS.display,
          fontSize: 18,
          lineHeight: 1.4,
        }}
      >
        {summary}
      </div>
    </GlassPanel>
  );
};

type ResultCardProps = {
  title: string;
  lines: string[];
  style?: CSSProperties;
};

export const ResultCard: React.FC<ResultCardProps> = ({title, lines, style}) => {
  return (
    <GlassPanel
      padding={24}
      radius={28}
      glowColor="rgba(13,110,110,0.18)"
      style={{
        background: "linear-gradient(180deg, rgba(13,110,110,0.18), rgba(7,11,21,0.96))",
        ...style,
      }}
    >
      <div
        style={{
          color: COLORS.textPrimary,
          fontFamily: FONTS.display,
          fontSize: 28,
          fontWeight: 700,
          letterSpacing: "-0.04em",
          marginBottom: 14,
        }}
      >
        {title}
      </div>
      <div style={{display: "flex", flexDirection: "column", gap: 10}}>
        {lines.map((line) => (
          <div
            key={line}
            style={{
              color: COLORS.textSecondary,
              fontFamily: FONTS.display,
              fontSize: 20,
              fontWeight: 500,
              lineHeight: 1.35,
            }}
          >
            {line}
          </div>
        ))}
      </div>
    </GlassPanel>
  );
};
