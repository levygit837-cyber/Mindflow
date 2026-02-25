import { render } from "@testing-library/react";
import { describe, it, expect, vi, beforeAll } from "vitest";

// Mock scrollIntoView which doesn't exist in jsdom
beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

// Mock ScrollArea to just render children
vi.mock("@frontend/components/ui/scroll-area", () => ({
  ScrollArea: ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <div className={className}>{children}</div>
  ),
}));

// Mock the useAgentChat hook
vi.mock("@frontend/hooks/use-agent-chat", () => ({
  useAgentChat: () => ({
    messages: [
      {
        id: "msg-1",
        role: "assistant",
        content: "Hello world",
        thoughts: "",
        toolCalls: [],
        isStreaming: false,
        contentParts: [
          { type: "text", id: "part-1", content: "Hello world" },
        ],
      },
    ],
    isLoading: false,
    provider: "vertexai",
    model: "gemini-3-flash-preview",
    sendMessage: vi.fn(),
    setProvider: vi.fn(),
    setModel: vi.fn(),
    setNoteContext: vi.fn(),
    clearMessages: vi.fn(),
  }),
}));

describe("ChatInterface", () => {
  it("assistant messages have max-width constraint", async () => {
    const { ChatInterface } = await import("../chat-interface");
    const { container } = render(<ChatInterface />);

    // Find the assistant message wrapper
    const assistantWrapper = container.querySelector("[data-testid='assistant-message']");
    expect(assistantWrapper).toBeTruthy();
    expect(assistantWrapper?.className).toContain("max-w-3xl");
  });

  it("content parts do not have fade-in-up animation class", async () => {
    const { ChatInterface } = await import("../chat-interface");
    const { container } = render(<ChatInterface />);

    // No element within the message area should have animate-fade-in-up
    const animatedElements = container.querySelectorAll(".animate-fade-in-up");
    expect(animatedElements.length).toBe(0);
  });

  it("response block does not use max-w-none", async () => {
    const { ResponseBlock } = await import("../response-block");
    const { container } = render(
      <ResponseBlock content="Hello" isStreaming={false} />
    );

    const proseEl = container.querySelector(".prose");
    expect(proseEl).toBeTruthy();
    expect(proseEl?.className).not.toContain("max-w-none");
  });
});
