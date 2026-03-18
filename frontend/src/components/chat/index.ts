// Export V2 components as the default chat visualization system
export * from './v2';

// Export streamPresentation utilities (used by V2)
export { buildStreamPresentation, getMindflowV2ElapsedLabel } from './streamPresentation';
export type { StreamPresentation, StreamError } from './streamPresentation';

// Export shared components still used by V2 (from streamComponents.tsx)
export { StreamNotifier, ChatDiagnostic, DiagnosticNotifier } from './streamComponents';
export type { StreamNotifierProps, ChatDiagnosticProps, DiagnosticNotifierProps } from './streamComponents';

// Legacy exports for backward compatibility (deprecated)
export * from './mindflowV2';
