import {AbsoluteFill, Sequence} from "remotion";
import {Background} from "../components/Background";
import {SCENES} from "../data/timeline";
import {HookScene} from "../scenes/HookScene";
import {DelegationScene} from "../scenes/DelegationScene";
import {SpecialistsScene} from "../scenes/SpecialistsScene";
import {ToolRailScene} from "../scenes/ToolRailScene";
import {FinaleScene} from "../scenes/FinaleScene";

export const MindFlowAgentsVideo: React.FC = () => {
  return (
    <AbsoluteFill>
      <Background />

      <Sequence from={SCENES.hook.start} durationInFrames={SCENES.hook.duration}>
        <HookScene />
      </Sequence>

      <Sequence from={SCENES.delegation.start} durationInFrames={SCENES.delegation.duration}>
        <DelegationScene />
      </Sequence>

      <Sequence from={SCENES.specialists.start} durationInFrames={SCENES.specialists.duration}>
        <SpecialistsScene />
      </Sequence>

      <Sequence from={SCENES.toolRail.start} durationInFrames={SCENES.toolRail.duration}>
        <ToolRailScene />
      </Sequence>

      <Sequence from={SCENES.finale.start} durationInFrames={SCENES.finale.duration}>
        <FinaleScene />
      </Sequence>
    </AbsoluteFill>
  );
};
