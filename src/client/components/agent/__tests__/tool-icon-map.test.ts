import { describe, it, expect } from "vitest";
import { getToolConfig } from "../tool-icon-map";

describe("getToolConfig", () => {
  it("returns config without accentColor field", () => {
    const config = getToolConfig("read_file");
    expect(config).toHaveProperty("icon");
    expect(config).toHaveProperty("label");
    expect(config).not.toHaveProperty("accentColor");
  });

  it("returns correct label for known tools", () => {
    expect(getToolConfig("read_file").label).toBe("Read File");
    expect(getToolConfig("write_file").label).toBe("Write File");
    expect(getToolConfig("search_web").label).toBe("Web Search");
    expect(getToolConfig("execute").label).toBe("Execute Code");
  });

  it("prettifies unknown tool names", () => {
    expect(getToolConfig("my_custom_tool").label).toBe("My Custom Tool");
  });
});
