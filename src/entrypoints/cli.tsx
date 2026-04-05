#!/usr/bin/env node
/**
 * MindFlow CLI - Entry Point
 * Built with json-render for AI-generated UI
 */

import React from "react";
import { Box, Text, render, useInput, useApp } from "ink";
import { useState, useCallback, useEffect } from "react";
import { Renderer, JSONUIProvider } from "@json-render/ink";
import { registry } from "../components/renderers";

async function main() {
    const args = process.argv.slice(2);

    // Fast-path for --version
    if (args.length === 1 && (args[0] === "--version" || args[0] === "-V" || args[0] === "-v")) {
        console.log("MindFlow CLI v0.2.0");
        return;
    }

    // Initial spec - empty state
    const initialSpec = {
        root: "Box",
        elements: {
            Box: {
                type: "Box",
                props: {
                    flexDirection: "column",
                    flexGrow: 1,
                    padding: 1,
                },
                children: ["Header", "Greeting", "InputBar"],
            },
            Header: {
                type: "Box",
                props: {
                    flexDirection: "row",
                    justifyContent: "space-between",
                    marginBottom: 1,
                },
                children: ["Title", "Help"],
            },
            Title: {
                type: "Box",
                props: {},
                children: [],
            },
            Help: {
                type: "Box",
                props: {},
                children: [],
            },
            Greeting: {
                type: "Box",
                props: {
                    marginBottom: 1,
                },
                children: [],
            },
            InputBar: {
                type: "InputBar",
                props: {
                    placeholder: "Type your request...",
                    value: "",
                    focused: true,
                },
            },
        },
    };

    function App() {
        const [spec, setSpec] = useState(initialSpec);
        const [inputValue, setInputValue] = useState("");
        const [messages, setMessages] = useState<any[]>([]);
        const { exit } = useApp();

        // Handle Ctrl+C to exit
        useInput((input, key) => {
            if (key.ctrl && input === "c") {
                exit();
                process.exit(0);
                return;
            }

            // Handle Enter key
            if (key.return) {
                if (!inputValue.trim()) return;

                // Add user message
                const userMsgId = `UserMessage-${Date.now()}`;
                const newMessages = [...messages, userMsgId];
                setMessages(newMessages);

                // Update spec with new message
                const updatedSpec = {
                    ...spec,
                    elements: {
                        ...spec.elements,
                        [userMsgId]: {
                            type: "UserMessage",
                            props: {
                                content: inputValue,
                                timestamp: new Date().toISOString(),
                            },
                        },
                        Box: {
                            ...spec.elements.Box,
                            children: [
                                ...spec.elements.Box.children.filter((c: string) => c !== "InputBar"),
                                userMsgId,
                                "InputBar",
                            ],
                        },
                        InputBar: {
                            type: "InputBar",
                            props: {
                                placeholder: "Type your request...",
                                value: "",
                                focused: true,
                            },
                        },
                    },
                };
                setSpec(updatedSpec);
                setInputValue("");

                // Simulate agent response (placeholder)
                setTimeout(() => {
                    const agentMsgId = `AgentMessage-${Date.now()}`;
                    setSpec((prev: any) => ({
                        ...prev,
                        elements: {
                            ...prev.elements,
                            [agentMsgId]: {
                                type: "AgentMessage",
                                props: {
                                    agentName: "Orchestrator",
                                    agentRole: "orchestrator",
                                    content: `Processing: "${inputValue}"\n\n> Connect to MindFlow backend for full agent capabilities.`,
                                    color: "blue",
                                    timestamp: new Date().toISOString(),
                                },
                            },
                            Box: {
                                ...prev.elements.Box,
                                children: [
                                    ...prev.elements.Box.children.filter((c: string) => c !== "InputBar"),
                                    agentMsgId,
                                    "InputBar",
                                ],
                            },
                        },
                    }));
                }, 500);

                return;
            }

            // Handle backspace
            if (key.backspace || key.delete) {
                setInputValue((prev) => prev.slice(0, -1));
                return;
            }

            // Handle escape
            if (key.escape) {
                return;
            }

            // Handle arrows
            if (key.upArrow || key.downArrow || key.leftArrow || key.rightArrow) {
                return;
            }

            // Handle tab
            if (key.tab) {
                return;
            }

            // Only accept printable characters
            if (input && input.length === 1 && input.charCodeAt(0) >= 32 && input.charCodeAt(0) <= 126) {
                setInputValue((prev) => prev + input);
            }
        });

        // Update InputBar value in spec when inputValue changes
        useEffect(() => {
            setSpec((prev: any) => ({
                ...prev,
                elements: {
                    ...prev.elements,
                    InputBar: {
                        type: "InputBar",
                        props: {
                            placeholder: "Type your request...",
                            value: inputValue,
                            focused: true,
                        },
                    },
                },
            }));
        }, [inputValue]);

        // Greeting based on time
        const hour = new Date().getHours();
        const period = hour < 12 ? "Morning" : hour < 18 ? "Afternoon" : "Evening";

        return React.createElement(
            Box,
            { flexDirection: "column", padding: 1 },
            React.createElement(Text, { bold: true, color: "cyan" }, "MindFlow CLI v0.2.0"),
            React.createElement(Text, { dimColor: true }, "Built with json-render"),
            React.createElement(Text, null, ""),
            React.createElement(Text, { bold: true }, `Good ${period}! MindFlow CLI ready.`),
            React.createElement(Text, { dimColor: true }, "Type your request or /help for commands"),
            React.createElement(Text, null, ""),
            React.createElement(
                JSONUIProvider,
                {
                    initialState: {},
                    children: React.createElement(Renderer, { spec, registry })
                }
            )
        );
    }

    render(React.createElement(App), { exitOnCtrlC: true });
}

main().catch((err) => {
    console.error("Failed to start MindFlow CLI:", err);
    process.exit(1);
});