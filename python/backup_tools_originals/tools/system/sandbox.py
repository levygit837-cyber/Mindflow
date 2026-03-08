"""
 sandbox tool 
for secure command execution. Migrated to the new ToolInterface architecture 
while preserving all existing functionality including process isolation, timeouts, and security controls. 
"""
 
from __future__ 
import annotations 
import os 
import subprocess 
import uuid 
from typing 
import Any, Dict, Optional, Union 
from mindflow_backend.infra.logging 
import get_logger 
from mindflow_backend.schemas.orchestration.orchestrator 
import AgentType 
from ..base.tool_interface 
import ToolInterface 
from ..base.tool_schemas 
import ( ToolSchema, ToolParameter, ParameterType, create_tool_schema, create_parameter ) _logger = get_logger(__name__) 
class MindFlowSandbox(ToolInterface, BaseSandbox): 
"""
 sandbox tool 
for secure command execution. Migrated to ToolInterface 
while preserving BaseSandbox inheritance and all existing security features including process isolation, timeouts, output limits, and read-only mode enforcement. 
"""
 
def __init__( self, root_dir: Optional[Union[str, "Path"]] = None, timeout: int = 60, max_output_bytes: int = 100_000, env: Optional[Dict[str, str]] = None, read_only: bool = False, ): 
"""
Initialize the sandbox 
with interface.
"""
 
from pathlib 
import Path 
# Initialize ToolInterface super().__init__() self.name = "sandbox" self.description = "Secure sandbox 
for shell command execution 
with process isolation" 
# Initialize BaseSandbox BaseSandbox.__init__(self) 
# Sandbox configuration self.cwd = Path(root_dir).resolve() 
if root_dir else Path.cwd() self._default_timeout = timeout self._max_output_bytes = max_output_bytes self._env = env 
if env is not None else {} self._id = f"mindflow-{uuid.uuid4().hex[:8]}" self._read_only = read_only @property 
def id(self) -> str: 
"""
Get sandbox identifier.
"""
 
return self._id 
def get_schema(self) -> Dict[str, Any]: 
"""
Return tool schema 
for validation.
"""
 
return create_tool_schema( name=self.name, description=self.description, category="system", parameters=[ create_parameter( name="command", param_type=ParameterType.STRING, description="Shell command to execute", required=True, min_length=1 ), create_parameter( name="timeout", param_type=ParameterType.INTEGER, description="Command timeout in seconds", required=False, default=self._default_timeout, min_value=1, max_value=300 ), create_parameter( name="working_directory", param_type=ParameterType.STRING, description="Working directory 
for command execution", required=False, default=str(self.cwd) ), create_parameter( name="environment", param_type=ParameterType.OBJECT, description="Additional environment variables", required=False, default={} ) ], requires_sandbox=True, supported_agents=[AgentType.CODER, AgentType.ORCHESTRATOR], security_level="high", timeout_seconds=self._default_timeout ).dict() async 
def execute(self, *args, **kwargs) -> Dict[str, Any]: 
"""
Execute command 
with interface and validation. Args: command: Shell command to execute timeout: Command timeout in seconds working_directory: Working directory 
for execution environment: Additional environment variables Returns: Execution result 
with standardized format 
"""
 try: command = kwargs.get("command") 
if not command: 
return self._format_result( success=False, error="Command parameter is required" ) 
# Validate command 
for security is_safe, error_msg = self._validate_command(command) 
if not is_safe: 
return self._format_result( success=False, error=f"Command validation failed: {error_msg}" ) 
# Execute using existing logic timeout = kwargs.get("timeout", self._default_timeout) working_dir = kwargs.get("working_directory", str(self.cwd)) env = kwargs.get("environment", {}) 
# Temporarily update working directory 
if specified original_cwd = self.cwd 
if working_dir != str(self.cwd): 
from pathlib 
import Path self.cwd = Path(working_dir).resolve() 
# Merge environment variables original_env = self._env 
if env: merged_env = {**self._env, **env} self._env = merged_env try: 
# Execute using existing BaseSandbox logic result = self.execute_command(command, timeout=timeout) 
# Convert to format 
return self._format_result( success=result.exit_code == 0, result={ "output": result.output, "exit_code": result.exit_code, "truncated": result.truncated }, metadata={ "sandbox_id": self.id, "command": command, "timeout": timeout, "working_directory": str(self.cwd), "read_only": self._read_only } ) 
finally: 
# Restore original configuration self.cwd = original_cwd self._env = original_env 
except Exception as e: _logger.error( "sandbox_execution_failed", command=kwargs.get("command"), error=str(e), sandbox_id=self.id ) 
return self._format_result( success=False, error=f"Sandbox execution failed: {str(e)}" ) 
def _validate_command(self, command: str) -> tuple[bool, Optional[str]]: 
"""
Validate command 
for security and policy compliance. Args: command: Command to validate Returns: Tuple of (is_valid, error_message) 
"""
 
# Check 
for dangerous commands dangerous_patterns = [ "rm -rf /", "sudo rm", "chmod 777", "chown root", "dd if=", "mkfs", "format", "fdisk", ] cmd_lower = command.lower() 
for pattern in dangerous_patterns: 
if pattern in cmd_lower: 
return False, f"Dangerous command pattern detected: {pattern}" 
# Check read-only restrictions 
if self._read_only: write_patterns = [ "rm ", "mv ", "cp ", "mkdir ", "touch ", "chmod ", "chown ", ">", ">>", "tee ", "dd ", "write", "delete", "truncate", ] 
if any(pat in cmd_lower 
for pat in write_patterns): 
return False, "Write operation blocked in read-only mode" 
return True, None 
# Legacy interface methods 
for backward compatibility 
def execute_command( self, command: str, *, timeout: Optional[int] = None, ) -> ExecuteResponse: 
"""
Execute a shell command within the sandbox (legacy interface). This method preserves the original BaseSandbox interface. 
"""
 
if not command: 
return ExecuteResponse(output="Error: Empty command", exit_code=1, truncated=False) 
# Enforce read-only mode 
if self._read_only: _WRITE_PATTERNS = [ "rm ", "mv ", "cp ", "mkdir ", "touch ", "chmod ", "chown ", ">", ">>", "tee ", "dd ", "write", "delete", "truncate", ] cmd_lower = command.lower().strip() 
if any(pat in cmd_lower 
for pat in _WRITE_PATTERNS): 
return ExecuteResponse( output="Error: Write operation blocked — agent is in READ_ONLY sandbox mode.", exit_code=1, truncated=False, ) effective_timeout = timeout 
if timeout is not None else self._default_timeout try: _logger.info("sandbox_executing", sandbox_id=self.id, command=command) 
# Execute in a shell-like environment but 
with limited context result = subprocess.run( command, shell=True, check=False, capture_output=True, text=True, timeout=effective_timeout, env=self._env, cwd=str(self.cwd), ) output_parts = [] 
if result.stdout: output_parts.append(result.stdout) 
if result.stderr: output_parts.append(f"[stderr] {result.stderr}") output = "\n".join(output_parts) 
if output_parts else "<no output>" truncated = False 
if len(output) > self._max_output_bytes: output = output[:self._max_output_bytes] + "\n\n... [output truncated]" truncated = True 
return ExecuteResponse( output=output, exit_code=result.returncode, truncated=truncated ) 
except subprocess.TimeoutExpired: 
return ExecuteResponse( output=f"Error: Command timed out after {effective_timeout}s", exit_code=124, truncated=False ) 
except Exception as e: 
return ExecuteResponse( output=f"Error executing command: {str(e)}", exit_code=1, truncated=False ) 
def execute( self, command: str, *, timeout: Optional[int] = None, ) -> ExecuteResponse: 
"""
Legacy execute method 
for backward compatibility.
"""
 
return self.execute_command(command, timeout=timeout) 
def upload_files(self, files: list[tuple[str, bytes]]) -> list: 
"""
Upload files to sandbox (legacy interface).
"""
 responses = [] 
for path, content in files: full_path = self.cwd / path try: full_path.parent.mkdir(parents=True, exist_ok=True) full_path.write_bytes(content) responses.append(FileUploadResponse(path=path, error=None)) 
except Exception as e: responses.append(FileUploadResponse(path=path, error=str(e))) 
return responses 
def download_files(self, paths: list[str]) -> list: 
"""
Download files 
from sandbox (legacy interface).
"""
 responses = [] 
for path in paths: full_path = self.cwd / path try: 
if full_path.exists(): content = full_path.read_bytes() responses.append(FileDownloadResponse(path=path, content=content, error=None)) 
else: responses.append(FileDownloadResponse(path=path, content=None, error="not_found")) 
except Exception as e: responses.append(FileDownloadResponse(path=path, content=None, error=str(e))) 
return responses 
def get_capabilities(self) -> Dict[str, Any]: 
"""
Return sandbox capabilities.
"""
 capabilities = super().get_capabilities() capabilities.update({ "requires_sandbox": True, "supports_file_upload": True, "supports_file_download": True, "read_only_mode": self._read_only, "max_output_bytes": self._max_output_bytes, "default_timeout": self._default_timeout, "working_directory": str(self.cwd) }) 
return capabilities 
# Factory function 
for dependency injection 
def get_sandbox_tool(**kwargs) -> MindFlowSandbox: 
"""
Factory function to get sandbox tool 
with configuration.
"""
 
return MindFlowSandbox(**kwargs) 
def get_readonly_sandbox(**kwargs) -> MindFlowSandbox: 
"""
Factory function to get read-only sandbox tool.
"""
 
return MindFlowSandbox(read_only=True, **kwargs)