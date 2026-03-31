import React, { useEffect, useState } from "react";

const SPINNER_FRAMES = ["\u280B", "\u2819", "\u2839", "\u2838", "\u283C", "\u2834", "\u2836", "\u2837", "\u283F"];

interface SpinnerProps {
    color?: string;
    label?: string;
}

export function Spinner({ color, label }: SpinnerProps) {
    const [frame, setFrame] = useState(0);

    useEffect(() => {
        const interval = setInterval(() => {
            setFrame(prev => (prev + 1) % SPINNER_FRAMES.length);
        }, 80);
        return () => clearInterval(interval);
    }, []);

    return (
        <span style={{ color }}>
            {SPINNER_FRAMES[frame]}
            {label && ` ${label}`}
        </span>
    );
}

interface ThinkingIndicatorProps {
    agentName?: string;
    operation?: string;
}

export function ThinkingIndicator({ agentName, operation }: ThinkingIndicatorProps) {
    const parts = [agentName].filter(Boolean);
    if (operation) {
        parts.push("\u2192");
        parts.push(operation);
    }
    parts.push("...");
    const label = parts.join(" ");

    return <Spinner label={label} color="yellow" />;
}