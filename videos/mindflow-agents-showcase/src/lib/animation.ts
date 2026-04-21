import {Easing, interpolate} from "remotion";

export const EASE_OUT = Easing.bezier(0.16, 1, 0.3, 1);
export const EASE_IN_OUT = Easing.bezier(0.45, 0, 0.55, 1);
export const EASE_POP = Easing.bezier(0.34, 1.56, 0.64, 1);

export const progress = (
  frame: number,
  start: number,
  duration: number,
  easing: ((input: number) => number) = EASE_OUT,
) => {
  return interpolate(frame, [start, start + duration], [0, 1], {
    easing,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
};

export const exitProgress = (
  frame: number,
  totalDuration: number,
  duration: number,
  easing: ((input: number) => number) = EASE_IN_OUT,
) => {
  return progress(frame, totalDuration - duration, duration, easing);
};

export const mix = (from: number, to: number, value: number) => {
  return from + (to - from) * value;
};
