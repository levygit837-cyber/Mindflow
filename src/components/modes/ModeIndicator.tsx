/** Mode Indicator — Shows current permission mode in UI. */

import React from 'react';
import { PermissionMode } from '../../types/modes';

interface ModeIndicatorProps {
    currentMode: PermissionMode;
    onToggle: (direction: 'next' | 'previous') => void;
    disabled?: boolean;
}

interface ModeConfig {
    name: string;
    icon: string;
    color: string;
    description: string;
}

const MODE_CONFIG: Record<PermissionMode, ModeConfig> = {
    default: {
        name: 'Default',
        icon: '🔒',
        color: 'yellow',
        description: 'User approval required per tool',
    },
    accept_edits: {
        name: 'Accept Edits',
        icon: '✏️',
        color: 'blue',
        description: 'Allow edits in working directory',
    },
    plan: {
        name: 'Plan Mode',
        icon: '📋',
        color: 'purple',
        description: 'Read-only planning, no execution',
    },
    auto: {
        name: 'Auto Mode',
        icon: '🤖',
        color: 'green',
        description: 'Classifier decides, no user prompt',
    },
    bypass: {
        name: 'Bypass',
        icon: '⚡',
        color: 'orange',
        description: 'All tools allowed (sandbox only)',
    },
    dont_ask: {
        name: "Don't Ask",
        icon: '🚫',
        color: 'red',
        description: 'Deny tools that would prompt',
    },
};

export const ModeIndicator: React.FC<ModeIndicatorProps> = ({
    currentMode,
    onToggle,
    disabled = false,
}) => {
    const config = MODE_CONFIG[currentMode];

    return (
        <div className="mode-indicator">
            <button
                onClick={() => onToggle('previous')}
                disabled={disabled}
                className="mode-toggle-btn"
                title="Previous mode"
            >
                ◀
            </button>

            <div
                className={`mode-badge mode-${config.color}`}
                title={config.description}
            >
                <span className="mode-icon">{config.icon}</span>
                <span className="mode-name">{config.name}</span>
            </div>

            <button
                onClick={() => onToggle('next')}
                disabled={disabled}
                className="mode-toggle-btn"
                title="Next mode"
            >
                ▶
            </button>
        </div>
    );
};

export default ModeIndicator;