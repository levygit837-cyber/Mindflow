import {loadFont as loadMonoFont} from "@remotion/google-fonts/IBMPlexMono";
import {loadFont as loadDisplayFont} from "@remotion/google-fonts/SpaceGrotesk";

const {fontFamily: displayFontFamily} = loadDisplayFont("normal", {
  weights: ["400", "500", "700"],
  subsets: ["latin"],
});

const {fontFamily: monoFontFamily} = loadMonoFont("normal", {
  weights: ["400", "500"],
  subsets: ["latin"],
});

export const COLORS = {
  background: "#060814",
  backgroundSoft: "#0d1224",
  panel: "rgba(14, 20, 37, 0.72)",
  panelStrong: "rgba(18, 25, 47, 0.88)",
  panelBorder: "rgba(255, 255, 255, 0.11)",
  textPrimary: "#f6f7fb",
  textSecondary: "rgba(233, 238, 255, 0.72)",
  textMuted: "rgba(213, 219, 245, 0.42)",
  teal: "#0D6E6E",
  indigo: "#5B6ABF",
  orange: "#C75D2C",
  green: "#2D8F5E",
  success: "#56c271",
  error: "#ef6767",
  warning: "#f3b857",
  white: "#ffffff",
} as const;

export const FONTS = {
  display: `"${displayFontFamily}", sans-serif`,
  mono: `"${monoFontFamily}", monospace`,
} as const;

export const AGENTS = {
  orchestrator: {
    label: "Orchestrator",
    subtitle: "Decide e sincroniza",
    color: COLORS.teal,
    accent: "rgba(13, 110, 110, 0.22)",
  },
  analyst: {
    label: "Analyst",
    subtitle: "Estrutura a missão",
    color: COLORS.indigo,
    accent: "rgba(91, 106, 191, 0.22)",
  },
  researcher: {
    label: "Researcher",
    subtitle: "Encontra contexto",
    color: COLORS.green,
    accent: "rgba(45, 143, 94, 0.22)",
  },
  coder: {
    label: "Coder",
    subtitle: "Entrega execução",
    color: COLORS.orange,
    accent: "rgba(199, 93, 44, 0.22)",
  },
} as const;

export type AgentKey = keyof typeof AGENTS;

export const SHADOWS = {
  panel: "0 22px 80px rgba(0, 0, 0, 0.32)",
  glow: "0 0 80px rgba(91, 106, 191, 0.18)",
  phone: "0 36px 120px rgba(0, 0, 0, 0.46)",
} as const;
