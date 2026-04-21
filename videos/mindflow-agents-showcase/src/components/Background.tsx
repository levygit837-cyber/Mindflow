import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from "remotion";
import {COLORS} from "../theme";

export const Background: React.FC = () => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();

  const drift = interpolate(frame, [0, durationInFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background: `
          radial-gradient(circle at 18% 12%, rgba(91, 106, 191, 0.22), transparent 28%),
          radial-gradient(circle at 82% 18%, rgba(13, 110, 110, 0.18), transparent 26%),
          radial-gradient(circle at 70% 80%, rgba(199, 93, 44, 0.16), transparent 24%),
          linear-gradient(180deg, #081021 0%, ${COLORS.background} 46%, #05070f 100%)
        `,
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: -200,
          backgroundImage: `
            linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px)
          `,
          backgroundSize: "120px 120px",
          transform: `translate3d(${drift * -80}px, ${drift * -40}px, 0) scale(1.06)`,
          opacity: 0.24,
        }}
      />

      <div
        style={{
          position: "absolute",
          top: 160 + drift * 40,
          left: 120 - drift * 50,
          width: 360,
          height: 360,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(91,106,191,0.34), transparent 72%)",
          filter: "blur(18px)",
        }}
      />

      <div
        style={{
          position: "absolute",
          right: 80 - drift * 35,
          bottom: 240 + drift * 45,
          width: 420,
          height: 420,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(13,110,110,0.22), transparent 72%)",
          filter: "blur(18px)",
        }}
      />

      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "linear-gradient(180deg, rgba(6,8,20,0) 0%, rgba(6,8,20,0.12) 40%, rgba(6,8,20,0.38) 100%)",
        }}
      />
    </AbsoluteFill>
  );
};
