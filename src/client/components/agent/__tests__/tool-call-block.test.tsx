import { render } from "@testing-library/react";
import { describe, it, expect, beforeAll, vi } from "vitest";
import { ToolCallBlock } from "../tool-call-block";

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

describe("ToolCallBlock", () => {
  it("does not render Check icon for success status", () => {
    const { container } = render(
      <ToolCallBlock
        id="tc-1"
        toolName="read_file"
        toolInput={{ path: "/test.ts" }}
        toolOutput="file contents"
        status="success"
        startedAt={new Date().toISOString()}
        completedAt={new Date().toISOString()}
      />
    );

    // Should NOT have a Check (checkmark) SVG — should use a dot instead
    const checkSvgs = container.querySelectorAll("svg");
    const checkPaths = Array.from(checkSvgs).filter(
      (svg) => svg.querySelector("polyline[points='20 6 9 17 4 12']") !== null
    );
    expect(checkPaths.length).toBe(0);
  });

  it("renders a subtle dot for success status", () => {
    const { container } = render(
      <ToolCallBlock
        id="tc-1"
        toolName="read_file"
        toolInput={{ path: "/test.ts" }}
        toolOutput="file contents"
        status="success"
        startedAt={new Date().toISOString()}
        completedAt={new Date().toISOString()}
      />
    );

    // Should have a dot span element for success
    const dots = container.querySelectorAll("span.rounded-full");
    expect(dots.length).toBeGreaterThan(0);
  });

  it("tool call button does not use w-full", () => {
    const { container } = render(
      <ToolCallBlock
        id="tc-1"
        toolName="read_file"
        toolInput={{ path: "/test.ts" }}
        toolOutput={null}
        status="running"
        startedAt={new Date().toISOString()}
      />
    );

    const button = container.querySelector("button");
    expect(button).toBeTruthy();
    expect(button?.className).not.toContain("w-full");
  });
});
