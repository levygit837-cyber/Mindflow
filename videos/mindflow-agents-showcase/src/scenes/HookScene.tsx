import {AbsoluteFill, useCurrentFrame, useVideoConfig} from "remotion";
import {PROMPT} from "../data/timeline";
import {exitProgress, mix, progress} from "../lib/animation";
import {COLORS, FONTS} from "../theme";
import {AgentChip} from "../components/AgentChip";
import {GlassPanel} from "../components/GlassPanel";
import {PhoneFrame} from "../components/PhoneFrame";
import {PromptBubble, StreamingPill} from "../components/EventCards";

export const HookScene: React.FC = () => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();

  const enter = progress(frame, 0, 28);
  const exit = exitProgress(frame, durationInFrames, 24);
  const promptEnter = progress(frame, 12, 34);
  const cardEnter = progress(frame, 30, 36);
  const chipEnter = progress(frame, 54, 24);

  const sceneOpacity = enter * (1 - exit * 0.88);
  const sceneTranslateY = mix(60, 0, enter) - exit * 40;

  return (
    <AbsoluteFill
      style={{
        opacity: sceneOpacity,
        transform: `translateY(${sceneTranslateY}px)`,
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 120,
          left: 90,
          right: 90,
          display: "flex",
          flexDirection: "column",
          gap: 18,
        }}
      >
        <div
          style={{
            color: COLORS.textMuted,
            fontFamily: FONTS.display,
            fontSize: 24,
            fontWeight: 600,
            letterSpacing: "0.16em",
            textTransform: "uppercase",
          }}
        >
          MindFlow
        </div>
        <div
          style={{
            color: COLORS.textPrimary,
            fontFamily: FONTS.display,
            fontSize: 92,
            fontWeight: 700,
            lineHeight: 0.94,
            letterSpacing: "-0.06em",
            maxWidth: 760,
          }}
        >
          Um pedido.
          <br />
          Vários agentes.
        </div>
        <div
          style={{
            color: COLORS.textSecondary,
            fontFamily: FONTS.display,
            fontSize: 28,
            fontWeight: 500,
            maxWidth: 640,
            lineHeight: 1.35,
          }}
        >
          A interface desperta, entende a missão e começa a coordenar trabalho em tempo real.
        </div>
      </div>

      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          paddingTop: 270,
        }}
      >
        <PhoneFrame
          style={{
            transform: `translateX(48px) translateY(${mix(90, 0, enter)}px) scale(${mix(0.92, 1, enter)})`,
            filter: `blur(${mix(16, 0, enter)}px)`,
          }}
        >
          <AbsoluteFill style={{padding: "112px 34px 40px"}}>
            <div style={{display: "flex", flexDirection: "column", gap: 22}}>
              <PromptBubble
                label="Prompt"
                text={PROMPT}
                style={{
                  opacity: promptEnter,
                  transform: `translateY(${mix(80, 0, promptEnter)}px)`,
                  filter: `blur(${mix(16, 0, promptEnter)}px)`,
                }}
              />

              <GlassPanel
                padding={22}
                radius={30}
                glowColor="rgba(13,110,110,0.24)"
                style={{
                  opacity: cardEnter,
                  transform: `translateY(${mix(44, 0, cardEnter)}px) scale(${mix(0.96, 1, cardEnter)})`,
                }}
              >
                <div style={{display: "flex", alignItems: "center", justifyContent: "space-between"}}>
                  <AgentChip type="orchestrator" active compact />
                  <StreamingPill agentType="orchestrator" text="routing" />
                </div>
              </GlassPanel>

              <div
                style={{
                  display: "flex",
                  gap: 12,
                  flexWrap: "wrap",
                  opacity: chipEnter,
                  transform: `translateY(${mix(24, 0, chipEnter)}px)`,
                }}
              >
                <AgentChip type="analyst" compact />
                <AgentChip type="researcher" compact />
                <AgentChip type="coder" compact />
              </div>
            </div>
          </AbsoluteFill>
        </PhoneFrame>
      </div>

      <div
        style={{
          position: "absolute",
          bottom: 130,
          left: 90,
          color: COLORS.textMuted,
          fontFamily: FONTS.display,
          fontSize: 22,
          fontWeight: 600,
          letterSpacing: "0.12em",
          textTransform: "uppercase",
        }}
      >
        Coordenação em tempo real
      </div>
    </AbsoluteFill>
  );
};
