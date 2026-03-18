from __future__ import annotations

from typing import Any, Dict, List
from enum import Enum
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree
from rich.columns import Columns
from rich.layout import Layout
from rich.live import Live
from rich.spinner import Spinner
from rich.progress import Progress, BarColumn, TextColumn
from rich.rule import Rule
from rich.align import Align
from rich.syntax import Syntax
from rich.filesize import decimal

from mindflow_backend.schemas.agent import StreamEvent
from mindflow_backend.schemas.orchestration.orchestrator import OrchestratorDecision, AgentType
from mindflow_cli.render.chat_stream import ChatStreamRenderer
from mindflow_cli.render.theme import MINDFLOW_THEME


class MessageRole(Enum):
    """Message roles for visual differentiation."""
    ORCHESTRATOR = "orchestrator"
    SPECIALIST = "specialist"
    CORE_SPECIALIST = "core_specialist"


class ToolOperationType(Enum):
    """Types of tool operations."""
    READ = "read"
    WRITE = "write"
    CREATE = "create"
    DELETE = "delete"
    EXECUTE = "execute"
    SEARCH = "search"


class AgentDelegationState(Enum):
    """Agent delegation states."""
    NOT_DELEGATED = "not_delegated"
    DELEGATED = "delegated"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class ToolOperation:
    """Represents a tool operation with file changes."""
    
    def __init__(self, operation_type: ToolOperationType, file_path: str, 
                 content: str = "", old_content: str = "", timestamp: datetime = None):
        self.operation_type = operation_type
        self.file_path = file_path
        self.content = content
        self.old_content = old_content
        self.timestamp = timestamp or datetime.now()
        self.agent = ""
        self.success = False
        self.error_message = ""


class AgentDelegationInfo:
    """Information about agent delegation state."""
    
    def __init__(self, agent_type: str, delegated_by: str = "", task: str = ""):
        self.agent_type = agent_type
        self.delegated_by = delegated_by
        self.task = task
        self.state = AgentDelegationState.NOT_DELEGATED
        self.start_time = None
        self.end_time = None
        self.tool_operations: List[ToolOperation] = []
        self.current_operation: ToolOperation = None


THOUGHT_SUMMARY_MAX_CHARS = 120


def _summarize_thought(thought: str, max_chars: int = THOUGHT_SUMMARY_MAX_CHARS) -> str:
    """Summarize agent thought for UI: first line or first N chars."""
    if not thought or len(thought.strip()) <= max_chars:
        return (thought or "").strip()
    first_line = thought.split("\n")[0].strip()
    if len(first_line) <= max_chars:
        return first_line
    return first_line[: max_chars - 3].rstrip() + "..."


class OrchestratorStreamRenderer(ChatStreamRenderer):
    """Enhanced stream renderer for orchestrator flows with decision visualization."""
    
    def __init__(self, console: Console) -> None:
        super().__init__(console)
        self._orchestrator_info = {}
        self._decision_tree = None
        self._agent_execution_log = []
        self._routing_analysis = None
        self._current_agent_role = MessageRole.ORCHESTRATOR
        self._reflection_mode = False
        self._orchestrator_thinking_live = None
        self._step_progress = None
        
        # Tool and delegation tracking
        self._agent_delegations: Dict[str, AgentDelegationInfo] = {}
        self._tool_operations: List[ToolOperation] = []
        self._active_tool_operation: ToolOperation = None
        self._file_changes_live: Live = None
        
    def _get_agent_style(self, agent_type: str, role: MessageRole) -> str:
        """Get styling for different agent types and roles."""
        base_styles = {
            "orchestrator": "bold gold",
            "coder": "bold green", 
            "analyst": "bold blue",
            "researcher": "bold cyan",
            "unknown": "bold white"
        }
        
        # Enhanced styles based on role
        if role == MessageRole.ORCHESTRATOR:
            return "bold gold3"  # Gold for orchestrator - central figure
        elif role == MessageRole.SPECIALIST:
            return f"{base_styles.get(agent_type.lower(), 'white')} italic"
        elif role == MessageRole.CORE_SPECIALIST:
            return f"{base_styles.get(agent_type.lower(), 'white')} bold underline"
        else:
            return base_styles.get(agent_type.lower(), "white")
    
    def _get_agent_prefix(self, agent_type: str, role: MessageRole) -> str:
        """Get visual prefix for different agent roles."""
        if role == MessageRole.ORCHESTRATOR:
            return "🎯 ORQ"  # Orchestrator - central figure
        elif role == MessageRole.SPECIALIST:
            return f"👤 {agent_type.upper()}"  # Specialist agent
        elif role == MessageRole.CORE_SPECIALIST:
            return f"⭐ {agent_type.upper()}"  # Core specialist
        else:
            return f"🤖 {agent_type.upper()}"
    
    def render_orchestrator_thinking_start(self) -> None:
        """Start streaming orchestrator thinking process."""
        self._ensure_response_line_closed()
        
        # Create live thinking display
        thinking_text = Text("🧠 Analyzing request and planning strategy...", style="bold gold3")
        spinner = Spinner("dots", text=thinking_text, style="gold3")
        
        self._orchestrator_thinking_live = Live(
            spinner,
            console=self.console,
            transient=True,
            refresh_per_second=4
        )
        self._orchestrator_thinking_live.start()
    
    def render_orchestrator_thinking_update(self, thought: str) -> None:
        """Update orchestrator thinking stream (summarized)."""
        if self._orchestrator_thinking_live:
            summary = _summarize_thought(thought)
            thinking_text = Text(f"🧠 {summary}", style="gold3")
            spinner = Spinner("dots", text=thinking_text, style="gold3")
            self._orchestrator_thinking_live.update(spinner)
    
    def render_orchestrator_thinking_end(self) -> None:
        """End orchestrator thinking stream."""
        if self._orchestrator_thinking_live:
            self._orchestrator_thinking_live.stop()
            self._orchestrator_thinking_live = None
            self.console.print("✅ Analysis complete", style="bold green")
    
    def render_reflection_mode_start(self) -> None:
        """Start reflection mode visual indication."""
        self._reflection_mode = True
        self._ensure_response_line_closed()
        
        reflection_panel = Panel(
            Text("🔄 REFLECTION MODE - Delegating task analysis", style="bold cyan"),
            title="🧠 Orchestrator Reflection",
            border_style="cyan",
            padding=(1, 2)
        )
        self.console.print(reflection_panel)
    
    def render_reflection_mode_end(self) -> None:
        """End reflection mode visual indication."""
        if self._reflection_mode:
            self._reflection_mode = False
            self.console.print("✅ Reflection complete - Task delegated", style="bold cyan")
    
    def _decision_val(self, decision: Any, key: str, default: str = "") -> str:
        """Get a decision field value from either an object or a dict (JSON)."""
        if isinstance(decision, dict):
            v = decision.get(key, default)
            return getattr(v, "value", v) if hasattr(v, "value") else str(v) if v is not None else default
        v = getattr(decision, key, None)
        return getattr(v, "value", v) if v is not None and hasattr(v, "value") else str(v) if v else default

    def render_orchestrator_decision(self, decision: OrchestratorDecision | Dict[str, Any]) -> None:
        """Render orchestrator decision with enhanced central figure visualization."""
        self._ensure_response_line_closed()
        self._current_agent_role = MessageRole.ORCHESTRATOR

        agent = self._decision_val(decision, "agent", "CODER")
        priority = self._decision_val(decision, "priority", "NORMAL")
        thinking = self._decision_val(decision, "thinking_level") or self._decision_val(decision, "thinking", "MEDIUM")
        tool_scope = self._decision_val(decision, "tool_scope")
        if not tool_scope:
            tools = decision.get("tools", []) if isinstance(decision, dict) else getattr(decision, "tools", [])
            tool_scope = f"{len(tools)} tools" if tools else "—"
        thinking_mode = self._decision_val(decision, "thinking_mode", "")

        # Create enhanced decision panel with central figure emphasis
        decision_content = Text()
        decision_content.append("🎯 ORCHESTRATOR DECISION\n\n", style="bold gold3 underline")
        decision_content.append("📋 Task Analysis Complete\n", style="bold white")
        decision_content.append(f"🎯 Selected Agent: {agent}\n", style="bold green")
        decision_content.append(f"⚡ Priority: {priority}\n", style="cyan")
        decision_content.append(f"🧠 Thinking Level: {thinking}\n", style="blue")
        decision_content.append(f"🔧 Tool Scope: {tool_scope}\n", style="magenta")

        if thinking_mode:
            mode_style = "bold yellow" if thinking_mode == "DECOMPOSITION" else "yellow"
            decision_content.append(f"🔄 Thinking Mode: {thinking_mode}\n", style=mode_style)
        
        # Add visual hierarchy
        self.console.print(Rule(style="gold3"))
        self.console.print(Panel(
            decision_content,
            title="🧠 CENTRAL ORCHESTRATOR",
            border_style="gold3",
            padding=(1, 2)
        ))
        self.console.print(Rule(style="gold3"))
        
        self._orchestrator_info["decision"] = decision
    
    def render_specialist_activation(self, agent_type: str, is_core: bool = False) -> None:
        """Render specialist agent activation with clear differentiation."""
        self._ensure_response_line_closed()
        
        # Set role based on agent type
        self._current_agent_role = MessageRole.CORE_SPECIALIST if is_core else MessageRole.SPECIALIST
        
        prefix = self._get_agent_prefix(agent_type, self._current_agent_role)
        style = self._get_agent_style(agent_type, self._current_agent_role)
        
        # Create specialist activation panel
        specialist_text = Text()
        specialist_text.append(f"{prefix} ACTIVATED\n\n", style=style)
        specialist_text.append(f"Role: {'Core Specialist' if is_core else 'Specialist Agent'}\n", style="white")
        specialist_text.append(f"Specialization: {self._get_specialization_description(agent_type)}\n", style="cyan")
        
        border_style = "bright_green" if is_core else "green"
        title = "⭐ CORE SPECIALIST" if is_core else "👤 SPECIALIST AGENT"
        
        self.console.print(Panel(
            specialist_text,
            title=title,
            border_style=border_style,
            padding=(1, 2)
        ))
    
    def render_specialist_thinking(self, agent_type: str, thought: str, is_core: bool = False) -> None:
        """Render specialist agent thinking with role differentiation (summarized)."""
        summary = _summarize_thought(thought)
        prefix = self._get_agent_prefix(agent_type, self._current_agent_role)
        style = self._get_agent_style(agent_type, self._current_agent_role)
        
        # Different thinking style for specialists vs orchestrator
        thinking_prefix = "💭" if not is_core else "⭐💭"
        
        self.console.print(Text(f"{thinking_prefix} {prefix}: {summary}", style=style))
    
    def render_orchestrator_step(self, step_description: str, step_number: int, total_steps: int) -> None:
        """Render orchestrator step with progress tracking."""
        self._ensure_response_line_closed()
        self._current_agent_role = MessageRole.ORCHESTRATOR
        
        # Create progress bar for orchestrator steps
        progress_text = Text(f"🎯 ORQ Step {step_number}/{total_steps}: {step_description}", style="bold gold3")
        
        # Simple progress visualization
        progress_bar = "█" * step_number + "░" * (total_steps - step_number)
        progress_display = Text(f"[{progress_bar}] {step_number}/{total_steps}", style="gold3")
        
        self.console.print(progress_text)
        self.console.print(progress_display)
    
    def render_agent_step(self, agent_type: str, step_description: str, step_number: int, is_core: bool = False) -> None:
        """Render specialist agent step with role differentiation."""
        self._current_agent_role = MessageRole.CORE_SPECIALIST if is_core else MessageRole.SPECIALIST
        prefix = self._get_agent_prefix(agent_type, self._current_agent_role)
        style = self._get_agent_style(agent_type, self._current_agent_role)
        
        step_icon = "⭐" if is_core else "👤"
        step_text = Text(f"{step_icon} {prefix} Step {step_number}: {step_description}", style=style)
        
        self.console.print(step_text)
    
    def _get_specialization_description(self, agent_type: str) -> str:
        """Get specialization description for agent types."""
        descriptions = {
            "CODER": "Code implementation, debugging, architecture",
            "ANALYST": "Code analysis, security audits, review",
            "RESEARCHER": "Web search, documentation, research",
            "ORCHESTRATOR": "Multi-agent coordination, session management"
        }
        return descriptions.get(agent_type.upper(), "General purpose tasks")
    
    def render_agent_delegation_start(self, agent_type: str, delegated_by: str, task: str) -> None:
        """Render the start of agent delegation with tracking."""
        self._ensure_response_line_closed()
        
        # Create delegation info
        delegation_info = AgentDelegationInfo(agent_type, delegated_by, task)
        delegation_info.state = AgentDelegationState.DELEGATED
        delegation_info.start_time = datetime.now()
        self._agent_delegations[agent_type] = delegation_info
        
        # Get styling based on agent role
        role = self._current_agent_role
        prefix = self._get_agent_prefix(agent_type, role)
        style = self._get_agent_style(agent_type, role)
        
        # Create delegation panel
        delegation_text = Text()
        delegation_text.append(f"{prefix} DELEGATED\n\n", style=style)
        delegation_text.append(f"Delegated by: {delegated_by}\n", style="white")
        delegation_text.append(f"Task: {task}\n", style="cyan")
        delegation_text.append(f"Status: 🔄 Executing\n", style="yellow")
        delegation_text.append(f"Started: {delegation_info.start_time.strftime('%H:%M:%S')}\n", style="dim")
        
        border_style = "bright_green" if role == MessageRole.CORE_SPECIALIST else "green"
        title = f"⭐ {agent_type.upper()} DELEGATION" if role == MessageRole.CORE_SPECIALIST else f"👤 {agent_type.upper()} DELEGATION"
        
        self.console.print(Panel(
            delegation_text,
            title=title,
            border_style=border_style,
            padding=(1, 2)
        ))
    
    def render_agent_delegation_complete(self, agent_type: str, success: bool = True, error_message: str = "") -> None:
        """Render the completion of agent delegation."""
        self._ensure_response_line_closed()
        
        if agent_type not in self._agent_delegations:
            return
            
        delegation_info = self._agent_delegations[agent_type]
        delegation_info.end_time = datetime.now()
        delegation_info.state = AgentDelegationState.COMPLETED if success else AgentDelegationState.FAILED
        
        # Calculate execution time
        execution_time = delegation_info.end_time - delegation_info.start_time
        
        role = self._current_agent_role
        prefix = self._get_agent_prefix(agent_type, role)
        style = self._get_agent_style(agent_type, role)
        
        # Create completion panel
        completion_text = Text()
        completion_text.append(f"{prefix} TASK COMPLETE\n\n", style=style)
        
        if success:
            completion_text.append(f"Status: ✅ Success\n", style="bold green")
            completion_text.append(f"Execution Time: {execution_time.total_seconds():.2f}s\n", style="white")
            completion_text.append(f"Tool Operations: {len(delegation_info.tool_operations)}\n", style="cyan")
        else:
            completion_text.append(f"Status: ❌ Failed\n", style="bold red")
            completion_text.append(f"Error: {error_message}\n", style="red")
            completion_text.append(f"Execution Time: {execution_time.total_seconds():.2f}s\n", style="white")
        
        completion_text.append(f"Completed: {delegation_info.end_time.strftime('%H:%M:%S')}\n", style="dim")
        
        border_style = "green" if success else "red"
        
        self.console.print(Panel(
            completion_text,
            title=f"{prefix} COMPLETION",
            border_style=border_style,
            padding=(1, 2)
        ))
        
        # Show tool operations summary if any
        if delegation_info.tool_operations:
            self.render_tool_operations_summary(agent_type, delegation_info.tool_operations)
    
    def render_tool_operation_start(self, tool_name: str, operation_type: str, file_path: str, agent_type: str) -> None:
        """Render the start of a tool operation with live tracking."""
        self._ensure_response_line_closed()
        
        # Create tool operation
        op_type = ToolOperationType(operation_type.lower())
        operation = ToolOperation(op_type, file_path)
        operation.agent = agent_type
        self._active_tool_operation = operation
        
        # Add to delegation tracking
        if agent_type in self._agent_delegations:
            self._agent_delegations[agent_type].current_operation = operation
            self._agent_delegations[agent_type].tool_operations.append(operation)
        
        # Get operation icon and color
        operation_icons = {
            ToolOperationType.READ: ("📖", "blue"),
            ToolOperationType.WRITE: ("✏️", "green"),
            ToolOperationType.CREATE: ("📝", "yellow"),
            ToolOperationType.DELETE: ("🗑️", "red"),
            ToolOperationType.EXECUTE: ("⚡", "magenta"),
            ToolOperationType.SEARCH: ("🔍", "cyan")
        }
        
        icon, color = operation_icons.get(op_type, ("🔧", "white"))
        
        # Create live operation display
        operation_text = Text(f"{icon} {agent_type} {operation_type.upper()}: {file_path}", style=color)
        spinner = Spinner("dots", text=operation_text, style=color)
        
        self._file_changes_live = Live(
            spinner,
            console=self.console,
            transient=True,
            refresh_per_second=4
        )
        self._file_changes_live.start()
    
    def render_tool_operation_update(self, update_message: str) -> None:
        """Update the current tool operation with progress."""
        if self._file_changes_live and self._active_tool_operation:
            operation = self._active_tool_operation
            op_type = operation.operation_type
            
            operation_icons = {
                ToolOperationType.READ: ("📖", "blue"),
                ToolOperationType.WRITE: ("✏️", "green"),
                ToolOperationType.CREATE: ("📝", "yellow"),
                ToolOperationType.DELETE: ("🗑️", "red"),
                ToolOperationType.EXECUTE: ("⚡", "magenta"),
                ToolOperationType.SEARCH: ("🔍", "cyan")
            }
            
            icon, color = operation_icons.get(op_type, ("🔧", "white"))
            operation_text = Text(f"{icon} {operation.agent} {op_type.value.upper()}: {operation.file_path} - {update_message}", style=color)
            spinner = Spinner("dots", text=operation_text, style=color)
            
            self._file_changes_live.update(spinner)
    
    def render_tool_operation_complete(self, success: bool = True, content: str = "", error_message: str = "") -> None:
        """Complete the current tool operation and show file changes."""
        if not self._active_tool_operation:
            return
            
        operation = self._active_tool_operation
        operation.success = success
        operation.content = content
        operation.error_message = error_message
        
        # Stop live display
        if self._file_changes_live:
            self._file_changes_live.stop()
            self._file_changes_live = None
        
        # Show operation result
        op_type = operation.operation_type
        operation_icons = {
            ToolOperationType.READ: ("📖", "blue"),
            ToolOperationType.WRITE: ("✏️", "green"),
            ToolOperationType.CREATE: ("📝", "yellow"),
            ToolOperationType.DELETE: ("🗑️", "red"),
            ToolOperationType.EXECUTE: ("⚡", "magenta"),
            ToolOperationType.SEARCH: ("🔍", "cyan")
        }
        
        icon, color = operation_icons.get(op_type, ("🔧", "white"))
        
        if success:
            status_icon = "✅"
            status_color = "green"
            self.console.print(Text(f"{status_icon} {icon} {operation.agent} {op_type.value.upper()} COMPLETE: {operation.file_path}", style=status_color))
            
            # Show file content for read operations
            if op_type == ToolOperationType.READ and content:
                self.render_file_content_preview(operation.file_path, content)
            # Show diff for write operations
            elif op_type in [ToolOperationType.WRITE, ToolOperationType.CREATE] and content:
                self.render_file_diff(operation.file_path, operation.old_content, content)
        else:
            status_icon = "❌"
            status_color = "red"
            self.console.print(Text(f"{status_icon} {icon} {operation.agent} {op_type.value.upper()} FAILED: {operation.file_path}", style=status_color))
            if error_message:
                self.console.print(Text(f"   Error: {error_message}", style="dim red"))
        
        # Clear active operation
        self._active_tool_operation = None
    
    def render_file_content_preview(self, file_path: str, content: str) -> None:
        """Render a preview of file content for read operations."""
        self._ensure_response_line_closed()
        
        # Limit content for preview
        max_lines = 20
        max_chars = 1000
        
        lines = content.split('\n')
        preview_lines = lines[:max_lines]
        preview_content = '\n'.join(preview_lines)
        
        if len(preview_content) > max_chars:
            preview_content = preview_content[:max_chars] + "..."
        
        if len(lines) > max_lines:
            preview_content += f"\n... ({len(lines) - max_lines} more lines)"
        
        # Determine file type for syntax highlighting
        file_extension = file_path.split('.')[-1].lower() if '.' in file_path else ''
        syntax_map = {
            'py': 'python',
            'js': 'javascript',
            'ts': 'typescript',
            'html': 'html',
            'css': 'css',
            'json': 'json',
            'md': 'markdown',
            'yaml': 'yaml',
            'yml': 'yaml',
            'sql': 'sql'
        }
        
        lexer = syntax_map.get(file_extension, 'text')
        
        try:
            syntax = Syntax(preview_content, lexer, theme="monokai", line_numbers=True)
        except:
            # Fallback to plain text if syntax highlighting fails
            syntax = Text(preview_content, style="dim")
        
        self.console.print(Panel(
            syntax,
            title=f"📖 File Preview: {file_path}",
            border_style="blue",
            padding=(1, 1)
        ))
    
    def render_file_diff(self, file_path: str, old_content: str, new_content: str) -> None:
        """Render a file diff for write/create operations."""
        self._ensure_response_line_closed()
        
        # Create a simple diff visualization
        diff_text = Text()
        
        if old_content:
            diff_text.append("─" * 40 + " OLD CONTENT " + "─" * 40 + "\n", style="dim red")
            diff_text.append(Text(old_content[:500] + ("..." if len(old_content) > 500 else ""), style="red"))
            diff_text.append("\n")
        
        diff_text.append("─" * 40 + " NEW CONTENT " + "─" * 40 + "\n", style="dim green")
        diff_text.append(Text(new_content[:500] + ("..." if len(new_content) > 500 else ""), style="green"))
        
        self.console.print(Panel(
            diff_text,
            title=f"✏️ File Changes: {file_path}",
            border_style="green",
            padding=(1, 1)
        ))
    
    def render_tool_operations_summary(self, agent_type: str, operations: List[ToolOperation]) -> None:
        """Render a summary of all tool operations performed by an agent."""
        self._ensure_response_line_closed()
        
        if not operations:
            return
        
        # Create summary table
        table = Table(title=f"🔧 {agent_type} Tool Operations Summary", show_header=True, header_style="bold cyan")
        table.add_column("Operation", style="bold", no_wrap=True)
        table.add_column("File", style="white")
        table.add_column("Status", style="bold")
        table.add_column("Size", style="dim", no_wrap=True)
        
        for op in operations:
            # Get operation icon
            operation_icons = {
                ToolOperationType.READ: "📖",
                ToolOperationType.WRITE: "✏️",
                ToolOperationType.CREATE: "📝",
                ToolOperationType.DELETE: "🗑️",
                ToolOperationType.EXECUTE: "⚡",
                ToolOperationType.SEARCH: "🔍"
            }
            
            icon = operation_icons.get(op.operation_type, "🔧")
            
            # Status
            status = "✅ Success" if op.success else "❌ Failed"
            status_style = "green" if op.success else "red"
            
            # File size
            size = f"{len(op.content)} chars" if op.content else "0 chars"
            
            table.add_row(
                f"{icon} {op.operation_type.value.upper()}",
                op.file_path,
                Text(status, style=status_style),
                size
            )
        
        self.console.print(table)
    
    def render_routing_analysis(self, analysis: dict[str, Any]) -> None:
        """Render routing analysis with detailed breakdown."""
        self._ensure_response_line_closed()
        
        # Create routing analysis table
        table = Table(title="🔀 Routing Analysis", show_header=True, header_style="bold cyan")
        table.add_column("Aspect", style="bold", no_wrap=True)
        table.add_column("Analysis", style="white")
        table.add_column("Confidence", style="green")
        
        # Extract analysis data
        user_intent = analysis.get("user_intent", "Not analyzed")
        needs_context = analysis.get("needs_code_context", False)
        recommended_agent = analysis.get("recommended_agent", "UNKNOWN")
        confidence = analysis.get("confidence", 0.0)
        is_multi_agent = analysis.get("is_multi_agent", False)
        
        # Add rows
        table.add_row(
            "User Intent",
            user_intent[:100] + "..." if len(user_intent) > 100 else user_intent,
            f"{confidence:.2f}"
        )
        
        table.add_row(
            "Code Context Needed",
            "Yes" if needs_context else "No",
            "High" if needs_context else "Low"
        )
        
        table.add_row(
            "Recommended Agent",
            recommended_agent,
            f"{confidence:.2f}"
        )
        
        table.add_row(
            "Multi-Agent Task",
            "Yes" if is_multi_agent else "No",
            "Medium"
        )
        
        if is_multi_agent and analysis.get("agent_sequence"):
            sequence = " → ".join(analysis["agent_sequence"])
            table.add_row("Agent Sequence", sequence, "High")
        
        self.console.print(table)
        self._routing_analysis = analysis
    
    def render_agent_execution_start(self, agent_type: str, execution_context: dict[str, Any]) -> None:
        """Render the start of agent execution with context."""
        self._ensure_response_line_closed()
        
        # Create agent execution panel
        agent_text = Text()
        agent_text.append(f"🤖 {agent_type.upper()} Agent Activated\n", style="bold green")
        
        # Add execution context
        if "provider" in execution_context:
            agent_text.append(f"Provider: {execution_context['provider']}\n", style="cyan")
        if "model" in execution_context:
            agent_text.append(f"Model: {execution_context['model']}\n", style="cyan")
        if "tools_enabled" in execution_context:
            tools_status = "✅" if execution_context["tools_enabled"] else "❌"
            agent_text.append(f"Tools: {tools_status}\n", style="yellow")
        if "sandbox_mode" in execution_context:
            agent_text.append(f"Sandbox: {execution_context['sandbox_mode']}\n", style="magenta")
        
        self.console.print(Panel(
            agent_text,
            title=f"🚀 Agent Execution: {agent_type}",
            border_style="green",
            padding=(1, 2)
        ))
        
        # Log execution
        self._agent_execution_log.append({
            "agent": agent_type,
            "start_time": execution_context.get("timestamp"),
            "context": execution_context
        })
    
    def render_execution_trace(self, trace_data: dict[str, Any]) -> None:
        """Render detailed execution trace for debugging."""
        self._ensure_response_line_closed()
        
        # Create trace tree
        tree = Tree("🔍 Execution Trace", guide_style="bold blue")
        
        # Add main branches
        if "routing" in trace_data:
            routing_branch = tree.add("🔀 Routing Phase", style="cyan")
            routing_data = trace_data["routing"]
            
            if "decision_time" in routing_data:
                routing_branch.add(f"Decision Time: {routing_data['decision_time']:.2f}s", style="dim")
            if "alternatives_considered" in routing_data:
                for alt in routing_data["alternatives_considered"]:
                    routing_branch.add(f"Alternative: {alt}", style="dim")
        
        if "agent_execution" in trace_data:
            agent_branch = tree.add("🤖 Agent Execution", style="green")
            agent_data = trace_data["agent_execution"]
            
            if "llm_calls" in agent_data:
                llm_branch = agent_branch.add("📞 LLM Calls", style="yellow")
                for i, call in enumerate(agent_data["llm_calls"], 1):
                    llm_branch.add(f"Call {i}: {call.get('duration', 0):.2f}s", style="dim")
            
            if "tool_calls" in agent_data:
                tool_branch = agent_branch.add("🔧 Tool Calls", style="magenta")
                for tool in agent_data["tool_calls"]:
                    tool_branch.add(f"Tool: {tool.get('name', 'unknown')}", style="dim")
        
        if "memory" in trace_data:
            memory_branch = tree.add("🧠 Memory Operations", style="blue")
            memory_data = trace_data["memory"]
            
            if "retrieved_context" in memory_data:
                memory_branch.add(f"Context Retrieved: {len(memory_data['retrieved_context'])} chars", style="dim")
            if "session_updated" in memory_data:
                memory_branch.add("Session Updated: ✅", style="green")
        
        self.console.print(tree)
    
    def render_multi_agent_flow(self, flow_data: dict[str, Any]) -> None:
        """Render multi-agent coordination flow."""
        self._ensure_response_line_closed()
        
        # Create flow visualization
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="flow"),
            Layout(name="footer", size=3)
        )
        
        # Header
        layout["header"].update(Panel(
            Text("🔄 Multi-Agent Coordination Flow", style="bold yellow"),
            border_style="yellow"
        ))
        
        # Flow visualization
        flow_text = Text()
        agents = flow_data.get("agents", [])
        for i, agent in enumerate(agents):
            if i > 0:
                flow_text.append(" → ", style="cyan")
            flow_text.append(agent.upper(), style=f"bold {self._get_agent_color(agent)}")
        
        layout["flow"].update(Panel(
            flow_text,
            title="Agent Sequence",
            border_style="cyan"
        ))
        
        # Footer with summary
        summary = f"Total Agents: {len(agents)} | Total Time: {flow_data.get('total_time', 0):.2f}s"
        layout["footer"].update(Panel(
            Text(summary, style="dim"),
            border_style="dim"
        ))
        
        self.console.print(layout)
    
    def render_performance_metrics(self, metrics: dict[str, Any]) -> None:
        """Render performance metrics for the execution."""
        self._ensure_response_line_closed()
        
        # Create metrics table
        table = Table(title="📊 Performance Metrics", show_header=True, header_style="bold cyan")
        table.add_column("Metric", style="bold", no_wrap=True)
        table.add_column("Value", style="white")
        table.add_column("Status", style="green")
        
        # Add metrics
        metrics_to_show = [
            ("Total Execution Time", f"{metrics.get('total_time', 0):.2f}s", "✅"),
            ("Routing Decision Time", f"{metrics.get('routing_time', 0):.2f}s", "✅"),
            ("Agent Execution Time", f"{metrics.get('agent_time', 0):.2f}s", "✅"),
            ("LLM Calls", str(metrics.get('llm_calls', 0)), "✅"),
            ("Tool Calls", str(metrics.get('tool_calls', 0)), "✅"),
            ("Tokens Used", str(metrics.get('tokens_used', 0)), "✅"),
        ]
        
        for metric, value, status in metrics_to_show:
            table.add_row(metric, value, status)
        
        self.console.print(table)
    
    def render_session_summary(self, session_data: dict[str, Any]) -> None:
        """Render session summary and statistics."""
        self._ensure_response_line_closed()
        
        # Create summary layout
        layout = Layout()
        layout.split_row(
            Layout(name="agents", ratio=1),
            Layout(name="metrics", ratio=1),
            Layout(name="timeline", ratio=2)
        )
        
        # Agents used
        agents_text = Text()
        agents_used = session_data.get("agents_used", [])
        for agent in agents_used:
            agents_text.append(f"• {agent}\n", style=self._get_agent_color(agent))
        
        layout["agents"].update(Panel(
            agents_text,
            title="🤖 Agents Used",
            border_style="green"
        ))
        
        # Key metrics
        metrics_text = Text()
        metrics_text.append(f"Messages: {session_data.get('message_count', 0)}\n", style="white")
        metrics_text.append(f"Decisions: {session_data.get('decision_count', 0)}\n", style="white")
        metrics_text.append(f"Total Time: {session_data.get('total_time', 0):.2f}s\n", style="white")
        
        layout["metrics"].update(Panel(
            metrics_text,
            title="📈 Session Stats",
            border_style="cyan"
        ))
        
        # Timeline
        timeline_text = Text()
        events = session_data.get("events", [])
        for event in events[:5]:  # Show last 5 events
            timestamp = event.get("timestamp", "")
            action = event.get("action", "")
            timeline_text.append(f"{timestamp}: {action}\n", style="dim")
        
        layout["timeline"].update(Panel(
            timeline_text,
            title="⏰ Recent Activity",
            border_style="yellow"
        ))
        
        self.console.print(layout)
    
    def _get_agent_color(self, agent_type: str) -> str:
        """Get color for agent type."""
        agent_colors = {
            "CODER": "green",
            "ANALYST": "blue", 
            "RESEARCHER": "cyan",
            "ORCHESTRATOR": "yellow"
        }
        return agent_colors.get(agent_type.upper(), "white")

    def _render_notifier(self, kind: str, message: str, details: Dict[str, Any]) -> None:
        """Render a flexible notifier (kind, message, details). Any info to show in the UI."""
        self._ensure_response_line_closed()
        kind_lower = (kind or "info").lower()
        icons = {
            "file_read": ("📖", "blue"),
            "file_write": ("✏️", "green"),
            "file_create": ("📝", "yellow"),
            "file_edit": ("✏️", "green"),
            "file_delete": ("🗑️", "red"),
            "gitnexus_status": ("🧭", "magenta"),
            "gitnexus_query": ("🧠", "magenta"),
            "gitnexus_context": ("🧩", "cyan"),
            "gitnexus_impact": ("💥", "yellow"),
            "tool_start": ("🔧", "magenta"),
            "tool_end": ("✅", "green"),
            "context_loaded": ("📎", "cyan"),
            "search_done": ("🔍", "cyan"),
            "decision": ("🎯", "yellow"),
            "warning": ("⚠️", "yellow"),
            "info": ("ℹ️", "dim"),
        }
        icon, style = icons.get(kind_lower, ("ℹ️", "dim"))
        self.console.print(Text(f"  {icon} ", style=style), end="")
        self.console.print(Text(message, style=style or "white"))
        if details:
            parts = []
            for k, v in list(details.items())[:5]:
                if v is not None and str(v).strip():
                    parts.append(f"{k}={v}")
            if parts:
                self.console.print(Text(f"      " + " | ".join(parts), style="dim"))
    
    def render(self, event: StreamEvent) -> None:
        """Override render to handle orchestrator-specific events with enhanced UI/UX."""
        
        # Handle orchestrator thinking events
        if event.type == "orchestrator_thinking_start":
            self.render_orchestrator_thinking_start()
            return
        
        elif event.type == "orchestrator_thinking":
            self.render_orchestrator_thinking_update(event.data)
            return
        
        elif event.type == "orchestrator_thinking_end":
            self.render_orchestrator_thinking_end()
            return
        
        # Handle reflection mode events
        elif event.type == "reflection_mode_start":
            self.render_reflection_mode_start()
            return
        
        elif event.type == "reflection_mode_end":
            self.render_reflection_mode_end()
            return
        
        # Handle orchestrator decision with enhanced visualization
        elif event.type == "orchestrator_decision":
            try:
                import json
                decision_data = json.loads(event.data)
                self.render_orchestrator_decision(decision_data)
            except:
                self.console.print(f"[gold3]🎯 ORCHESTRATOR DECISION: {event.data}[/]")
            return
        
        # Handle agent delegation events
        elif event.type == "agent_delegation_start":
            try:
                import json
                data = json.loads(event.data)
                agent_type = data.get("agent_type", "UNKNOWN")
                delegated_by = data.get("delegated_by", "ORCHESTRATOR")
                task = data.get("task", "")
                self.render_agent_delegation_start(agent_type, delegated_by, task)
            except:
                self.console.print(f"[green]👤 AGENT DELEGATED: {event.data}[/]")
            return
        
        elif event.type == "agent_delegation_complete":
            try:
                import json
                data = json.loads(event.data)
                agent_type = data.get("agent_type", "UNKNOWN")
                success = data.get("success", True)
                error_message = data.get("error_message", "")
                self.render_agent_delegation_complete(agent_type, success, error_message)
            except:
                self.console.print(f"[green]✅ AGENT COMPLETE: {event.data}[/]")
            return
        
        # Handle tool operation events
        elif event.type == "tool_operation_start":
            try:
                import json
                data = json.loads(event.data)
                tool_name = data.get("tool_name", "UNKNOWN")
                operation_type = data.get("operation_type", "read")
                file_path = data.get("file_path", "")
                agent_type = data.get("agent_type", "UNKNOWN")
                self.render_tool_operation_start(tool_name, operation_type, file_path, agent_type)
            except:
                self.console.print(f"[blue]🔧 TOOL START: {event.data}[/]")
            return
        
        elif event.type == "tool_operation_update":
            try:
                data = json.loads(event.data)
                update_message = data.get("update", "")
                self.render_tool_operation_update(update_message)
            except:
                self.console.print(f"[blue]🔧 TOOL UPDATE: {event.data}[/]")
            return
        
        elif event.type == "tool_operation_complete":
            try:
                import json
                data = json.loads(event.data)
                success = data.get("success", True)
                content = data.get("content", "")
                error_message = data.get("error_message", "")
                self.render_tool_operation_complete(success, content, error_message)
            except:
                self.console.print(f"[blue]✅ TOOL COMPLETE: {event.data}[/]")
            return
        
        # Handle specialist activation events
        elif event.type == "specialist_activation":
            try:
                import json
                data = json.loads(event.data)
                agent_type = data.get("agent_type", "UNKNOWN")
                is_core = data.get("is_core", False)
                self.render_specialist_activation(agent_type, is_core)
            except:
                self.console.print(f"[green]👤 SPECIALIST ACTIVATED: {event.data}[/]")
            return
        
        # Handle specialist thinking events
        elif event.type == "specialist_thinking":
            try:
                import json
                data = json.loads(event.data)
                agent_type = data.get("agent_type", "UNKNOWN")
                thought = data.get("thought", "")
                is_core = data.get("is_core", False)
                self.render_specialist_thinking(agent_type, thought, is_core)
            except:
                self.console.print(f"[green]💭 SPECIALIST THINKING: {event.data}[/]")
            return
        
        # Handle orchestrator step events
        elif event.type == "orchestrator_step":
            try:
                import json
                data = json.loads(event.data)
                step_desc = data.get("description", "")
                step_num = data.get("step_number", 1)
                total_steps = data.get("total_steps", 1)
                self.render_orchestrator_step(step_desc, step_num, total_steps)
            except:
                self.console.print(f"[gold3]🎯 ORCHESTRATOR STEP: {event.data}[/]")
            return
        
        # Handle agent step events
        elif event.type == "agent_step":
            try:
                import json
                data = json.loads(event.data)
                agent_type = data.get("agent_type", "UNKNOWN")
                step_desc = data.get("description", "")
                step_num = data.get("step_number", 1)
                is_core = data.get("is_core", False)
                self.render_agent_step(agent_type, step_desc, step_num, is_core)
            except:
                # Fallback to original step rendering with role differentiation
                self._current_agent_role = MessageRole.SPECIALIST
                super()._render_step(event)
            return
        
        # Handle existing orchestrator-specific events
        elif event.type == "routing_analysis":
            try:
                import json
                analysis = json.loads(event.data)
                self.render_routing_analysis(analysis)
            except:
                self.console.print(f"[cyan]🔀 Routing Analysis: {event.data}[/]")
            return
        
        elif event.type == "agent_execution_start":
            try:
                import json
                context = json.loads(event.data)
                agent_type = context.get("agent_type", "UNKNOWN")
                self.render_agent_execution_start(agent_type, context)
            except:
                self.console.print(f"[green]🤖 Agent Execution: {event.data}[/]")
            return
        
        elif event.type == "execution_trace":
            try:
                import json
                trace = json.loads(event.data)
                self.render_execution_trace(trace)
            except:
                self.console.print(f"[blue]🔍 Execution Trace: {event.data}[/]")
            return
        
        elif event.type == "multi_agent_flow":
            try:
                import json
                flow = json.loads(event.data)
                self.render_multi_agent_flow(flow)
            except:
                self.console.print(f"[magenta]🔄 Multi-Agent Flow: {event.data}[/]")
            return
        
        elif event.type == "performance_metrics":
            try:
                import json
                metrics = json.loads(event.data)
                self.render_performance_metrics(metrics)
            except:
                self.console.print(f"[cyan]📊 Performance: {event.data}[/]")
            return
        
        elif event.type == "session_summary":
            try:
                import json
                summary = json.loads(event.data)
                self.render_session_summary(summary)
            except:
                self.console.print(f"[yellow]📋 Session Summary: {event.data}[/]")
            return

        # Flexible notifier: kind, message, details (file ops, tools, context, etc.)
        elif event.type == "notifier":
            try:
                import json
                data = json.loads(event.data) if isinstance(event.data, str) else event.data
                kind = data.get("kind") or data.get("category", "info")
                message = data.get("message", str(event.data))
                details = data.get("details", {})
                if isinstance(details, str):
                    details = {}
                self._render_notifier(kind, message, details)
            except Exception:
                self.console.print(Text(f"  ℹ️ {event.data}", style="dim"))
            return
        
        # Handle standard events with role differentiation (thoughts summarized)
        elif event.type == "thought":
            summary = _summarize_thought(event.data)
            if self._current_agent_role == MessageRole.ORCHESTRATOR:
                if self._reflection_mode:
                    self.console.print(Text(f"🔄 REFLECTION: {summary}", style="bold cyan"))
                else:
                    self.console.print(Text(f"🧠 ORCHESTRATOR: {summary}", style="bold gold3"))
            else:
                super()._render_thought(summary)
            return
        
        elif event.type == "response":
            # Enhanced response rendering with role context
            if not self._response_open:
                agent_style = self._get_agent_style(
                    self._current_agent or "coder", 
                    self._current_agent_role
                )
                
                sender_name = self._get_agent_prefix(
                    self._current_agent or "coder",
                    self._current_agent_role
                )
                
                if event.meta and event.meta.model:
                    provider = event.meta.provider or "AI"
                    sender_name = f"{sender_name} ({provider}/{event.meta.model})"
                    
                self.console.print(Text.assemble(
                    (f"{sender_name} ", agent_style),
                    ("› ", "panel.border")
                ), end="")
                self._response_open = True
                
            self.console.print(Text(event.data, style="response.text"), end="")
            return
        
        # Fall back to parent renderer for other events
        super().render(event)
