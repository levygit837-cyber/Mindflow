/**
 * Chat Visualization V2 - Legacy Export
 * 
 * This file maintains backward compatibility by re-exporting from the new v2/ structure.
 * New code should import directly from './v2' instead.
 * 
 * @deprecated Use './v2' imports instead
 */

export type {
  MindflowV2AgentType,
  MindflowV2Tone,
  MindflowV2ComponentKey,
  MindflowV2AgentTheme,
  MindflowV2ComponentMapping,
} from './v2/types';

export {
  MINDFLOW_V2_AGENT_ORDER,
  MINDFLOW_V2_AGENT_THEME,
  MINDFLOW_V2_COMPONENT_MAPPING,
} from './v2/types';

export {
  resolveMindflowV2AgentType,
  getMindflowV2AgentTheme,
  resolveMindflowV2Tone,
  formatMindflowV2Duration,
  formatMindflowV2Value,
  summarizeMindflowV2Value,
} from './v2/utils';
