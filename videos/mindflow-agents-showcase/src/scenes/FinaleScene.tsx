import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from "remotion";
import {mix, progress} from "../lib/animation";
import {COLORS, FONTS} from "../theme";
import {AgentChip} from "../components/AgentChip";
import {PhoneFrame} from "../components/PhoneFrame";
import {PromptBubble, ResultCard, StreamingPill, ToolCallCard} from "../components/EventCards";
import {PROMPT} from "../data/timeline";

export const FinaleScene: React.FC = () => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const enter = progress(frame, 0, 30);
  const halo = interpolate(frame % 90, [0, 45, 89], [0.85, 1, 0.85], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const float = interpolate(frame % 120, [0, 60, 119], [-10, 10, -10], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const holdOpacity = progress(frame, durationInFrames - 40, 30);

  return (
    <AbsoluteFill
      style={{
        opacity: enter,
        transform: `translateY(${mix(70, 0, enter)}px)`,
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 108,
          left: 90,
          right: 90,
          display: "flex",
          flexDirection: "column",
          gap: 18,
          alignItems: "center",
          textAlign: "center",
        }}
      >
        <div
          style={{
            color: COLORS.textPrimary,
            fontFamily: FONTS.display,
            fontSize: 86,
            fontWeight: 700,
            letterSpacing: "-0.06em",
            lineHeight: 0.94,
            maxWidth: 920,
          }}
        >
          MindFlow coordena
          <br />
          agentes, contexto e execução.
        </div>
        <div
          style={{
            color: COLORS.textSecondary,
            fontFamily: FONTS.display,
            fontSize: 28,
            fontWeight: 500,
            lineHeight: 1.35,
            maxWidth: 760,
          }}
        >
          Do prompt ao resultado, tudo segue no mesmo fluxo.
        </div>
      </div>

      <div
        style={{
          position: "absolute",
          top: 420,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            position: "absolute",
            top: 260,
            width: 820,
            height: 820,
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(13,110,110,0.18), transparent 68%)",
            transform: `scale(${halo})`,
            filter: "blur(12px)",
          }}
        />

        <PhoneFrame
          style={{
            transform: `translateY(${float}px) scale(${mix(0.96, 1, enter)})`,
          }}
        >
          <AbsoluteFill style={{padding: "118px 30px 34px", display: "flex", flexDirection: "column", gap: 18}}>
            <PromptBubble label="Prompt" text={PROMPT} style={{maxWidth: 540}} />

            <div style={{display: "flex", gap: 10, flexWrap: "wrap"}}>
              <AgentChip type="orchestrator" compact active />
              <AgentChip type="analyst" compact active />
              <AgentChip type="researcher" compact active />
              <AgentChip type="coder" compact active />
            </div>

            <StreamingPill agentType="orchestrator" text="mission synced" />

            <ToolCallCard
              agentType="coder"
              toolName="execute_code"
              status="success"
              summary="Entrega pronta, validada e devolvida para o fluxo principal."
            />

            <ResultCard
              title="Resultado"
              lines={[
                "Estratégia coordenada entre especialistas",
                "Contexto preservado durante toda a execução",
                "Entrega final consolidada em um único fluxo",
              ]}
              style={{marginTop: 4}}
            />
          </AbsoluteFill>
        </PhoneFrame>
      </div>

      <div
        style={{
          position: "absolute",
          bottom: 88,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          opacity: holdOpacity,
        }}
      >
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 14,
            padding: "18px 22px",
            borderRadius: 999,
            border: "1px solid rgba(255,255,255,0.09)",
            background: "rgba(8,12,24,0.72)",
            boxShadow: "0 18px 50px rgba(0,0,0,0.28)",
          }}
        >
          <div
            style={{
              width: 14,
              height: 14,
              borderRadius: "50%",
              background: COLORS.teal,
              boxShadow: `0 0 18px ${COLORS.teal}`,
            }}
          />
          <span
            style={{
              color: COLORS.textPrimary,
              fontFamily: FONTS.display,
              fontSize: 24,
              fontWeight: 700,
              letterSpacing: "0.18em",
              textTransform: "uppercase",
            }}
          >
            MindFlow
          </span>
        </div>
      </div>
    </AbsoluteFill>
  );
};
