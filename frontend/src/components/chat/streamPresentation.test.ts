import { describe, it, expect } from 'vitest';
import {
  buildStreamPresentation,
  parseStructuredStreamEventData,
  type StreamPresentation,
} from './streamPresentation';

describe('buildStreamPresentation', () => {
  describe('Infrastructure Step Filtering', () => {
    it('should filter out infrastructure steps with __ prefix', () => {
      const events = [
        { type: 'agent_step', data: '{"stepName": "__internal_route"}' },
        { type: 'agent_step', data: '{"stepName": "Business Step"}' },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.journey.steps).toHaveLength(1);
      expect(result.journey.steps[0].title).toBe('Business Step');
    });

    it('should filter out steps ending with _route', () => {
      const events = [
        { type: 'agent_step', data: '{"stepName": "orchestrator_route"}' },
        { type: 'agent_step', data: '{"stepName": "Valid Step"}' },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.journey.steps).toHaveLength(1);
      expect(result.journey.steps[0].title).toBe('Valid Step');
    });

    it('should filter out steps ending with _check', () => {
      const events = [
        { type: 'agent_step', data: '{"stepName": "validation_check"}' },
        { type: 'agent_step', data: '{"stepName": "Process Data"}' },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.journey.steps).toHaveLength(1);
      expect(result.journey.steps[0].title).toBe('Process Data');
    });

    it('should filter out analyze_request steps', () => {
      const events = [
        { type: 'agent_step', data: '{"stepName": "analyze_request"}' },
        { type: 'agent_step', data: '{"stepName": "Analyze Request"}' },
        { type: 'agent_step', data: '{"stepName": "Execute Task"}' },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.journey.steps).toHaveLength(1);
      expect(result.journey.steps[0].title).toBe('Execute Task');
    });

    it('should filter out orchestration steps', () => {
      const events = [
        { type: 'agent_step', data: '{"stepName": "orchestrator_init"}' },
        { type: 'agent_step', data: '{"stepName": "orchestrate_flow"}' },
        { type: 'agent_step', data: '{"stepName": "Real Work"}' },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.journey.steps).toHaveLength(1);
      expect(result.journey.steps[0].title).toBe('Real Work');
    });

    it('should filter out route_to steps', () => {
      const events = [
        { type: 'agent_step', data: '{"stepName": "route_to_agent"}' },
        { type: 'agent_step', data: '{"stepName": "Route To Specialist"}' },
        { type: 'agent_step', data: '{"stepName": "Business Logic"}' },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.journey.steps).toHaveLength(1);
      expect(result.journey.steps[0].title).toBe('Business Logic');
    });

    it('should filter out dispatch steps', () => {
      const events = [
        { type: 'agent_step', data: '{"stepName": "dispatch_task"}' },
        { type: 'agent_step', data: '{"stepName": "Actual Work"}' },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.journey.steps).toHaveLength(1);
      expect(result.journey.steps[0].title).toBe('Actual Work');
    });

    it('should filter out initialize steps', () => {
      const events = [
        { type: 'agent_step', data: '{"stepName": "initialize_agent"}' },
        { type: 'agent_step', data: '{"stepName": "Main Process"}' },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.journey.steps).toHaveLength(1);
      expect(result.journey.steps[0].title).toBe('Main Process');
    });

    it('should filter out direct_agent steps', () => {
      const events = [
        { type: 'agent_step', data: '{"stepName": "direct_agent:coder"}' },
        { type: 'agent_step', data: '{"stepName": "Direct Agent: Analyst"}' },
        { type: 'agent_step', data: '{"stepName": "Execute Code"}' },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.journey.steps).toHaveLength(1);
      expect(result.journey.steps[0].title).toBe('Execute Code');
    });

    it('should keep all business steps when no infrastructure steps present', () => {
      const events = [
        { type: 'agent_step', data: '{"stepName": "Analyze Data"}' },
        { type: 'agent_step', data: '{"stepName": "Process Results"}' },
        { type: 'agent_step', data: '{"stepName": "Generate Report"}' },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.journey.steps).toHaveLength(3);
      expect(result.journey.steps[0].title).toBe('Analyze Data');
      expect(result.journey.steps[1].title).toBe('Process Results');
      expect(result.journey.steps[2].title).toBe('Generate Report');
    });
  });

  describe('Notifier Deduplication', () => {
    it('should deduplicate notifiers with same title and status within 2s window', () => {
      const events = [
        { type: 'notifier', data: '{"kind": "routing", "message": "Routing request"}' },
        { type: 'notifier', data: '{"kind": "routing", "message": "Routing request"}' },
        { type: 'notifier', data: '{"kind": "routing", "message": "Routing request"}' },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.notifiers).toHaveLength(1);
      expect(result.notifiers[0].title).toBe('Routing');
    });

    it('should keep notifiers with different titles', () => {
      const events = [
        { type: 'notifier', data: '{"kind": "routing", "message": "Routing"}' },
        { type: 'notifier', data: '{"kind": "success", "message": "Success"}' },
        { type: 'notifier', data: '{"kind": "error", "message": "Error"}' },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.notifiers).toHaveLength(3);
    });

    it('should keep notifiers with same title but different status', () => {
      const events = [
        { type: 'notifier', data: '{"kind": "operation", "message": "Starting"}' },
        { type: 'notifier', data: '{"kind": "operation", "message": "Running"}' },
        { type: 'notifier', data: '{"kind": "operation", "message": "Complete"}' },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.notifiers).toHaveLength(3);
    });

    it('should apply NOTIFIER_CAP limit of 6 notifiers', () => {
      const events = Array.from({ length: 10 }, (_, i) => ({
        type: 'notifier',
        data: `{"kind": "event_${i}", "message": "Event ${i}"}`,
      }));
      const result = buildStreamPresentation(events, false);
      expect(result.notifiers).toHaveLength(6);
      // Should keep the most recent 6
      expect(result.notifiers[0].title).toBe('Event 4');
      expect(result.notifiers[5].title).toBe('Event 9');
    });

    it('should handle empty notifier data gracefully', () => {
      const events = [
        { type: 'notifier', data: '' },
        { type: 'notifier', data: '{}' },
        { type: 'notifier', data: '{"kind": "valid"}' },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.notifiers.length).toBeGreaterThanOrEqual(1);
    });
  });

  describe('Empty Events Array Handling', () => {
    it('should return default structure for empty events array', () => {
      const result = buildStreamPresentation([], false);
      expect(result.activeAgents).toEqual([]);
      expect(result.thinkingStatuses).toEqual({});
      expect(result.thoughts).toEqual([]);
      expect(result.delegations).toEqual([]);
      expect(result.toolEvents).toEqual([]);
      expect(result.notifiers).toEqual([]);
      expect(result.memoryEvents).toEqual([]);
      expect(result.journey.steps).toEqual([]);
      expect(result.errors).toEqual([]);
      expect(result.diagnostics.scopeEscape).toBe(false);
    });

    it('should add orchestrator to activeAgents when streaming with empty events', () => {
      const result = buildStreamPresentation([], true);
      expect(result.activeAgents).toEqual(['orchestrator']);
    });

    it('should not add orchestrator when not streaming with empty events', () => {
      const result = buildStreamPresentation([], false);
      expect(result.activeAgents).toEqual([]);
    });

    it('should handle journey summary with no steps', () => {
      const result = buildStreamPresentation([], false);
      expect(result.journey.summary).toBe('0 etapas · 0 agentes');
    });
  });

  describe('Error Event Parsing', () => {
    it('should parse error event with complete payload', () => {
      const events = [
        {
          type: 'error',
          id: 'err-1',
          data: '{"message": "Connection failed", "code": "ERR_CONN", "recoverable": true}',
        },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.errors).toHaveLength(1);
      expect(result.errors[0].message).toBe('Connection failed');
      expect(result.errors[0].code).toBe('ERR_CONN');
      expect(result.errors[0].recoverable).toBe(true);
      expect(result.errors[0].id).toBe('err-1');
    });

    it('should parse error event with minimal payload', () => {
      const events = [
        {
          type: 'error',
          data: '{"message": "Unknown error"}',
        },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.errors).toHaveLength(1);
      expect(result.errors[0].message).toBe('Unknown error');
      expect(result.errors[0].code).toBeUndefined();
      expect(result.errors[0].recoverable).toBe(false);
    });

    it('should handle error event with plain text data', () => {
      const events = [
        {
          type: 'error',
          data: 'Something went wrong',
        },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.errors).toHaveLength(1);
      expect(result.errors[0].message).toBe('Something went wrong');
    });

    it('should handle error event with empty data', () => {
      const events = [
        {
          type: 'error',
          data: '',
        },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.errors).toHaveLength(1);
      // When data is empty string, normalizeText returns empty string
      // The fallback 'Erro desconhecido' only applies when payload fields are null/undefined
      expect(result.errors[0].message).toBe('');
    });

    it('should use fallback message when all error fields are missing', () => {
      const events = [
        {
          type: 'error',
          data: '{}',
        },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.errors).toHaveLength(1);
      // When payload is empty object, event.data ('{}') is used as fallback
      expect(result.errors[0].message).toBe('{}');
    });

    it('should handle error event with malformed JSON', () => {
      const events = [
        {
          type: 'error',
          data: '{invalid json}',
        },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.errors).toHaveLength(1);
      expect(result.errors[0].message).toBe('{invalid json}');
    });

    it('should add error to journey steps', () => {
      const events = [
        {
          type: 'error',
          data: '{"message": "Task failed"}',
          meta: { agent: 'coder' },
        },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.journey.steps).toHaveLength(1);
      expect(result.journey.steps[0].title).toBe('Erro');
      expect(result.journey.steps[0].detail).toBe('Task failed');
      expect(result.journey.steps[0].status).toBe('error');
      expect(result.journey.steps[0].agentType).toBe('coder');
    });

    it('should handle multiple error events', () => {
      const events = [
        { type: 'error', data: '{"message": "Error 1"}' },
        { type: 'error', data: '{"message": "Error 2"}' },
        { type: 'error', data: '{"message": "Error 3"}' },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.errors).toHaveLength(3);
      expect(result.errors[0].message).toBe('Error 1');
      expect(result.errors[1].message).toBe('Error 2');
      expect(result.errors[2].message).toBe('Error 3');
    });

    it('should assign timestamp to error events', () => {
      const before = Date.now();
      const events = [
        { type: 'error', data: '{"message": "Test error"}' },
      ];
      const result = buildStreamPresentation(events, false);
      const after = Date.now();
      expect(result.errors[0].timestamp).toBeGreaterThanOrEqual(before);
      expect(result.errors[0].timestamp).toBeLessThanOrEqual(after);
    });

    it('should generate error ID when not provided', () => {
      const events = [
        { type: 'error', data: '{"message": "Error 1"}' },
        { type: 'error', data: '{"message": "Error 2"}' },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.errors[0].id).toBe('error-0');
      expect(result.errors[1].id).toBe('error-1');
    });
  });

  describe('Scope Escape Detection', () => {
    it('should detect scope escape from scope_escape field', () => {
      const events = [
        {
          type: 'orchestrator_decision',
          data: '{"scope_escape": true, "decision": "Out of scope"}',
        },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.diagnostics.scopeEscape).toBe(true);
    });

    it('should detect scope escape from execution_strategy', () => {
      const events = [
        {
          type: 'orchestrator_decision',
          data: '{"execution_strategy": "scope_escape"}',
        },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.diagnostics.scopeEscape).toBe(true);
    });

    it('should detect scope escape from routing_reason', () => {
      const events = [
        {
          type: 'orchestrator_decision',
          data: '{"routing_reason": "Request is out of scope"}',
        },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.diagnostics.scopeEscape).toBe(true);
    });

    it('should detect scope escape from decision text', () => {
      const events = [
        {
          type: 'orchestrator_decision',
          data: '{"decision": "This request is out of scope"}',
        },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.diagnostics.scopeEscape).toBe(true);
    });

    it('should not detect scope escape when not present', () => {
      const events = [
        {
          type: 'orchestrator_decision',
          data: '{"decision": "Route to coder"}',
        },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.diagnostics.scopeEscape).toBe(false);
    });
  });

  describe('parseStructuredStreamEventData', () => {
    it('should parse valid JSON', () => {
      const result = parseStructuredStreamEventData('{"key": "value"}');
      expect(result).toEqual({ key: 'value' });
    });

    it('should return null for invalid JSON', () => {
      const result = parseStructuredStreamEventData('{invalid}');
      expect(result).toBeNull();
    });

    it('should return null for empty string', () => {
      const result = parseStructuredStreamEventData('');
      expect(result).toBeNull();
    });

    it('should return null for whitespace-only string', () => {
      const result = parseStructuredStreamEventData('   ');
      expect(result).toBeNull();
    });

    it('should parse complex nested objects', () => {
      const data = '{"nested": {"key": "value"}, "array": [1, 2, 3]}';
      const result = parseStructuredStreamEventData(data);
      expect(result).toEqual({
        nested: { key: 'value' },
        array: [1, 2, 3],
      });
    });
  });

  describe('Tool Event Handling', () => {
    it('should create tool event from tool_call', () => {
      const events = [
        {
          type: 'tool_call',
          data: '{"id": "tool-1", "name": "readFile", "args": {"path": "test.ts"}}',
        },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.toolEvents).toHaveLength(1);
      expect(result.toolEvents[0].name).toBe('readFile');
      expect(result.toolEvents[0].status).toBe('running');
    });

    it('should update tool event status on tool_result', () => {
      const events = [
        {
          type: 'tool_call',
          data: '{"id": "tool-1", "name": "readFile"}',
        },
        {
          type: 'tool_result',
          data: '{"id": "tool-1", "result": "file content"}',
        },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.toolEvents).toHaveLength(1);
      expect(result.toolEvents[0].status).toBe('completed');
      expect(result.toolEvents[0].result).toBe('file content');
    });

    it('should handle tool error', () => {
      const events = [
        {
          type: 'tool_call',
          data: '{"id": "tool-1", "name": "readFile"}',
        },
        {
          type: 'tool_result',
          data: '{"id": "tool-1", "error": "File not found"}',
        },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.toolEvents).toHaveLength(1);
      expect(result.toolEvents[0].status).toBe('error');
      expect(result.toolEvents[0].error).toBe('File not found');
    });
  });

  describe('Thinking State Management', () => {
    it('should set orchestrator thinking status on orchestrator_thinking_start', () => {
      const events = [
        { type: 'orchestrator_thinking_start', data: '' },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.activeAgents).toContain('orchestrator');
      expect(result.thinkingStatuses.orchestrator).toBe('routing');
    });

    it('should update orchestrator status on orchestrator_thinking_end', () => {
      const events = [
        { type: 'orchestrator_thinking_start', data: '' },
        { type: 'orchestrator_thinking_end', data: '' },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.thinkingStatuses.orchestrator).toBe('ready');
    });

    it('should create thought from orchestrator_thinking event', () => {
      const events = [
        {
          type: 'orchestrator_thinking',
          data: 'Analyzing the request...',
          meta: { agent: 'orchestrator' },
        },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.thoughts).toHaveLength(1);
      expect(result.thoughts[0].content).toBe('Analyzing the request...');
      expect(result.thoughts[0].agentType).toBe('orchestrator');
    });
  });

  describe('Memory Event Handling', () => {
    it('should create memory event from context_loaded notifier', () => {
      const events = [
        {
          type: 'notifier',
          data: '{"kind": "context_loaded", "message": "Context loaded", "details": {"source": "database", "count": 5}}',
        },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.memoryEvents).toHaveLength(1);
      expect(result.memoryEvents[0].source).toBe('database');
      expect(result.memoryEvents[0].count).toBe(5);
    });

    it('should default to vector source when not database', () => {
      const events = [
        {
          type: 'notifier',
          data: '{"kind": "memory", "message": "Memory loaded"}',
        },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.memoryEvents).toHaveLength(1);
      expect(result.memoryEvents[0].source).toBe('vector');
    });
  });

  describe('Delegation Handling', () => {
    it('should create delegation from agent_delegation_start', () => {
      const events = [
        {
          type: 'agent_delegation_start',
          data: '{"agent_role": "coder", "task": "Write unit tests", "step_id": "123"}',
        },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.delegations).toHaveLength(1);
      expect(result.delegations[0].subtitle).toBe('Write unit tests');
      expect(result.delegations[0].agents[0].agentType).toBe('coder');
    });

    it('should add journey step for delegation', () => {
      const events = [
        {
          type: 'agent_delegation_start',
          data: '{"agent_role": "analyst", "task": "Analyze data"}',
        },
      ];
      const result = buildStreamPresentation(events, false);
      expect(result.journey.steps).toHaveLength(1);
      expect(result.journey.steps[0].title).toContain('Analyst');
      expect(result.journey.steps[0].status).toBe('live');
    });
  });
});
