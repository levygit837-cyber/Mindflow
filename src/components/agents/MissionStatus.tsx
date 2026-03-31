import { Mission } from "../../types";

interface MissionStatusProps {
    missions: Mission[];
}

const STATUS_ICONS: Record<string, string> = {
    pending: "\u25CB",       // ○
    running: "\u27F3",        // ⟳
    complete: "\u2713",       // ✓
    failed: "\u2717",         // ✗
    cancelled: "\u274C",     // ❌
};

export function renderMissionStatus(props: MissionStatusProps): string {
    if (props.missions.length === 0) return "";

    const lines = [
        "\u2500\u2500\u2500 Missions \u2500\u2500\u2500",
        ...props.missions.map(m => {
            const icon = STATUS_ICONS[m.status] || "?";
            const progress = m.progress !== undefined ? ` ${m.progress}%` : "";
            const summary = m.summary ? ` \u2192 ${m.summary}` : "";
            return `  [${m.agentName.padEnd(10)}] ${m.type}${progress}${icon}${summary}`;
        }),
    ];

    return lines.join("\n");
}