import { render } from "@testing-library/react";
import { describe, it, expect, beforeAll, vi } from "vitest";
import { ThinkingBlock } from "../thinking-block";

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

describe("ThinkingBlock", () => {
  it("does not render animate-ping elements when streaming", () => {
    const { container } = render(
      <ThinkingBlock
        id="t-1"
        content=""
        isStreaming={true}
      />
    );

    const pingElements = container.querySelectorAll(".animate-ping");
    expect(pingElements.length).toBe(0);
  });

  it("renders a simple pulsing dot instead of ping animation", () => {
    const { container } = render(
      <ThinkingBlock
        id="t-1"
        content=""
        isStreaming={true}
      />
    );

    const pulseDot = container.querySelector(".animate-pulse");
    expect(pulseDot).toBeTruthy();
  });
});
