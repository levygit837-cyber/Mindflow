#!/usr/bin/env node
/**
 * MindFlow CLI - Entry Point
 * Interactive REPL with Ink terminal UI and proper text input.
 */

import React from "react";

async function main() {
    const args = process.argv.slice(2);

    // Fast-path for --version
    if (args.length === 1 && (args[0] === "--version" || args[0] === "-V" || args[0] === "-v")) {
        console.log("MindFlow CLI v0.1.0");
        return;
    }

    // Dynamic ESM imports
    const { Box, Text, render, useInput, useApp, useStdin } = await import("ink");
    const { useState, useCallback } = await import("react");

    type Message = {
        id: string;
        type: "user" | "agent" | "system" | "error";
        content: string;
        timestamp: Date;
        agentId?: string;
        agentName?: string;
        agentRole?: string;
    };

    // -----------------------------------------------------------------------
    // Help / Commands
    // -----------------------------------------------------------------------

    const COMMANDS = [
        { cmd: "/help", desc: "Show available commands" },
        { cmd: "/clear", desc: "Clear chat history" },
        { cmd: "/team", desc: "Show team composition" },
        { cmd: "/exit", desc: "Exit MindFlow CLI" },
    ];

    function getHelpText(): string {
        return [
            "--- Commands---",
            ...COMMANDS.map((c) => `  ${c.cmd.padEnd(12)} ${c.desc}`),
        ].join("\n");
    }

    // -----------------------------------------------------------------------
    // TextInput Component - Properly handles raw input without flickering
    // -----------------------------------------------------------------------

    function TextInput({
        value,
        onSubmit,
        isFocused = true,
    }: {
        value: string;
        onSubmit: (text: string) => void;
        isFocused?: boolean;
    }) {
        const [cursorVisible, setCursorVisible] = useState(true);

        // Blink cursor effect
        useState(() => {
            const interval = setInterval(() => {
                setCursorVisible((v) => !v);
            }, 530);
            return () => clearInterval(interval);
        });

        return React.createElement(
            Box,
            { flexDirection: "row" },
            React.createElement(Text, { bold: true, color: "green" }, "> "),
            React.createElement(Text, null, value),
            isFocused &&
            React.createElement(
                Text,
                { color: cursorVisible ? "green" : "white" },
                "\u2588" // Block cursor character
            )
        );
    }

    // -----------------------------------------------------------------------
    // REPL Component
    // -----------------------------------------------------------------------

    function REPL() {
        const [messages, setMessages] = useState<Message[]>([]);
        const [inputValue, setInputValue] = useState("");
        const { exit } = useApp();

        const handleSubmit = useCallback(
            (text: string) => {
                if (!text.trim()) return;

                const trimmed = text.trim();

                // User message
                const userMsg: Message = {
                    id: String(Date.now()),
                    type: "user",
                    content: trimmed,
                    timestamp: new Date(),
                };
                setMessages((prev) => [...prev, userMsg]);

                // Handle local commands
                if (trimmed === "/exit" || trimmed === "/quit") {
                    exit();
                    process.exit(0);
                    return;
                }

                if (trimmed === "/help") {
                    setMessages((prev) => [
                        ...prev,
                        {
                            id: String(Date.now() + 1),
                            type: "system",
                            content: getHelpText(),
                            timestamp: new Date(),
                        },
                    ]);
                    return;
                }

                if (trimmed === "/clear") {
                    setMessages([]);
                    return;
                }

                if (trimmed === "/team") {
                    setMessages((prev) => [
                        ...prev,
                        {
                            id: String(Date.now() + 1),
                            type: "system",
                            content:
                                "Team: No active agents. Connect to MindFlow backend to start a session.",
                            timestamp: new Date(),
                        },
                    ]);
                    return;
                }

                // Agent echo response (placeholder until backend is connected)
                const agentMsg: Message = {
                    id: String(Date.now() + 2),
                    type: "agent",
                    content: `Processing: "${trimmed}"\n\n> Connect to MindFlow backend for full agent capabilities.`,
                    timestamp: new Date(),
                    agentName: "mindflow",
                    agentRole: "orchestrator",
                };
                setMessages((prev) => [...prev, agentMsg]);
            },
            [exit]
        );

        useInput((input, key) => {
            // Handle Enter key
            if (key.return) {
                handleSubmit(inputValue);
                setInputValue("");
                return;
            }

            // Handle backspace
            if (key.backspace || key.delete) {
                setInputValue((prev) => prev.slice(0, -1));
                return;
            }

            // Handle escape - do nothing
            if (key.escape) {
                return;
            }

            // Handle arrows - do nothing for now
            if (key.upArrow || key.downArrow || key.leftArrow || key.rightArrow) {
                return;
            }

            // Handle tab - do nothing for now
            if (key.tab) {
                return;
            }

            // Handle Ctrl+C and Ctrl+Z
            if (key.ctrl && (input === "c" || input === "z")) {
                return;
            }

            // Only accept printable single characters
            // Filter out control characters and escape sequences
            if (input && input.length === 1 && input.charCodeAt(0) >= 32 && input.charCodeAt(0) <= 126) {
                setInputValue((prev) => prev + input);
            }
        });

        // Greeting
        const hour = new Date().getHours();
        const period = hour < 12 ? "Morning" : hour < 18 ? "Afternoon" : "Evening";

        return React.createElement(
            Box,
            { flexDirection: "column", flexGrow: 1 },
            // Header
            React.createElement(
                Box,
                { flexDirection: "row", justifyContent: "space-between" },
                React.createElement(Text, { bold: true, color: "cyan" }, "MindFlow CLI"),
                React.createElement(Text, { dimColor: true }, "help for commands")
            ),
            React.createElement(Text, null, ""),
            // Greeting
            React.createElement(Text, { bold: true }, `Good ${period}! MindFlow CLI ready.`),
            React.createElement(Text, null, ""),
            // Messages
            ...messages.flatMap((msg, idx) => {
                const prefix =
                    msg.type === "user"
                        ? React.createElement(Text, { bold: true }, "You:")
                        : msg.type === "agent"
                            ? React.createElement(Text, { bold: true, color: "blue" }, `${msg.agentName || "Agent"}:`)
                            : React.createElement(Text, { bold: true, color: "yellow" }, "");

                return React.createElement(
                    Box,
                    { flexDirection: "row", key: `msg-${idx}` },
                    React.createElement(
                        Box,
                        { width: 14 },
                        prefix
                    ),
                    React.createElement(Text, null, msg.content)
                );
            }),
            React.createElement(Text, null, ""),
            // Input
            React.createElement(TextInput, {
                value: inputValue,
                onSubmit: handleSubmit,
                isFocused: true,
            })
        );
    }

    // -----------------------------------------------------------------------
    // Render
    // -----------------------------------------------------------------------

    render(React.createElement(REPL), { exitOnCtrlC: true, patchConsole: false });
}

main().catch((err) => {
    console.error("Failed to start MindFlow CLI:", err);
    process.exit(1);
});