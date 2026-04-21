import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from "remotion";
import {exitProgress, mix, progress} from "../lib/animation";
import {AGENTS, COLORS, FONTS} from "../theme";
import {AgentChip} from "../components/AgentChip";
import {GlassPanel} from "../components/GlassPanel";
import {PhoneFrame} from "../components/PhoneFrame";

type LineSpec = {
  key: "analyst" | "researcher" | "coder";
  x2: number;
  y2: number;
};

const lines: LineSpec[] = [
  {key: "analyst", x2: 146, y2: 910},
  {key: "researcher", x2: 520, y2: 900},
  {key: "coder", x2: 336, y2: 1088},
];

export const DelegationScene: React.FC = () => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const enter = progress(frame, 0, 24);
  const exit = exitProgress(frame, durationInFrames, 28);
  const networkProgress = progress(frame, 20, 90);
  const chipReveal = progress(frame, 48, 44);
  const pulseTravel = progress(frame, 80, 70);

  const sceneOpacity = enter * (1 - exit * 0.9);

  return (
    <AbsoluteFill style={{opacity: sceneOpacity}}>
      <div
        style={{
          position: "absolute",
          top: 120,
          left: 90,
          right: 90,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
        }}
      >
        <div style={{maxWidth: 520}}>
          <div
            style={{
              color: COLORS.textPrimary,
              fontFamily: FONTS.display,
              fontSize: 78,
              fontWeight: 700,
              letterSpacing: "-0.06em",
              lineHeight: 0.96,
              marginBottom: 18,
            }}
          >
            O Orchestrator divide,
            <br />
            prioriza e sincroniza.
          </div>
          <div
            style={{
              color: COLORS.textSecondary,
              fontFamily: FONTS.display,
              fontSize: 28,
              fontWeight: 500,
              lineHeight: 1.36,
            }}
          >
            Cada agente recebe uma parte clara da missão. O fluxo continua conectado, sem perder o contexto.
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
          paddingTop: 160,
          transform: `translateX(78px) translateY(${mix(80, 0, enter) - exit * 50}px) scale(${mix(0.94, 1, enter)})`,
          filter: `blur(${mix(12, 0, enter)}px)`,
        }}
      >
        <PhoneFrame>
          <AbsoluteFill style={{padding: "118px 34px 40px"}}>
            <svg
              width="100%"
              height="100%"
              viewBox="0 0 622 1220"
              style={{position: "absolute", inset: 0, overflow: "visible"}}
            >
              {lines.map((line) => {
                const dashOffset = interpolate(networkProgress, [0, 1], [560, 0], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                });
                const travelX = interpolate(pulseTravel, [0, 1], [311, line.x2], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                });
                const travelY = interpolate(pulseTravel, [0, 1], [340, line.y2], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                });
                const color = AGENTS[line.key].color;

                return (
                  <g key={line.key}>
                    <line
                      x1={311}
                      y1={340}
                      x2={line.x2}
                      y2={line.y2}
                      stroke={`${color}55`}
                      strokeWidth={4}
                      strokeLinecap="round"
                      strokeDasharray="14 16"
                      strokeDashoffset={dashOffset}
                    />
                    <circle cx={travelX} cy={travelY} r={16} fill={color} opacity={0.18} />
                    <circle cx={travelX} cy={travelY} r={10} fill={color} opacity={0.36} />
                    <circle cx={travelX} cy={travelY} r={6} fill={color} />
                  </g>
                );
              })}
            </svg>

            <GlassPanel
              padding={26}
              radius={34}
              glowColor="rgba(13,110,110,0.24)"
              style={{
                position: "absolute",
                top: 180,
                left: 122,
                width: 378,
                opacity: networkProgress,
              }}
            >
              <div
                style={{
                  color: COLORS.textMuted,
                  fontFamily: FONTS.display,
                  fontSize: 14,
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "0.14em",
                  marginBottom: 14,
                }}
              >
                Mission Control
              </div>
              <AgentChip type="orchestrator" active />
              <div
                style={{
                  color: COLORS.textSecondary,
                  fontFamily: FONTS.display,
                  fontSize: 20,
                  fontWeight: 500,
                  lineHeight: 1.4,
                  marginTop: 18,
                }}
              >
                Delega análise, pesquisa e execução enquanto mantém tudo alinhado.
              </div>
            </GlassPanel>

            <div
              style={{
                position: "absolute",
                left: 18,
                top: 768,
                opacity: chipReveal,
                transform: `translateX(${mix(-50, 0, chipReveal)}px)`,
              }}
            >
              <AgentChip type="analyst" active />
            </div>
            <div
              style={{
                position: "absolute",
                right: 12,
                top: 756,
                opacity: chipReveal,
                transform: `translateX(${mix(50, 0, chipReveal)}px)`,
              }}
            >
              <AgentChip type="researcher" active />
            </div>
            <div
              style={{
                position: "absolute",
                left: 144,
                bottom: 86,
                opacity: chipReveal,
                transform: `translateY(${mix(40, 0, chipReveal)}px)`,
              }}
            >
              <AgentChip type="coder" active />
            </div>
          </AbsoluteFill>
        </PhoneFrame>
      </div>
    </AbsoluteFill>
  );
};
