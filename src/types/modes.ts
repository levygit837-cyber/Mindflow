/** Permission Mode Types for MindFlow. */

export type PermissionMode =
    | 'default'
    | 'accept_edits'
    | 'plan'
    | 'auto'
    | 'bypass'
    | 'dont_ask';

export interface ModeInfo {
    name: string;
    icon: string;
    color: string;
    description: string;
}

export interface ModeToggleRequest {
    session_id: string;
    direction: 'next' | 'previous' | 'direct';
    target_mode?: PermissionMode;
}

export interface ModeToggleResponse {
    old_mode: string;
    new_mode: string;
    mode_info: ModeInfo;
    success: boolean;
    message: string;
}

export interface ModeInfoResponse {
    session_id: string;
    current_mode: string;
    mode_info: ModeInfo;
    cycle_order: string[];
}