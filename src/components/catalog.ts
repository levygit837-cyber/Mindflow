/**
 * MindFlow CLI Component Catalog
 * Defines the component schema for json-render
 */

import { defineCatalog } from "@json-render/core";
import { schema } from "@json-render/ink/schema";
import { z } from "zod";

export const catalog = defineCatalog(schema, {
  components: {
    // Layout Components
    InputBar: {
      props: z.object({
        placeholder: z.string().default("Type your request..."),
        value: z.string().default(""),
        focused: z.boolean().default(true),
      }),
      description: "Input bar for user prompts with cursor",
    },

    // Message Components
    UserMessage: {
      props: z.object({
        content: z.string(),
        timestamp: z.string().optional(),
      }),
      description: "User message bubble with timestamp",
    },

    AgentMessage: {
      props: z.object({
        agentName: z.string(),
        agentRole: z.string().optional(),
        content: z.string(),
        timestamp: z.string().optional(),
        color: z.string().optional(),
      }),
      description: "Agent message bubble with agent info",
    },

    OutputRender: {
      props: z.object({
        content: z.string(),
        language: z.string().optional(),
        streaming: z.boolean().default(false),
      }),
      description: "Rendered output (code, markdown, etc.)",
    },

    // EventRail Components
    ThinkingIndicator: {
      props: z.object({
        active: z.boolean().default(true),
        message: z.string().default("Thinking..."),
      }),
      description: "Thinking indicator with animated dots",
    },

    SpinnerLoader: {
      props: z.object({
        active: z.boolean().default(true),
        message: z.string().optional(),
      }),
      description: "Spinner loader for async operations",
    },

    ReadTool: {
      props: z.object({
        path: z.string(),
        status: z.enum(["pending", "running", "completed", "error"]).default("pending"),
        preview: z.string().optional(),
      }),
      description: "File read tool indicator",
    },

    WriteTool: {
      props: z.object({
        path: z.string(),
        status: z.enum(["pending", "running", "completed", "error"]).default("pending"),
        preview: z.string().optional(),
      }),
      description: "File write tool indicator",
    },
  },
  actions: {
    submit_prompt: {
      description: "Submit user prompt to agents",
    },
    cancel_operation: {
      description: "Cancel current operation",
    },
    toggle_expansion: {
      description: "Toggle component expansion",
    },
  },
});
