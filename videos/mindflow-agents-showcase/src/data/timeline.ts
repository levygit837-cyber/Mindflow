export const FPS = 30;

export const SCENES = {
  hook: {
    start: 0,
    duration: 165,
  },
  delegation: {
    start: 165,
    duration: 210,
  },
  specialists: {
    start: 375,
    duration: 240,
  },
  toolRail: {
    start: 615,
    duration: 285,
  },
  finale: {
    start: 900,
    duration: 300,
  },
} as const;

export const TOTAL_DURATION_IN_FRAMES = 1200;

export const PROMPT =
  "Crie um fluxo de agentes para pesquisar, planejar e entregar uma solução.";
