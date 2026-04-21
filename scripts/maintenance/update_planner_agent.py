import re
with open('python/mindflow_backend/agents/planner_agent.py', 'r') as f:
    content = f.read()

# Task 2: Token-Aware Context Summarization
# We'll update the _build_planning_messages function to be async and take the llm to do summarization if needed.

# Let's replace `_build_planning_messages` signature and calls.
content = content.replace(
    "planning_messages = self._build_planning_messages(request)",
    "planning_messages = await self._build_planning_messages(request, llm)"
)

new_func = """    async def _build_planning_messages(self, request: PlanningRequest, llm: Any) -> list[dict[str, str]]:
        \"\"\"Build the messages for the planning LLM call.\"\"\"
        messages = [
            {"role": "system", "content": self.system_prompt},
        ]
        
        # Add gathered context
        if request.context.strip():
            context_text = request.context
            estimated_tokens = len(context_text) // 4
            
            # Semantic summarization if context is too large
            if estimated_tokens > 12000:
                _logger.warning("planner_context_too_large", estimated_tokens=estimated_tokens)
                try:
                    summary_prompt = [
                        {"role": "system", "content": "You are a senior analyst. Summarize the following codebase context, keeping all technical details, file paths, and architectural decisions relevant to the user's request. Be highly concise."},
                        {"role": "user", "content": f"User Request: {request.message}\\n\\nContext (truncated): {context_text[:40000]}"}
                    ]
                    summary_response = await llm.ainvoke(summary_prompt)
                    context_text = summary_response.content if hasattr(summary_response, "content") else str(summary_response)
                except Exception as exc:
                    _logger.error("planner_context_summarization_failed", error=str(exc))
                    context_text = context_text[:32000] + "\\n\\n...[Context truncated due to size limits]..."
                
            messages.append({
                "role": "system",
                "content": f"## Gathered Context\\n\\n{context_text}",
            })
        
        # Add workspace info
        if request.folder_path:
            messages.append({
                "role": "system",
                "content": f"## Workspace Root\\n\\nThe working directory is: {request.folder_path}\\n\\nUse this path as the base for all file references in the plan.",
            })
        
        # Add complexity indicator
        complexity_note = ""
        if request.complexity_score >= 0.7:
            complexity_note = "\\n\\n**Note**: This is a HIGH complexity task. Consider breaking it into more granular subtasks."
        elif request.complexity_score >= 0.5:
            complexity_note = "\\n\\n**Note**: This is a MEDIUM complexity task. Plan accordingly."
        
        # Add the planning request
        messages.append({
            "role": "user",
            "content": f"Create a structured implementation plan for:\\n\\n**{request.message}**{complexity_note}\\n\\nFollow the planning protocol strictly. Output the plan in markdown format.",
        })
        
        return messages"""

old_func_regex = r"    def _build_planning_messages\(self, request: PlanningRequest\) -> list\[dict\[str, str\]\]:.*?(?=    def _parse_plan_response)"
content = re.sub(old_func_regex, new_func + "\n\n", content, flags=re.DOTALL)

with open('python/mindflow_backend/agents/planner_agent.py', 'w') as f:
    f.write(content)
