"""Integration tools for MindFlow agents.

Provides Git operations, Docker management, and cloud service
integrations with enhanced capabilities.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

try:
    import git
    from git import InvalidGitRepositoryError, Repo
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False
    git = None
    Repo = None
    InvalidGitRepositoryError = None

try:
    import docker
    from docker.client import DockerClient
    from docker.models.containers import Container
    from docker.models.images import Image
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    docker = None
    DockerClient = None
    Container = None
    Image = None

from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools.integration_schemas import DOCKER_SCHEMA, GIT_SCHEMA

_logger = get_logger(__name__)


class GitTool(AsyncToolInterface):
    """Git operations tool."""
    
    def __init__(self, backend: Any | None = None):
        """Initialize the Git tool.
        
        Args:
            backend: Optional backend for compatibility
        """
        super().__init__()
        self.backend = backend
        self.name = "git_manager"
        self.description = "Git repository management and operations"
        
        self._schema = GIT_SCHEMA
    
    async def execute(self, **kwargs) -> dict[str, Any]:
        """Execute Git operation.
        
        Args:
            action: Git action to perform
            repository_path: Repository path or URL
            files: Files to add
            message: Commit message
            branch: Branch name
            remote: Remote name
            options: Additional options
            
        Returns:
            Dictionary with operation result
        """
        try:
            action = kwargs["action"]
            repository_path = kwargs.get("repository_path", ".")
            files = kwargs.get("files", [])
            message = kwargs.get("message")
            branch = kwargs.get("branch")
            remote = kwargs.get("remote", "origin")
            options = kwargs.get("options", {})
            
            if action == "status":
                return await self._git_status(repository_path)
            elif action == "add":
                if not files:
                    return self._format_result(
                        success=False,
                        error="Files required for add action"
                    )
                return await self._git_add(repository_path, files)
            elif action == "commit":
                if not message:
                    return self._format_result(
                        success=False,
                        error="Commit message required for commit action"
                    )
                return await self._git_commit(repository_path, message, options)
            elif action == "push":
                return await self._git_push(repository_path, remote, branch, options)
            elif action == "pull":
                return await self._git_pull(repository_path, remote, branch, options)
            elif action == "clone":
                if not repository_path:
                    return self._format_result(
                        success=False,
                        error="Repository URL required for clone action"
                    )
                return await self._git_clone(repository_path, options)
            elif action == "log":
                return await self._git_log(repository_path, options)
            elif action == "branch":
                return await self._git_branch(repository_path, branch, options)
            elif action == "merge":
                if not branch:
                    return self._format_result(
                        success=False,
                        error="Branch name required for merge action"
                    )
                return await self._git_merge(repository_path, branch, options)
            elif action == "diff":
                return await self._git_diff(repository_path, options)
            else:
                return self._format_result(
                    success=False,
                    error=f"Unknown action: {action}"
                )
                
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Git operation failed: {str(e)}"
            )
    
    async def _git_status(self, repository_path: str) -> dict[str, Any]:
        """Get Git repository status."""
        try:
            if not GIT_AVAILABLE:
                return await self._git_status_fallback(repository_path)
            
            repo_path = Path(repository_path)
            if not repo_path.exists():
                return self._format_result(
                    success=False,
                    error=f"Repository path not found: {repository_path}"
                )
            
            try:
                repo = Repo(repo_path)
            except InvalidGitRepositoryError:
                return self._format_result(
                    success=False,
                    error=f"Not a Git repository: {repository_path}"
                )
            
            # Get status
            status = repo.git.status("--porcelain").splitlines()
            
            staged_files = []
            modified_files = []
            untracked_files = []
            
            for line in status:
                if line.startswith("M "):
                    modified_files.append(line[3:])
                elif line.startswith("A "):
                    staged_files.append(line[3:])
                elif line.startswith("?? "):
                    untracked_files.append(line[3:])
            
            # Get current branch
            current_branch = repo.active_branch.name
            
            return self._format_result(
                success=True,
                result={
                    "action": "status",
                    "repository": str(repo_path.absolute()),
                    "current_branch": current_branch,
                    "staged_files": staged_files,
                    "modified_files": modified_files,
                    "untracked_files": untracked_files,
                    "is_clean": len(status) == 0
                }
            )
            
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Git status failed: {str(e)}"
            )
    
    async def _git_status_fallback(self, repository_path: str) -> dict[str, Any]:
        """Fallback Git status using command line."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repository_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return self._format_result(
                    success=False,
                    error=f"Git status failed: {result.stderr}"
                )
            
            status_lines = result.stdout.splitlines()
            staged_files = []
            modified_files = []
            untracked_files = []
            
            for line in status_lines:
                if line.startswith("M "):
                    modified_files.append(line[3:])
                elif line.startswith("A "):
                    staged_files.append(line[3:])
                elif line.startswith("?? "):
                    untracked_files.append(line[3:])
            
            # Get current branch
            branch_result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=repository_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            current_branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"
            
            return self._format_result(
                success=True,
                result={
                    "action": "status",
                    "repository": str(Path(repository_path).absolute()),
                    "current_branch": current_branch,
                    "staged_files": staged_files,
                    "modified_files": modified_files,
                    "untracked_files": untracked_files,
                    "is_clean": len(status_lines) == 0
                }
            )
            
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Git status fallback failed: {str(e)}"
            )
    
    async def _git_add(self, repository_path: str, files: list[str]) -> dict[str, Any]:
        """Add files to Git staging area."""
        try:
            if GIT_AVAILABLE:
                repo = Repo(repository_path)
                
                for file_path in files:
                    repo.index.add([file_path])
                
                return self._format_result(
                    success=True,
                    result={
                        "action": "add",
                        "files_added": files,
                        "repository": str(Path(repository_path).absolute())
                    }
                )
            else:
                # Fallback to command line
                cmd = ["git", "add"] + files
                result = subprocess.run(
                    cmd,
                    cwd=repository_path,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode != 0:
                    return self._format_result(
                        success=False,
                        error=f"Git add failed: {result.stderr}"
                    )
                
                return self._format_result(
                    success=True,
                    result={
                        "action": "add",
                        "files_added": files,
                        "repository": str(Path(repository_path).absolute())
                    }
                )
                
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Git add failed: {str(e)}"
            )
    
    async def _git_commit(self, repository_path: str, message: str, options: dict) -> dict[str, Any]:
        """Create a Git commit."""
        try:
            if GIT_AVAILABLE:
                repo = Repo(repository_path)
                repo.index.commit(message)
                
                return self._format_result(
                    success=True,
                    result={
                        "action": "commit",
                        "message": message,
                        "repository": str(Path(repository_path).absolute())
                    }
                )
            else:
                # Fallback to command line
                cmd = ["git", "commit", "-m", message]
                result = subprocess.run(
                    cmd,
                    cwd=repository_path,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode != 0:
                    return self._format_result(
                        success=False,
                        error=f"Git commit failed: {result.stderr}"
                    )
                
                return self._format_result(
                    success=True,
                    result={
                        "action": "commit",
                        "message": message,
                        "repository": str(Path(repository_path).absolute())
                    }
                )
                
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Git commit failed: {str(e)}"
            )
    
    async def _git_push(self, repository_path: str, remote: str, branch: str | None, options: dict) -> dict[str, Any]:
        """Push changes to remote repository."""
        try:
            if GIT_AVAILABLE:
                repo = Repo(repository_path)
                
                if branch:
                    origin = repo.remote(remote)
                    origin.push(branch)
                else:
                    origin = repo.remote(remote)
                    origin.push()
                
                return self._format_result(
                    success=True,
                    result={
                        "action": "push",
                        "remote": remote,
                        "branch": branch or "default",
                        "repository": str(Path(repository_path).absolute())
                    }
                )
            else:
                # Fallback to command line
                cmd = ["git", "push", remote]
                if branch:
                    cmd.append(branch)
                
                result = subprocess.run(
                    cmd,
                    cwd=repository_path,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode != 0:
                    return self._format_result(
                        success=False,
                        error=f"Git push failed: {result.stderr}"
                    )
                
                return self._format_result(
                    success=True,
                    result={
                        "action": "push",
                        "remote": remote,
                        "branch": branch or "default",
                        "repository": str(Path(repository_path).absolute())
                    }
                )
                
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Git push failed: {str(e)}"
            )
    
    async def _git_clone(self, repository_url: str, options: dict) -> dict[str, Any]:
        """Clone a Git repository."""
        try:
            target_dir = options.get("target_dir", ".")
            branch = options.get("branch")
            depth = options.get("depth")
            
            if GIT_AVAILABLE:
                clone_args = [repository_url, target_dir]
                if branch:
                    clone_args.append(f"--branch={branch}")
                if depth:
                    clone_args.append(f"--depth={depth}")
                
                repo = Repo.clone_from(*clone_args)
                
                return self._format_result(
                    success=True,
                    result={
                        "action": "clone",
                        "repository_url": repository_url,
                        "target_dir": str(Path(target_dir).absolute()),
                        "branch": branch
                    }
                )
            else:
                # Fallback to command line
                cmd = ["git", "clone", repository_url, target_dir]
                if branch:
                    cmd.extend(["--branch", branch])
                if depth:
                    cmd.extend(["--depth", str(depth)])
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minutes for cloning
                )
                
                if result.returncode != 0:
                    return self._format_result(
                        success=False,
                        error=f"Git clone failed: {result.stderr}"
                    )
                
                return self._format_result(
                    success=True,
                    result={
                        "action": "clone",
                        "repository_url": repository_url,
                        "target_dir": str(Path(target_dir).absolute()),
                        "branch": branch
                    }
                )
                
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Git clone failed: {str(e)}"
            )
    
    async def _git_log(self, repository_path: str, options: dict) -> dict[str, Any]:
        """Get Git commit log."""
        try:
            limit = options.get("limit", 10)
            
            if GIT_AVAILABLE:
                repo = Repo(repository_path)
                commits = list(repo.iter_commits('HEAD', max_count=limit))
                
                log_data = []
                for commit in commits:
                    log_data.append({
                        "hash": commit.hexsha,
                        "short_hash": commit.hexsha[:7],
                        "author": str(commit.author),
                        "date": commit.committed_datetime.isoformat(),
                        "message": commit.message.strip()
                    })
                
                return self._format_result(
                    success=True,
                    result={
                        "action": "log",
                        "commits": log_data,
                        "count": len(log_data),
                        "repository": str(Path(repository_path).absolute())
                    }
                )
            else:
                # Fallback to command line
                cmd = ["git", "log", "--oneline", f"-n{limit}", "--pretty=format:%H|%an|%ad|%s", "--date=iso"]
                result = subprocess.run(
                    cmd,
                    cwd=repository_path,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode != 0:
                    return self._format_result(
                        success=False,
                        error=f"Git log failed: {result.stderr}"
                    )
                
                commits = []
                for line in result.stdout.splitlines():
                    parts = line.split('|', 3)
                    if len(parts) >= 4:
                        commits.append({
                            "hash": parts[0],
                            "short_hash": parts[0][:7],
                            "author": parts[1],
                            "date": parts[2],
                            "message": parts[3]
                        })
                
                return self._format_result(
                    success=True,
                    result={
                        "action": "log",
                        "commits": commits,
                        "count": len(commits),
                        "repository": str(Path(repository_path).absolute())
                    }
                )
                
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Git log failed: {str(e)}"
            )
    
    async def _git_branch(self, repository_path: str, branch_name: str | None, options: dict) -> dict[str, Any]:
        """Manage Git branches."""
        try:
            action_type = options.get("type", "list")
            
            if GIT_AVAILABLE:
                repo = Repo(repository_path)
                
                if action_type == "list":
                    branches = [branch.name for branch in repo.branches]
                    current_branch = repo.active_branch.name
                    
                    return self._format_result(
                        success=True,
                        result={
                            "action": "branch",
                            "type": "list",
                            "branches": branches,
                            "current_branch": current_branch,
                            "repository": str(Path(repository_path).absolute())
                        }
                    )
                elif action_type == "create" and branch_name:
                    new_branch = repo.create_head(branch_name)
                    return self._format_result(
                        success=True,
                        result={
                            "action": "branch",
                            "type": "create",
                            "branch": branch_name,
                            "repository": str(Path(repository_path).absolute())
                        }
                    )
                elif action_type == "checkout" and branch_name:
                    repo.git.checkout(branch_name)
                    return self._format_result(
                        success=True,
                        result={
                            "action": "branch",
                            "type": "checkout",
                            "branch": branch_name,
                            "repository": str(Path(repository_path).absolute())
                        }
                    )
            
            return self._format_result(
                success=False,
                error="Branch operation not supported or invalid parameters"
            )
            
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Git branch failed: {str(e)}"
            )
    
    async def _git_merge(self, repository_path: str, branch_name: str, options: dict) -> dict[str, Any]:
        """Merge a branch."""
        try:
            if GIT_AVAILABLE:
                repo = Repo(repository_path)
                repo.git.merge(branch_name)
                
                return self._format_result(
                    success=True,
                    result={
                        "action": "merge",
                        "branch": branch_name,
                        "repository": str(Path(repository_path).absolute())
                    }
                )
            else:
                # Fallback to command line
                cmd = ["git", "merge", branch_name]
                result = subprocess.run(
                    cmd,
                    cwd=repository_path,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode != 0:
                    return self._format_result(
                        success=False,
                        error=f"Git merge failed: {result.stderr}"
                    )
                
                return self._format_result(
                    success=True,
                    result={
                        "action": "merge",
                        "branch": branch_name,
                        "repository": str(Path(repository_path).absolute())
                    }
                )
                
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Git merge failed: {str(e)}"
            )
    
    async def _git_diff(self, repository_path: str, options: dict) -> dict[str, Any]:
        """Get Git diff."""
        try:
            file_path = options.get("file_path")
            staged = options.get("staged", False)
            
            if GIT_AVAILABLE:
                repo = Repo(repository_path)
                
                if staged:
                    diff = repo.git.diff("--staged", file_path if file_path else "")
                else:
                    diff = repo.git.diff(file_path if file_path else "")
                
                return self._format_result(
                    success=True,
                    result={
                        "action": "diff",
                        "diff": diff,
                        "staged": staged,
                        "file_path": file_path,
                        "repository": str(Path(repository_path).absolute())
                    }
                )
            else:
                # Fallback to command line
                cmd = ["git", "diff"]
                if staged:
                    cmd.append("--staged")
                if file_path:
                    cmd.append(file_path)
                
                result = subprocess.run(
                    cmd,
                    cwd=repository_path,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode != 0:
                    return self._format_result(
                        success=False,
                        error=f"Git diff failed: {result.stderr}"
                    )
                
                return self._format_result(
                    success=True,
                    result={
                        "action": "diff",
                        "diff": result.stdout,
                        "staged": staged,
                        "file_path": file_path,
                        "repository": str(Path(repository_path).absolute())
                    }
                )
                
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Git diff failed: {str(e)}"
            )
    
    def get_schema(self) -> dict[str, Any]:
        """Get tool schema."""
        return self._schema.dict()


class DockerTool(AsyncToolInterface):
    """Docker operations tool."""
    
    def __init__(self, backend: Any | None = None):
        """Initialize the Docker tool.
        
        Args:
            backend: Optional backend for compatibility
        """
        super().__init__()
        self.backend = backend
        self.name = "docker_manager"
        self.description = "Docker container and image management"
        
        self._client = None
        
        self._schema = DOCKER_SCHEMA
    
    async def execute(self, **kwargs) -> dict[str, Any]:
        """Execute Docker operation.
        
        Args:
            action: Docker action to perform
            container_name: Container name or ID
            image_name: Image name
            command: Container command
            ports: Port mappings
            volumes: Volume mappings
            environment: Environment variables
            detach: Detached mode
            dockerfile_path: Dockerfile path
            tag: Image tag
            
        Returns:
            Dictionary with operation result
        """
        try:
            action = kwargs["action"]
            container_name = kwargs.get("container_name")
            image_name = kwargs.get("image_name")
            command = kwargs.get("command")
            ports = kwargs.get("ports", [])
            volumes = kwargs.get("volumes", [])
            environment = kwargs.get("environment", {})
            detach = kwargs.get("detach", True)
            dockerfile_path = kwargs.get("dockerfile_path")
            tag = kwargs.get("tag")
            
            if not DOCKER_AVAILABLE:
                return self._format_result(
                    success=False,
                    error="Docker library not available. Install with: pip install docker"
                )
            
            # Initialize Docker client
            if not self._client:
                self._client = docker.from_env()
            
            if action == "list_containers":
                return await self._list_containers()
            elif action == "list_images":
                return await self._list_images()
            elif action == "run":
                if not image_name:
                    return self._format_result(
                        success=False,
                        error="Image name required for run action"
                    )
                return await self._run_container(image_name, container_name, command, ports, volumes, environment, detach)
            elif action == "stop":
                if not container_name:
                    return self._format_result(
                        success=False,
                        error="Container name required for stop action"
                    )
                return await self._stop_container(container_name)
            elif action == "remove":
                if not container_name:
                    return self._format_result(
                        success=False,
                        error="Container name required for remove action"
                    )
                return await self._remove_container(container_name)
            elif action == "build":
                if not dockerfile_path:
                    return self._format_result(
                        success=False,
                        error="Dockerfile path required for build action"
                    )
                return await self._build_image(dockerfile_path, tag)
            elif action == "logs":
                if not container_name:
                    return self._format_result(
                        success=False,
                        error="Container name required for logs action"
                    )
                return await self._get_container_logs(container_name)
            elif action == "exec":
                if not container_name or not command:
                    return self._format_result(
                        success=False,
                        error="Container name and command required for exec action"
                    )
                return await self._exec_command(container_name, command)
            else:
                return self._format_result(
                    success=False,
                    error=f"Unknown action: {action}"
                )
                
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Docker operation failed: {str(e)}"
            )
    
    async def _list_containers(self) -> dict[str, Any]:
        """List all containers."""
        try:
            containers = self._client.containers.list(all=True)
            
            container_data = []
            for container in containers:
                container_data.append({
                    "id": container.short_id,
                    "name": container.name,
                    "image": container.image.tags[0] if container.image.tags else "unknown",
                    "status": container.status,
                    "created": container.attrs["Created"],
                    "ports": container.ports,
                    "labels": container.labels
                })
            
            return self._format_result(
                success=True,
                result={
                    "action": "list_containers",
                    "containers": container_data,
                    "count": len(container_data)
                }
            )
            
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Failed to list containers: {str(e)}"
            )
    
    async def _list_images(self) -> dict[str, Any]:
        """List all images."""
        try:
            images = self._client.images.list()
            
            image_data = []
            for image in images:
                tags = image.tags if image.tags else ["<none>:<none>"]
                image_data.append({
                    "id": image.short_id,
                    "tags": tags,
                    "size": image.attrs["Size"],
                    "created": image.attrs["Created"],
                    "labels": image.labels
                })
            
            return self._format_result(
                success=True,
                result={
                    "action": "list_images",
                    "images": image_data,
                    "count": len(image_data)
                }
            )
            
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Failed to list images: {str(e)}"
            )
    
    async def _run_container(self, image_name: str, container_name: str | None, command: str | None, ports: list, volumes: list, environment: dict, detach: bool) -> dict[str, Any]:
        """Run a Docker container."""
        try:
            # Prepare port mappings
            port_bindings = {}
            for port_mapping in ports:
                if isinstance(port_mapping, str) and ':' in port_mapping:
                    host_port, container_port = port_mapping.split(':')
                    port_bindings[int(container_port)] = int(host_port)
            
            # Prepare volume mappings
            volume_bindings = {}
            for volume_mapping in volumes:
                if isinstance(volume_mapping, str) and ':' in volume_mapping:
                    host_path, container_path = volume_mapping.split(':')
                    volume_bindings[container_path] = {'bind': host_path, 'mode': 'rw'}
            
            # Run container
            container = self._client.containers.run(
                image=image_name,
                name=container_name,
                command=command,
                ports=port_bindings if port_bindings else None,
                volumes=volume_bindings if volume_bindings else None,
                environment=environment,
                detach=detach
            )
            
            return self._format_result(
                success=True,
                result={
                    "action": "run",
                    "container_id": container.short_id,
                    "container_name": container.name,
                    "image": image_name,
                    "status": container.status
                }
            )
            
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Failed to run container: {str(e)}"
            )
    
    async def _stop_container(self, container_name: str) -> dict[str, Any]:
        """Stop a container."""
        try:
            container = self._client.containers.get(container_name)
            container.stop()
            
            return self._format_result(
                success=True,
                result={
                    "action": "stop",
                    "container_name": container_name,
                    "status": "stopped"
                }
            )
            
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Failed to stop container: {str(e)}"
            )
    
    async def _remove_container(self, container_name: str) -> dict[str, Any]:
        """Remove a container."""
        try:
            container = self._client.containers.get(container_name)
            container.remove()
            
            return self._format_result(
                success=True,
                result={
                    "action": "remove",
                    "container_name": container_name,
                    "status": "removed"
                }
            )
            
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Failed to remove container: {str(e)}"
            )
    
    async def _build_image(self, dockerfile_path: str, tag: str | None) -> dict[str, Any]:
        """Build a Docker image."""
        try:
            dockerfile_dir = Path(dockerfile_path).parent
            
            image_tag = tag or "custom-image:latest"
            
            image, build_logs = self._client.images.build(
                path=str(dockerfile_dir),
                tag=image_tag,
                dockerfile=Path(dockerfile_path).name
            )
            
            return self._format_result(
                success=True,
                result={
                    "action": "build",
                    "image_id": image.short_id,
                    "tag": image_tag,
                    "build_logs": [log.get('stream', '') for log in build_logs if 'stream' in log]
                }
            )
            
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Failed to build image: {str(e)}"
            )
    
    async def _get_container_logs(self, container_name: str) -> dict[str, Any]:
        """Get container logs."""
        try:
            container = self._client.containers.get(container_name)
            logs = container.logs().decode('utf-8')
            
            return self._format_result(
                success=True,
                result={
                    "action": "logs",
                    "container_name": container_name,
                    "logs": logs
                }
            )
            
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Failed to get logs: {str(e)}"
            )
    
    async def _exec_command(self, container_name: str, command: str) -> dict[str, Any]:
        """Execute command in container."""
        try:
            container = self._client.containers.get(container_name)
            
            exec_result = container.exec_run(command)
            
            return self._format_result(
                success=True,
                result={
                    "action": "exec",
                    "container_name": container_name,
                    "command": command,
                    "exit_code": exec_result.exit_code,
                    "output": exec_result.output.decode('utf-8')
                }
            )
            
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Failed to execute command: {str(e)}"
            )
    
    def get_schema(self) -> dict[str, Any]:
        """Get tool schema."""
        return self._schema.dict()
