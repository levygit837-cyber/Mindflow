"""Integration interfaces for MindFlow backend.

Provides interfaces for external service integration,
version control, cloud services, and notifications.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from abc import ABC, abstractmethod

from pydantic import BaseModel


class GitInterface(ABC):
    """Interface for Git operations."""
    
    @abstractmethod
    async def get_status(self, repository_path: str) -> Dict[str, Any]:
        """Get Git repository status.
        
        Args:
            repository_path: Path to repository
            
        Returns:
            Repository status information
        """
        pass
    
    @abstractmethod
    async def commit_changes(
        self,
        repository_path: str,
        message: str,
        files: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Commit changes to repository.
        
        Args:
            repository_path: Path to repository
            message: Commit message
            files: Files to commit (None for all)
            
        Returns:
            Commit result
        """
        pass
    
    @abstractmethod
    async def create_branch(
        self,
        repository_path: str,
        branch_name: str,
        from_branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create new branch.
        
        Args:
            repository_path: Path to repository
            branch_name: New branch name
            from_branch: Source branch
            
        Returns:
            Branch creation result
        """
        pass
    
    @abstractmethod
    async def merge_branch(
        self,
        repository_path: str,
        source_branch: str,
        target_branch: str
    ) -> Dict[str, Any]:
        """Merge branches.
        
        Args:
            repository_path: Path to repository
            source_branch: Source branch
            target_branch: Target branch
            
        Returns:
            Merge result
        """
        pass
    
    @abstractmethod
    async def get_history(
        self,
        repository_path: str,
        limit: int = 10,
        branch: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get commit history.
        
        Args:
            repository_path: Path to repository
            limit: Number of commits to retrieve
            branch: Branch to get history from
            
        Returns:
            List of commit information
        """
        pass


class DockerInterface(ABC):
    """Interface for Docker operations."""
    
    @abstractmethod
    async def build_image(
        self,
        dockerfile_path: str,
        image_name: str,
        context_path: Optional[str] = None,
        build_args: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Build Docker image.
        
        Args:
            dockerfile_path: Path to Dockerfile
            image_name: Image name
            context_path: Build context path
            build_args: Build arguments
            
        Returns:
            Build result
        """
        pass
    
    @abstractmethod
    async def run_container(
        self,
        image_name: str,
        container_name: Optional[str] = None,
        ports: Optional[Dict[str, str]] = None,
        volumes: Optional[Dict[str, str]] = None,
        environment: Optional[Dict[str, str]] = None,
        detached: bool = True
    ) -> Dict[str, Any]:
        """Run Docker container.
        
        Args:
            image_name: Image to run
            container_name: Container name
            ports: Port mappings
            volumes: Volume mappings
            environment: Environment variables
            detached: Run in detached mode
            
        Returns:
            Container run result
        """
        pass
    
    @abstractmethod
    async def list_containers(self, all_containers: bool = False) -> List[Dict[str, Any]]:
        """List Docker containers.
        
        Args:
            all_containers: Include stopped containers
            
        Returns:
            List of container information
        """
        pass
    
    @abstractmethod
    async def stop_container(self, container_id: str) -> Dict[str, Any]:
        """Stop Docker container.
        
        Args:
            container_id: Container ID or name
            
        Returns:
            Stop result
        """
        pass
    
    @abstractmethod
    async def remove_container(self, container_id: str, force: bool = False) -> Dict[str, Any]:
        """Remove Docker container.
        
        Args:
            container_id: Container ID or name
            force: Force removal
            
        Returns:
            Removal result
        """
        pass


class CloudInterface(ABC):
    """Interface for cloud service operations."""
    
    @abstractmethod
    async def upload_file(
        self,
        local_path: str,
        remote_path: str,
        bucket_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upload file to cloud storage.
        
        Args:
            local_path: Local file path
            remote_path: Remote file path
            bucket_name: Bucket name (if applicable)
            
        Returns:
            Upload result
        """
        pass
    
    @abstractmethod
    async def download_file(
        self,
        remote_path: str,
        local_path: str,
        bucket_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Download file from cloud storage.
        
        Args:
            remote_path: Remote file path
            local_path: Local file path
            bucket_name: Bucket name (if applicable)
            
        Returns:
            Download result
        """
        pass
    
    @abstractmethod
    async def list_files(
        self,
        remote_path: str = "",
        bucket_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List files in cloud storage.
        
        Args:
            remote_path: Remote path to list
            bucket_name: Bucket name (if applicable)
            
        Returns:
            List of file information
        """
        pass
    
    @abstractmethod
    async def delete_file(
        self,
        remote_path: str,
        bucket_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Delete file from cloud storage.
        
        Args:
            remote_path: Remote file path
            bucket_name: Bucket name (if applicable)
            
        Returns:
            Delete result
        """
        pass


class NotificationInterface(ABC):
    """Interface for notification operations."""
    
    @abstractmethod
    async def send_email(
        self,
        to: Union[str, List[str]],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        attachments: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Send email notification.
        
        Args:
            to: Recipient(s)
            subject: Email subject
            body: Email body
            html_body: HTML body (optional)
            attachments: File attachments
            
        Returns:
            Send result
        """
        pass
    
    @abstractmethod
    async def send_webhook(
        self,
        url: str,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        method: str = "POST"
    ) -> Dict[str, Any]:
        """Send webhook notification.
        
        Args:
            url: Webhook URL
            payload: Request payload
            headers: Request headers
            method: HTTP method
            
        Returns:
            Send result
        """
        pass
    
    @abstractmethod
    async def send_slack(
        self,
        message: str,
        channel: Optional[str] = None,
        webhook_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send Slack notification.
        
        Args:
            message: Message to send
            channel: Slack channel
            webhook_url: Slack webhook URL
            
        Returns:
            Send result
        """
        pass
    
    @abstractmethod
    async def send_discord(
        self,
        message: str,
        webhook_url: str,
        username: Optional[str] = None,
        avatar_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send Discord notification.
        
        Args:
            message: Message to send
            webhook_url: Discord webhook URL
            username: Bot username
            avatar_url: Bot avatar URL
            
        Returns:
            Send result
        """
        pass


# Schema classes for integration interfaces
class GitStatus(BaseModel):
    """Git status schema."""
    
    repository_path: str
    branch: str
    commit_hash: str
    is_clean: bool
    modified_files: List[str]
    added_files: List[str]
    deleted_files: List[str]
    untracked_files: List[str]


class GitCommit(BaseModel):
    """Git commit schema."""
    
    hash: str
    author: str
    email: str
    date: str
    message: str
    files_changed: List[str]
    insertions: int
    deletions: int


class DockerContainer(BaseModel):
    """Docker container schema."""
    
    container_id: str
    name: str
    image: str
    status: str
    ports: Dict[str, str]
    created: str
    labels: Dict[str, str]


class DockerImage(BaseModel):
    """Docker image schema."""
    
    image_id: str
    repository: str
    tag: str
    size: int
    created: str


class CloudFile(BaseModel):
    """Cloud file schema."""
    
    name: str
    path: str
    size_bytes: int
    last_modified: str
    content_type: str
    etag: Optional[str] = None


class NotificationResult(BaseModel):
    """Notification result schema."""
    
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    timestamp: str


# Abstract base classes for implementation
class BaseGit(GitInterface):
    """Base implementation of GitInterface."""
    
    def __init__(self):
        self._repository_cache = {}
        self._status_cache = {}
    
    async def _validate_repository(self, repository_path: str) -> bool:
        """Validate Git repository."""
        # Implementation would check .git directory
        return True
    
    async def _execute_git_command(
        self,
        repository_path: str,
        command: List[str]
    ) -> Dict[str, Any]:
        """Execute Git command."""
        # Implementation would use subprocess or gitpython
        return {}


class BaseDocker(DockerInterface):
    """Base implementation of DockerInterface."""
    
    def __init__(self):
        self._container_cache = {}
        self._image_cache = {}
    
    async def _validate_dockerfile(self, dockerfile_path: str) -> bool:
        """Validate Dockerfile."""
        # Implementation would check file existence and syntax
        return True
    
    async def _execute_docker_command(
        self,
        command: List[str]
    ) -> Dict[str, Any]:
        """Execute Docker command."""
        # Implementation would use docker-py or subprocess
        return {}


class BaseCloud(CloudInterface):
    """Base implementation of CloudInterface."""
    
    def __init__(self):
        self._connection_config = {}
        self._bucket_cache = {}
    
    async def _validate_connection(self) -> bool:
        """Validate cloud connection."""
        # Implementation would test connectivity
        return True
    
    async def _get_client(self):
        """Get cloud service client."""
        # Implementation would return appropriate client
        return None


class BaseNotification(NotificationInterface):
    """Base implementation of NotificationInterface."""
    
    def __init__(self):
        self._provider_configs = {}
        self._rate_limits = {}
    
    async def _validate_recipients(self, recipients: Union[str, List[str]]) -> bool:
        """Validate recipient addresses."""
        # Implementation would validate email/webhook formats
        return True
    
    async def _check_rate_limit(self, provider: str) -> bool:
        """Check rate limiting for provider."""
        # Implementation would check against rate limits
        return True
