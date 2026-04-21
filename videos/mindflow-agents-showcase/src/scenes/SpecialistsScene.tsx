import {AbsoluteFill, useCurrentFrame, useVideoConfig} from "remotion";
import {exitProgress, mix, progress} from "../lib/animation";
import {COLORS, FONTS} from "../theme";
import {AgentChip} from "../components/AgentChip";
import {GlassPanel} from "../components/GlassPanel";
import {StreamingPill} from "../components/EventCards";

const lines = {
  analyst: ["Quebra o pedido em etapas", "Define prioridades", "Mapeia riscos"],
  researcher: ["Recupera contexto", "Cruza referências", "Entrega sinais úteis"],
  coder: ["Abre a trilha de execução", "Gera patch incremental", "Valida o resultado"],
};

export const SpecialistsScene: React.FC = () => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();

  const enter = progress(frame, 0, 26);
  const exit = exitProgress(frame, durationInFrames, 26);
  const analystEnter = progress(frame, 12, 32);
  const researcherEnter = progress(frame, 26, 32);
  const coderEnter = progress(frame, 42, 36);

  const sceneOpacity = enter * (1 - exit * 0.92);
  const sceneScale = mix(0.96, 1, enter) - exit * 0.04;

  return (
    <AbsoluteFill
      style={{
        opacity: sceneOpacity,
        transform: `scale(${sceneScale})`,
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 118,
          left: 90,
          right: 90,
        }}
      >
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
          Especialistas trabalham
          <br />
          em paralelo.
        </div>
        <div
          style={{
            color: COLORS.textSecondary,
            fontFamily: FONTS.display,
            fontSize: 28,
            fontWeight: 500,
            lineHeight: 1.35,
            maxWidth: 640,
          }}
        >
          O sistema distribui a missão sem parar o fluxo. Cada agente avança numa frente diferente.
        </div>
      </div>

      <div
        style={{
          position: "absolute",
          top: 470,
          left: 78,
          right: 78,
          display: "flex",
          flexDirection: "column",
          gap: 26,
        }}
      >
        <GlassPanel
          padding={24}
          radius={30}
          glowColor="rgba(91,106,191,0.2)"
          style={{
            opacity: analystEnter,
            transform: `translateX(${mix(-80, 0, analystEnter)}px)`,
            filter: `blur(${mix(18, 0, analystEnter)}px)`,
          }}
        >
          <AgentChip type="analyst" active />
          <div style={{display: "flex", flexDirection: "column", gap: 10, marginTop: 20}}>
            {lines.analyst.map((line) => (
              <div
                key={line}
                style={{
                  color: COLORS.textSecondary,
                  fontFamily: FONTS.display,
                  fontSize: 22,
                  fontWeight: 500,
                }}
              >
                {line}
              </div>
            ))}
          </div>
        </GlassPanel>

        <GlassPanel
          padding={24}
          radius={30}
          glowColor="rgba(45,143,94,0.18)"
          style={{
            width: 860,
            alignSelf: "flex-end",
            opacity: researcherEnter,
            transform: `translateX(${mix(90, 0, researcherEnter)}px)`,
            filter: `blur(${mix(18, 0, researcherEnter)}px)`,
          }}
        >
          <AgentChip type="researcher" active />
          <div style={{display: "flex", flexDirection: "column", gap: 10, marginTop: 20}}>
            {lines.researcher.map((line) => (
              <div
                key={line}
                style={{
                  color: COLORS.textSecondary,
                  fontFamily: FONTS.display,
                  fontSize: 22,
                  fontWeight: 500,
                }}
              >
                {line}
              </div>
            ))}
          </div>
        </GlassPanel>

        <GlassPanel
          padding={24}
          radius={30}
          glowColor="rgba(199,93,44,0.18)"
          style={{
            opacity: coderEnter,
            transform: `translateY(${mix(70, 0, coderEnter)}px)`,
            filter: `blur(${mix(20, 0, coderEnter)}px)`,
          }}
        >
          <div style={{display: "flex", justifyContent: "space-between", alignItems: "center"}}>
            <AgentChip type="coder" active />
            <StreamingPill agentType="coder" text="streaming" />
          </div>
          <div style={{display: "flex", flexDirection: "column", gap: 10, marginTop: 20}}>
            {lines.coder.map((line) => (
              <div
                key={line}
                style={{
                  color: COLORS.textSecondary,
                  fontFamily: FONTS.display,
                  fontSize: 22,
                  fontWeight: 500,
                }}
              >
                {line}
              </div>
            ))}
          </div>
        </GlassPanel>
      </div>
    </AbsoluteFill>
  );
};
