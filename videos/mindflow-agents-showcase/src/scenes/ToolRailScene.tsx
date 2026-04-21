import {AbsoluteFill, useCurrentFrame, useVideoConfig} from "remotion";
import {exitProgress, mix, progress} from "../lib/animation";
import {COLORS, FONTS} from "../theme";
import {AgentChip} from "../components/AgentChip";
import {PhoneFrame} from "../components/PhoneFrame";
import {StreamingPill, ToolCallCard} from "../components/EventCards";

export const ToolRailScene: React.FC = () => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();

  const enter = progress(frame, 0, 26);
  const exit = exitProgress(frame, durationInFrames, 28);
  const cardOne = progress(frame, 18, 28);
  const cardTwo = progress(frame, 42, 28);
  const cardThree = progress(frame, 66, 28);

  const sceneOpacity = enter * (1 - exit * 0.9);

  return (
    <AbsoluteFill style={{opacity: sceneOpacity}}>
      <div
        style={{
          position: "absolute",
          top: 118,
          left: 90,
          right: 90,
          display: "flex",
          justifyContent: "space-between",
        }}
      >
        <div style={{maxWidth: 620}}>
          <div
            style={{
              color: COLORS.textPrimary,
              fontFamily: FONTS.display,
              fontSize: 82,
              fontWeight: 700,
              letterSpacing: "-0.06em",
              lineHeight: 0.96,
              marginBottom: 18,
            }}
          >
            Ferramentas certas,
            <br />
            na ordem certa.
          </div>
          <div
            style={{
              color: COLORS.textSecondary,
              fontFamily: FONTS.display,
              fontSize: 28,
              fontWeight: 500,
              lineHeight: 1.35,
            }}
          >
            O trilho de eventos mostra quem está pensando, o que foi delegado e quais ferramentas estão em execução.
          </div>
        </div>
      </div>

      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          paddingTop: 190,
          transform: `translateX(64px) translateY(${mix(90, 0, enter) - exit * 40}px)`,
        }}
      >
        <PhoneFrame>
          <AbsoluteFill style={{padding: "118px 30px 34px", display: "flex", flexDirection: "column"}}>
            <div style={{display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 22}}>
              <StreamingPill agentType="orchestrator" text="event rail" />
              <div style={{display: "flex", gap: 10}}>
                <AgentChip type="analyst" compact active />
                <AgentChip type="researcher" compact active />
                <AgentChip type="coder" compact active />
              </div>
            </div>

            <div style={{display: "flex", flexDirection: "column", gap: 16}}>
              <ToolCallCard
                agentType="researcher"
                toolName="web_search"
                status="success"
                summary="Recupera referências e contexto relevante para a missão."
                style={{
                  opacity: cardOne,
                  transform: `translateY(${mix(70, 0, cardOne)}px)`,
                  filter: `blur(${mix(18, 0, cardOne)}px)`,
                }}
              />
              <ToolCallCard
                agentType="analyst"
                toolName="plan_graph"
                status="running"
                summary="Consolida sinais, prioridades e dependências antes da execução."
                style={{
                  opacity: cardTwo,
                  transform: `translateY(${mix(70, 0, cardTwo)}px)`,
                  filter: `blur(${mix(18, 0, cardTwo)}px)`,
                }}
              />
              <ToolCallCard
                agentType="coder"
                toolName="execute_code"
                status="running"
                summary="Abre a trilha de entrega com progresso incremental e feedback contínuo."
                style={{
                  opacity: cardThree,
                  transform: `translateY(${mix(70, 0, cardThree)}px)`,
                  filter: `blur(${mix(18, 0, cardThree)}px)`,
                }}
              />
            </div>
          </AbsoluteFill>
        </PhoneFrame>
      </div>
    </AbsoluteFill>
  );
};
