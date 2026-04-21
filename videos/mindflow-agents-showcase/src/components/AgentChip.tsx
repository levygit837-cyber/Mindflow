import {interpolate, useCurrentFrame} from "remotion";
import {AGENTS, type AgentKey, COLORS, FONTS} from "../theme";

type AgentChipProps = {
  type: AgentKey;
  active?: boolean;
  compact?: boolean;
};

export const AgentChip: React.FC<AgentChipProps> = ({type, active = false, compact = false}) => {
  const frame = useCurrentFrame();
  const agent = AGENTS[type];

  const pulse = interpolate(frame % 45, [0, 22, 44], [0.85, 1, 0.85], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: compact ? 10 : 14,
        padding: compact ? "10px 14px" : "14px 18px",
        borderRadius: 999,
        border: `1px solid ${active ? `${agent.color}55` : COLORS.panelBorder}`,
        background: active
          ? `linear-gradient(180deg, ${agent.accent}, rgba(11, 16, 29, 0.88))`
          : "rgba(10, 14, 28, 0.6)",
        boxShadow: active ? `0 0 36px ${agent.accent}` : "none",
      }}
    >
      <div
        style={{
          width: compact ? 10 : 12,
          height: compact ? 10 : 12,
          borderRadius: "50%",
          background: agent.color,
          transform: `scale(${active ? pulse : 1})`,
          boxShadow: active ? `0 0 18px ${agent.color}` : "none",
        }}
      />
      <div style={{display: "flex", flexDirection: "column", gap: compact ? 2 : 4}}>
        <span
          style={{
            color: COLORS.textPrimary,
            fontFamily: FONTS.display,
            fontSize: compact ? 22 : 26,
            fontWeight: 700,
            letterSpacing: "-0.03em",
            lineHeight: 1,
          }}
        >
          {agent.label}
        </span>
        {!compact ? (
          <span
            style={{
              color: COLORS.textSecondary,
              fontFamily: FONTS.display,
              fontSize: 15,
              fontWeight: 500,
              letterSpacing: "0.01em",
            }}
          >
            {agent.subtitle}
          </span>
        ) : null}
      </div>
    </div>
  );
};
