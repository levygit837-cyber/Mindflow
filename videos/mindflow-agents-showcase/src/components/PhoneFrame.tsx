import type {CSSProperties, ReactNode} from "react";
import {COLORS, SHADOWS} from "../theme";

type PhoneFrameProps = {
  children: ReactNode;
  style?: CSSProperties;
};

export const PhoneFrame: React.FC<PhoneFrameProps> = ({children, style}) => {
  return (
    <div
      style={{
        position: "relative",
        width: 690,
        height: 1370,
        borderRadius: 72,
        padding: 18,
        background: "linear-gradient(180deg, rgba(28,34,56,0.94), rgba(10,12,20,0.96))",
        boxShadow: SHADOWS.phone,
        ...style,
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 22,
          left: "50%",
          width: 240,
          height: 42,
          borderRadius: 999,
          background: "rgba(3, 5, 12, 0.92)",
          transform: "translateX(-50%)",
          zIndex: 10,
        }}
      />
      <div
        style={{
          position: "relative",
          width: "100%",
          height: "100%",
          overflow: "hidden",
          borderRadius: 56,
          background: `linear-gradient(180deg, rgba(10,16,29,0.98), ${COLORS.backgroundSoft})`,
          border: "1px solid rgba(255,255,255,0.05)",
        }}
      >
        {children}
      </div>
    </div>
  );
};
