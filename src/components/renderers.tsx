/**
 * MindFlow CLI Component Renderers
 * Ink renderers for the component catalog
 */

import React from "react";
import { Box, Text } from "ink";
import { defineRegistry, Renderer } from "@json-render/ink";
import { catalog } from "./catalog";

// Cursor blink effect hook
function useCursorBlink(interval = 530) {
  const [visible, setVisible] = React.useState(true);

  React.useEffect(() => {
    const timer = setInterval(() => setVisible((v) => !v), interval);
    return () => clearInterval(timer);
  }, [interval]);

  return visible;
}

// Input Bar Renderer
const InputBar = ({ props }: { props: any }) => {
  const cursorVisible = useCursorBlink();

  return React.createElement(
    Box,
    { flexDirection: "row", alignItems: "center" },
    React.createElement(Text, { bold: true, color: "green" }, "> "),
    React.createElement(Text, null, props.value),
    props.focused &&
      React.createElement(Text, { color: cursorVisible ? "green" : "white" }, "\u2588")
  );
};

// User Message Renderer
const UserMessage = ({ props }: { props: any }) => {
  return React.createElement(
    Box,
    { flexDirection: "column", marginBottom: 1 },
    React.createElement(
      Box,
      { flexDirection: "row" },
      React.createElement(Text, { bold: true, color: "cyan" }, "You:"),
      props.timestamp &&
        React.createElement(Text, { dimColor: true, color: "gray" }, ` ${props.timestamp}`)
    ),
    React.createElement(Text, null, props.content)
  );
};

// Agent Message Renderer
const AgentMessage = ({ props }: { props: any }) => {
  const agentColor = props.color || "blue";

  return React.createElement(
    Box,
    { flexDirection: "column", marginBottom: 1 },
    React.createElement(
      Box,
      { flexDirection: "row" },
      React.createElement(Text, { bold: true, color: agentColor }, `${props.agentName}:`),
      props.agentRole &&
        React.createElement(Text, { dimColor: true, color: "gray" }, ` (${props.agentRole})`),
      props.timestamp &&
        React.createElement(Text, { dimColor: true, color: "gray" }, ` ${props.timestamp}`)
    ),
    React.createElement(Text, null, props.content)
  );
};

// Output Render Renderer
const OutputRender = ({ props }: { props: any }) => {
  const languageColor = props.language ? "yellow" : "white";
  const streamingIndicator = props.streaming ? "▌" : "";

  return React.createElement(
    Box,
    { flexDirection: "column", marginBottom: 1, paddingX: 2 },
    props.language &&
      React.createElement(
        Text,
        { dimColor: true, color: languageColor },
        `[${props.language}]`
      ),
    React.createElement(Text, null, props.content + streamingIndicator)
  );
};

// Thinking Indicator Renderer
const ThinkingIndicator = ({ props }: { props: any }) => {
  const [dots, setDots] = React.useState(0);

  React.useEffect(() => {
    if (!props.active) return;
    const interval = setInterval(() => setDots((d) => (d + 1) % 4), 300);
    return () => clearInterval(interval);
  }, [props.active]);

  if (!props.active) return null;

  const dotsStr = ".".repeat(dots);

  return React.createElement(
    Box,
    { flexDirection: "row" },
    React.createElement(Text, { dimColor: true, color: "gray" }, `${props.message}${dotsStr}`)
  );
};

// Spinner Loader Renderer
const SpinnerLoader = ({ props }: { props: any }) => {
  const [frame, setFrame] = React.useState(0);
  const spinnerChars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];

  React.useEffect(() => {
    if (!props.active) return;
    const interval = setInterval(() => setFrame((f) => (f + 1) % spinnerChars.length), 80);
    return () => clearInterval(interval);
  }, [props.active]);

  if (!props.active) return null;

  return React.createElement(
    Box,
    { flexDirection: "row" },
    React.createElement(Text, { color: "yellow" }, spinnerChars[frame]),
    props.message &&
      React.createElement(Text, { dimColor: true, color: "gray" }, ` ${props.message}`)
  );
};

// Read Tool Renderer
const ReadTool = ({ props }: { props: any }) => {
  const statusColors: Record<string, string> = {
    pending: "gray",
    running: "yellow",
    completed: "green",
    error: "red",
  };
  const statusIcons: Record<string, string> = {
    pending: "○",
    running: "◐",
    completed: "●",
    error: "✕",
  };

  const status = props.status || "pending";

  return React.createElement(
    Box,
    { flexDirection: "column", marginBottom: 1, paddingX: 2 },
    React.createElement(
      Box,
      { flexDirection: "row" },
      React.createElement(Text, { color: statusColors[status] }, statusIcons[status]),
      React.createElement(Text, { dimColor: true, color: "gray" }, " READ: "),
      React.createElement(Text, { color: "cyan" }, props.path)
    ),
    props.preview &&
      React.createElement(Text, { dimColor: true, color: "gray" }, `  ${props.preview}`)
  );
};

// Write Tool Renderer
const WriteTool = ({ props }: { props: any }) => {
  const statusColors: Record<string, string> = {
    pending: "gray",
    running: "yellow",
    completed: "green",
    error: "red",
  };
  const statusIcons: Record<string, string> = {
    pending: "○",
    running: "◐",
    completed: "●",
    error: "✕",
  };

  const status = props.status || "pending";

  return React.createElement(
    Box,
    { flexDirection: "column", marginBottom: 1, paddingX: 2 },
    React.createElement(
      Box,
      { flexDirection: "row" },
      React.createElement(Text, { color: statusColors[status] }, statusIcons[status]),
      React.createElement(Text, { dimColor: true, color: "gray" }, " WRITE: "),
      React.createElement(Text, { color: "magenta" }, props.path)
    ),
    props.preview &&
      React.createElement(Text, { dimColor: true, color: "gray" }, `  ${props.preview}`)
  );
};

// Create registry with all renderers
export const { registry } = defineRegistry(catalog, {
  components: {
    InputBar,
    UserMessage,
    AgentMessage,
    OutputRender,
    ThinkingIndicator,
    SpinnerLoader,
    ReadTool,
    WriteTool,
  },
});
