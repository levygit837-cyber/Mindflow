/**
 * MindFlow CLI - REPL Component
 * Main interactive interface with input handling.
 */

import React, { useState, useEffect } from "react";
import { Box, Text, useInput } from "ink";
import { renderChatHistory } from "../components/chat/ChatHistory";
import { renderTeamStatus } from "../components/agents/TeamStatus";
import { renderInputBar } from "../components/input/InputBar";
import { getState } from "../state/store";
import type { Message } from "../types";
import { useMindFlowState } from "../hooks/useMindFlowState";

export default function REPL() {
    const state = useMindFlowState();
    const [inputValue, setInputValue] = useState("");

    useInput((input, key) => {
        if (key.return) {
            if (inputValue.trim()) {
                handleInput(inputValue.trim());
            }
            setInputValue("");
            return;
        }

        if (input === "\b" || input === "\x7F") {
            setInputValue((prev) => prev.slice(0, -1));
            return;
        }

        if (input.length === 1 && !key.ctrl && !key.meta) {
            setInputValue((prev) => prev + input);
        }
    });

    function handleInput(text: string) {
        // Handle local commands
        if (text === "/exit" || text === "/quit") {
            process.exit(0);
        }
        if (text === "/help") {
            console.log("Available commands: /help, /exit, /clear, /team, /missions");
            return;
        }
        if (text === "/clear") {
            return;
        }

        // For now, echo back the input as a user message
        const msg: Message = {
            id: String(Date.now()),
            type: "user",
            content: text,
            timestamp: new Date(),
        };

        console.log(renderChatHistory({ messages: [msg] }));
    }

    function getGreeting(): string {
        const hour = new Date().getHours();
        const period =
            hour < 12
                ? "Morning"
                : hour < 18
                    ? "Afternoon"
                    : "Evening";
        return `Good ${period}! MindFlow CLI ready.`;
    }

    return React.createElement(
        Box,
        { flexDirection: "column", flexGrow: 1 },
        React.createElement(
            Box,
            { flexDirection: "row", justifyContent: "space-between" },
            React.createElement(Text, { bold: true, color: "cyan" }, "MindFlow CLI"),
            React.createElement(Text, { dimColor: true }, "/help for commands")
        ),
        React.createElement(Text, { dimColor: true }, "\n" + getGreeting() + "\n"),
        // Team status
        state.activeAgents.length > 0
            ? React.createElement(Text, { color: "yellow" }, renderTeamStatus({ agents: state.activeAgents }))
            : null,
        // Chat history placeholder
        state.messages.length === 0
            ? React.createElement(Text, { dimColor: true }, "No messages yet. Type a message to begin.")
            : null,
        // Input bar
        React.createElement(
            Box,
            { flexDirection: "row", marginTop: 1 },
            React.createElement(Text, { bold: true, color: "green" }, renderInputBar(state.isProcessing)),
            React.createElement(Text, null, inputValue + " ")
        )
    );
}