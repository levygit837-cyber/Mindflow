import { describe, it, expect } from "vitest";
import {
  classifyNode,
  getNodeLabel,
  isStreamableNode,
  NodeCategory,
} from "@backend/agent/node-registry";

describe("node-registry", () => {
  it("classifica 'agent' como LLM_INVOKE", () => {
    expect(classifyNode("agent")).toBe(NodeCategory.LLM_INVOKE);
  });

  it("classifica 'tools' como TOOL_EXECUTION", () => {
    expect(classifyNode("tools")).toBe(NodeCategory.TOOL_EXECUTION);
  });

  it("classifica nodes de middleware como INTERNAL", () => {
    expect(classifyNode("patchToolCallsMiddleware.before_agent")).toBe(NodeCategory.INTERNAL);
    expect(classifyNode("SummarizationMiddleware.after_agent")).toBe(NodeCategory.INTERNAL);
    expect(classifyNode("__start__")).toBe(NodeCategory.INTERNAL);
    expect(classifyNode("__end__")).toBe(NodeCategory.INTERNAL);
  });

  it("classifica subgraph nodes como SUBGRAPH", () => {
    expect(classifyNode("coder:agent")).toBe(NodeCategory.SUBGRAPH);
    expect(classifyNode("analyst:tools")).toBe(NodeCategory.SUBGRAPH);
  });

  it("classifica nodes desconhecidos como UNKNOWN", () => {
    expect(classifyNode("my_custom_node")).toBe(NodeCategory.UNKNOWN);
  });

  it("retorna label amigável para nodes conhecidos", () => {
    expect(getNodeLabel("agent")).toBe("Agent");
    expect(getNodeLabel("tools")).toBe("Tools");
  });

  it("retorna label descritivo para subgraph nodes", () => {
    expect(getNodeLabel("coder:agent")).toBe("Coder › Agent");
  });

  it("isStreamableNode retorna false para INTERNAL", () => {
    expect(isStreamableNode("__start__")).toBe(false);
    expect(isStreamableNode("patchToolCallsMiddleware.before_agent")).toBe(false);
  });

  it("isStreamableNode retorna true para agent e tools", () => {
    expect(isStreamableNode("agent")).toBe(true);
    expect(isStreamableNode("tools")).toBe(true);
  });
});
