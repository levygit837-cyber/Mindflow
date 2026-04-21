import "./index.css";
import { Composition } from "remotion";
import { MindFlowAgentsVideo } from "./compositions/MindFlowAgentsVideo";
import { TOTAL_DURATION_IN_FRAMES } from "./data/timeline";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="MindFlowAgentsVideo"
        component={MindFlowAgentsVideo}
        durationInFrames={TOTAL_DURATION_IN_FRAMES}
        fps={30}
        width={1080}
        height={1920}
      />
    </>
  );
};
