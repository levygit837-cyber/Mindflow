import { describe, it, expect } from "vitest";
import { buildDynamicPrompt } from "@/lib/agent/prompts/dynamic-prompt";
import { MessagesAnnotation } from "@langchain/langgraph";
import { HumanMessage } from "@langchain/core/messages";

describe("buildDynamicPrompt", () => {
  const baseState = {
    messages: [new HumanMessage("Olá")],
  };

  it("retorna SystemMessage + messages no mínimo", () => {
    const result = buildDynamicPrompt(baseState);
    expect(result.length).toBeGreaterThanOrEqual(2);
    const first = result[0] as { role: string; content: string };
    expect(first.role).toBe("system");
    expect(first.content).toContain("OmniMind");
  });

  it("inclui instruções de filesystem quando há tool_calls de filesystem", () => {
    const stateWithFsTool = {
      messages: [
        new HumanMessage("leia o arquivo"),
        // Simula AIMessage com tool_call de filesystem
        {
          type: "ai",
          content: "",
          tool_calls: [{ id: "tc-1", name: "read_file", args: { file_path: "/src/index.ts" } }],
        },
      ],
    };
    const result = buildDynamicPrompt(stateWithFsTool as typeof MessagesAnnotation.State);
    const systemContent = (result[0] as { role: string; content: string }).content;
    expect(systemContent).toContain("read_file");
    expect(systemContent).toContain("edit_file");
  });

  it("inclui instruções de web search quando há tool_calls de search", () => {
    const stateWithSearchTool = {
      messages: [
        new HumanMessage("pesquise"),
        {
          type: "ai",
          content: "",
          tool_calls: [{ id: "tc-2", name: "search_web", args: { query: "langgraph" } }],
        },
      ],
    };
    const result = buildDynamicPrompt(stateWithSearchTool as typeof MessagesAnnotation.State);
    const systemContent = (result[0] as { role: string; content: string }).content;
    expect(systemContent).toContain("search_web");
  });

  it("não duplica seções quando múltiplas tools do mesmo grupo são chamadas", () => {
    const stateWithMultipleFsTools = {
      messages: [
        new HumanMessage("edite e leia"),
        {
          type: "ai",
          content: "",
          tool_calls: [
            { id: "tc-3", name: "read_file", args: {} },
            { id: "tc-4", name: "edit_file", args: {} },
          ],
        },
      ],
    };
    const resultBoth = buildDynamicPrompt(stateWithMultipleFsTools as typeof MessagesAnnotation.State);
    const systemContentBoth = (resultBoth[0] as { role: string; content: string }).content;

    // Verifica que a seção de filesystem aparece exatamente UMA vez
    // (não duplicada porque read_file e edit_file pertencem ao mesmo grupo)
    const stateWithOnlyReadFile = {
      messages: [
        new HumanMessage("leia"),
        {
          type: "ai",
          content: "",
          tool_calls: [{ id: "tc-5", name: "read_file", args: {} }],
        },
      ],
    };
    const resultOne = buildDynamicPrompt(stateWithOnlyReadFile as typeof MessagesAnnotation.State);
    const systemContentOne = (resultOne[0] as { role: string; content: string }).content;

    // Com um ou dois tools do mesmo grupo, o número de ocorrências de "read_file" deve ser idêntico
    const occurrencesBoth = (systemContentBoth.match(/read_file/g) ?? []).length;
    const occurrencesOne = (systemContentOne.match(/read_file/g) ?? []).length;
    expect(occurrencesBoth).toBe(occurrencesOne);
    expect(occurrencesBoth).toBeGreaterThan(0);
  });
});
