"""Streaming service for real-time event streaming.

This service provides comprehensive streaming capabilities including
broadcast channels, event management, and real-time communication.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, AsyncGenerator
from datetime import datetime, UTC
import asyncio
import uuid
from collections import defaultdict, deque

from omnimind_backend.infra.logging import get_logger
from omnimind_backend.services.interfaces.base_interfaces import BaseAbstractService
from omnimind_backend.services.interfaces.communication_interfaces import StreamingServiceInterface


class StreamingService(BaseAbstractService, StreamingServiceInterface):
    """Service for real-time event streaming and communication.
    
    This service provides comprehensive streaming capabilities including
    broadcast channels, event management, and subscription handling.
    """
    
    def __init__(self) -> None:
        """Initialize streaming service with configuration."""
        super().__init__()
        
        # Stream management
        self._streams: Dict[str, Dict[str, Any]] = {}
        self._subscribers: Dict[str, Dict[str, Any]] = {}
        self._broadcast_channels: Dict[str, Dict[str, Any]] = {}
        
        # Event queues
        self._event_queues: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._subscriber_queues: Dict[str, asyncio.Queue] = {}
        
        # Configuration
        self._max_subscribers_per_stream = 100
        self._max_events_per_queue = 1000
        self._default_stream_ttl = 3600  # 1 hour
        
        # Metrics
        self._streaming_metrics = {
            "total_streams": 0,
            "active_streams": 0,
            "total_subscribers": 0,
            "total_events": 0,
            "broadcast_channels": 0
        }
    
    def _get_logger(self) -> Any:
        """Get logger instance for this service."""
        return get_logger(__name__)
    
    async def create_stream(
        self,
        stream_id: str,
        stream_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new event stream.
        
        Args:
            stream_id: Unique stream identifier
            stream_config: Stream configuration
            
        Returns:
            Dictionary containing stream creation result
        """
        self.log_operation("create_stream", stream_id=stream_id)
        
        try:
            # Validate stream configuration
            required_fields = ["name"]
            for field in required_fields:
                if field not in stream_config:
                    raise ValueError(f"Missing required field: {field}")
            
            # Check if stream already exists
            if stream_id in self._streams:
                raise ValueError(f"Stream already exists: {stream_id}")
            
            # Create stream
            stream = {
                "id": stream_id,
                "name": stream_config["name"],
                "description": stream_config.get("description", ""),
                "config": stream_config,
                "created_at": datetime.now(UTC).isoformat(),
                "status": "active",
                "subscriber_count": 0,
                "event_count": 0,
                "last_event_at": None,
                "ttl": stream_config.get("ttl", self._default_stream_ttl)
            }
            
            self._streams[stream_id] = stream
            self._streaming_metrics["total_streams"] += 1
            self._streaming_metrics["active_streams"] += 1
            
            # Create event queue for stream
            self._event_queues[stream_id] = deque(maxlen=self._max_events_per_queue)
            
            return {
                "stream_id": stream_id,
                "name": stream_config["name"],
                "status": "created",
                "created_at": stream["created_at"],
                "config": stream_config
            }
            
        except Exception as exc:
            self._logger.error(f"Error creating stream {stream_id}: {str(exc)}")
            raise
    
    async def send_event(
        self,
        stream_id: str,
        event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send an event to a stream.
        
        Args:
            stream_id: Stream identifier
            event: Event data
            
        Returns:
            Dictionary containing event send result
        """
        self.log_operation("send_event", stream_id=stream_id)
        
        try:
            # Validate stream exists
            if stream_id not in self._streams:
                raise ValueError(f"Stream not found: {stream_id}")
            
            # Create event with metadata
            event_with_metadata = {
                "id": str(uuid.uuid4()),
                "stream_id": stream_id,
                "data": event,
                "timestamp": datetime.now(UTC).isoformat(),
                "type": event.get("type", "data")
            }
            
            # Add to stream event queue
            self._event_queues[stream_id].append(event_with_metadata)
            
            # Update stream metadata
            stream = self._streams[stream_id]
            stream["event_count"] += 1
            stream["last_event_at"] = event_with_metadata["timestamp"]
            
            # Notify subscribers
            await self._notify_subscribers(stream_id, event_with_metadata)
            
            # Update metrics
            self._streaming_metrics["total_events"] += 1
            
            return {
                "stream_id": stream_id,
                "event_id": event_with_metadata["id"],
                "status": "sent",
                "timestamp": event_with_metadata["timestamp"],
                "subscriber_count": stream["subscriber_count"]
            }
            
        except Exception as exc:
            self._logger.error(f"Error sending event to stream {stream_id}: {str(exc)}")
            raise
    
    async def subscribe_to_stream(
        self,
        stream_id: str,
        subscriber_id: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Subscribe to an event stream.
        
        Args:
            stream_id: Stream identifier
            subscriber_id: Unique subscriber identifier
            
        Yields:
            Stream events as they occur
        """
        self.log_operation("subscribe_to_stream", stream_id=stream_id, subscriber_id=subscriber_id)
        
        try:
            # Validate stream exists
            if stream_id not in self._streams:
                raise ValueError(f"Stream not found: {stream_id}")
            
            # Check subscriber limit
            stream = self._streams[stream_id]
            if stream["subscriber_count"] >= self._max_subscribers_per_stream:
                raise ValueError(f"Stream {stream_id} has reached maximum subscribers")
            
            # Create subscriber
            subscriber = {
                "id": subscriber_id,
                "stream_id": stream_id,
                "subscribed_at": datetime.now(UTC).isoformat(),
                "status": "active",
                "event_count": 0,
                "last_event_id": None
            }
            
            # Add subscriber to stream
            if stream_id not in self._subscribers:
                self._subscribers[stream_id] = {}
            
            self._subscribers[stream_id][subscriber_id] = subscriber
            stream["subscriber_count"] += 1
            
            # Create subscriber queue
            queue_key = f"{stream_id}:{subscriber_id}"
            self._subscriber_queues[queue_key] = asyncio.Queue(maxsize=100)
            
            # Update metrics
            self._streaming_metrics["total_subscribers"] += 1
            
            try:
                # Send existing events to new subscriber
                existing_events = list(self._event_queues[stream_id])
                for event in existing_events[-10:]:  # Last 10 events
                    await self._subscriber_queues[queue_key].put(event)
                
                # Yield new events as they arrive
                while True:
                    try:
                        # Wait for event with timeout
                        event = await asyncio.wait_for(
                            self._subscriber_queues[queue_key].get(),
                            timeout=1.0
                        )
                        
                        # Update subscriber metadata
                        subscriber["event_count"] += 1
                        subscriber["last_event_id"] = event["id"]
                        
                        yield event
                        
                    except asyncio.TimeoutError:
                        # Check if subscriber is still active
                        if subscriber_id not in self._subscribers.get(stream_id, {}):
                            break
                        
                        # Send heartbeat
                        yield {
                            "type": "heartbeat",
                            "timestamp": datetime.now(UTC).isoformat(),
                            "stream_id": stream_id
                        }
                        
            except GeneratorExit:
                # Subscriber disconnected
                pass
            finally:
                # Cleanup subscriber
                await self._cleanup_subscriber(stream_id, subscriber_id)
                
        except Exception as exc:
            self._logger.error(f"Error subscribing to stream {stream_id}: {str(exc)}")
            raise
    
    async def close_stream(self, stream_id: str) -> Dict[str, Any]:
        """Close an event stream.
        
        Args:
            stream_id: Stream identifier
            
        Returns:
            Dictionary containing stream closure result
        """
        self.log_operation("close_stream", stream_id=stream_id)
        
        try:
            # Validate stream exists
            if stream_id not in self._streams:
                raise ValueError(f"Stream not found: {stream_id}")
            
            stream = self._streams[stream_id]
            
            # Notify all subscribers of stream closure
            closure_event = {
                "type": "stream_closed",
                "stream_id": stream_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "reason": "stream_terminated"
            }
            
            await self._notify_subscribers(stream_id, closure_event)
            
            # Remove all subscribers
            if stream_id in self._subscribers:
                for subscriber_id in list(self._subscribers[stream_id].keys()):
                    await self._cleanup_subscriber(stream_id, subscriber_id)
                
                del self._subscribers[stream_id]
            
            # Clean up stream resources
            if stream_id in self._event_queues:
                del self._event_queues[stream_id]
            
            # Update stream status
            stream["status"] = "closed"
            stream["closed_at"] = datetime.now(UTC).isoformat()
            
            self._streaming_metrics["active_streams"] -= 1
            
            return {
                "stream_id": stream_id,
                "status": "closed",
                "closed_at": stream["closed_at"],
                "final_subscriber_count": stream["subscriber_count"],
                "total_events": stream["event_count"]
            }
            
        except Exception as exc:
            self._logger.error(f"Error closing stream {stream_id}: {str(exc)}")
            raise
    
    async def get_stream_status(self, stream_id: str) -> Dict[str, Any]:
        """Get status of a specific stream.
        
        Args:
            stream_id: Stream identifier
            
        Returns:
            Dictionary containing stream status
        """
        self.log_operation("get_stream_status", stream_id=stream_id)
        
        try:
            stream = self._streams.get(stream_id)
            if not stream:
                raise ValueError(f"Stream not found: {stream_id}")
            
            # Get recent events
            recent_events = list(self._event_queues.get(stream_id, []))[-10:]
            
            # Get subscriber information
            subscribers = self._subscribers.get(stream_id, {})
            subscriber_details = [
                {
                    "id": sub_id,
                    "subscribed_at": sub["subscribed_at"],
                    "event_count": sub["event_count"],
                    "last_event_id": sub["last_event_id"],
                    "status": sub["status"]
                }
                for sub_id, sub in subscribers.items()
            ]
            
            return {
                "stream_id": stream_id,
                "name": stream["name"],
                "status": stream["status"],
                "created_at": stream["created_at"],
                "closed_at": stream.get("closed_at"),
                "subscriber_count": stream["subscriber_count"],
                "event_count": stream["event_count"],
                "last_event_at": stream["last_event_at"],
                "recent_events": recent_events,
                "subscribers": subscriber_details,
                "config": stream["config"]
            }
            
        except Exception as exc:
            self._logger.error(f"Error getting stream status for {stream_id}: {str(exc)}")
            raise
    
    async def list_active_streams(self) -> List[Dict[str, Any]]:
        """List all active streams.
        
        Returns:
            List of active stream information
        """
        self.log_operation("list_active_streams")
        
        try:
            active_streams = []
            
            for stream_id, stream in self._streams.items():
                if stream["status"] == "active":
                    # Get basic status
                    recent_events = list(self._event_queues.get(stream_id, []))[-5:]
                    
                    stream_info = {
                        "stream_id": stream_id,
                        "name": stream["name"],
                        "created_at": stream["created_at"],
                        "subscriber_count": stream["subscriber_count"],
                        "event_count": stream["event_count"],
                        "last_event_at": stream["last_event_at"],
                        "recent_event_count": len(recent_events),
                        "config": stream["config"]
                    }
                    
                    active_streams.append(stream_info)
            
            # Sort by creation time (newest first)
            active_streams.sort(key=lambda x: x["created_at"], reverse=True)
            
            return active_streams
            
        except Exception as exc:
            self._logger.error(f"Error listing active streams: {str(exc)}")
            raise
    
    async def create_broadcast_channel(
        self,
        channel_name: str,
        channel_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a broadcast channel for multiple subscribers.
        
        Args:
            channel_name: Channel name
            channel_config: Channel configuration
            
        Returns:
            Dictionary containing channel creation result
        """
        self.log_operation("create_broadcast_channel", channel_name=channel_name)
        
        try:
            # Validate channel configuration
            required_fields = ["name"]
            for field in required_fields:
                if field not in channel_config:
                    raise ValueError(f"Missing required field: {field}")
            
            # Check if channel already exists
            if channel_name in self._broadcast_channels:
                raise ValueError(f"Broadcast channel already exists: {channel_name}")
            
            # Create broadcast channel
            channel = {
                "name": channel_name,
                "config": channel_config,
                "created_at": datetime.now(UTC).isoformat(),
                "status": "active",
                "subscriber_count": 0,
                "message_count": 0,
                "last_message_at": None
            }
            
            self._broadcast_channels[channel_name] = channel
            self._streaming_metrics["broadcast_channels"] += 1
            
            return {
                "channel_name": channel_name,
                "status": "created",
                "created_at": channel["created_at"],
                "config": channel_config
            }
            
        except Exception as exc:
            self._logger.error(f"Error creating broadcast channel {channel_name}: {str(exc)}")
            raise
    
    async def broadcast_event(
        self,
        channel_name: str,
        event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Broadcast event to all channel subscribers.
        
        Args:
            channel_name: Channel name
            event: Event data
            
        Returns:
            Dictionary containing broadcast result
        """
        self.log_operation("broadcast_event", channel_name=channel_name)
        
        try:
            # Validate channel exists
            if channel_name not in self._broadcast_channels:
                raise ValueError(f"Broadcast channel not found: {channel_name}")
            
            # Create broadcast event
            broadcast_event = {
                "id": str(uuid.uuid4()),
                "channel_name": channel_name,
                "data": event,
                "timestamp": datetime.now(UTC).isoformat(),
                "type": event.get("type", "broadcast")
            }
            
            # Create stream for this broadcast if it doesn't exist
            stream_id = f"broadcast:{channel_name}"
            if stream_id not in self._streams:
                await self.create_stream(stream_id, {
                    "name": f"Broadcast: {channel_name}",
                    "type": "broadcast",
                    "channel_name": channel_name
                })
            
            # Send event to broadcast stream
            result = await self.send_event(stream_id, broadcast_event)
            
            # Update channel metadata
            channel = self._broadcast_channels[channel_name]
            channel["message_count"] += 1
            channel["last_message_at"] = broadcast_event["timestamp"]
            
            return {
                "channel_name": channel_name,
                "event_id": broadcast_event["id"],
                "status": "broadcasted",
                "timestamp": broadcast_event["timestamp"],
                "subscriber_count": channel["subscriber_count"]
            }
            
        except Exception as exc:
            self._logger.error(f"Error broadcasting event to {channel_name}: {str(exc)}")
            raise
    
    async def get_stream_metrics(self, stream_id: str) -> Dict[str, Any]:
        """Get performance metrics for a stream.
        
        Args:
            stream_id: Stream identifier
            
        Returns:
            Dictionary containing stream metrics
        """
        self.log_operation("get_stream_metrics", stream_id=stream_id)
        
        try:
            stream = self._streams.get(stream_id)
            if not stream:
                raise ValueError(f"Stream not found: {stream_id}")
            
            # Calculate metrics
            events = list(self._event_queues.get(stream_id, []))
            subscribers = self._subscribers.get(stream_id, {})
            
            # Event rate metrics
            if events:
                time_span = (
                    datetime.fromisoformat(events[-1]["timestamp"]) -
                    datetime.fromisoformat(events[0]["timestamp"])
                ).total_seconds()
                
                events_per_second = len(events) / time_span if time_span > 0 else 0
                events_per_minute = events_per_second * 60
            else:
                events_per_second = events_per_minute = 0
            
            # Subscriber metrics
            active_subscribers = len([s for s in subscribers.values() if s["status"] == "active"])
            
            return {
                "stream_id": stream_id,
                "total_events": len(events),
                "total_subscribers": len(subscribers),
                "active_subscribers": active_subscribers,
                "events_per_second": round(events_per_second, 3),
                "events_per_minute": round(events_per_minute, 2),
                "uptime_seconds": self._calculate_stream_uptime(stream),
                "average_events_per_subscriber": round(len(events) / len(subscribers), 2) if subscribers else 0,
                "last_event_at": stream["last_event_at"],
                "generated_at": datetime.now(UTC).isoformat()
            }
            
        except Exception as exc:
            self._logger.error(f"Error getting stream metrics for {stream_id}: {str(exc)}")
            raise
    
    async def configure_stream_security(
        self,
        stream_id: str,
        security_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Configure security settings for a stream.
        
        Args:
            stream_id: Stream identifier
            security_config: Security configuration
            
        Returns:
            Dictionary containing security configuration result
        """
        self.log_operation("configure_stream_security", stream_id=stream_id)
        
        try:
            # Validate stream exists
            if stream_id not in self._streams:
                raise ValueError(f"Stream not found: {stream_id}")
            
            # Validate security configuration
            required_fields = ["authentication_required"]
            for field in required_fields:
                if field not in security_config:
                    raise ValueError(f"Missing required security field: {field}")
            
            # Update stream security configuration
            stream = self._streams[stream_id]
            
            if "security" not in stream["config"]:
                stream["config"]["security"] = {}
            
            stream["config"]["security"].update(security_config)
            stream["security_updated_at"] = datetime.now(UTC).isoformat()
            
            return {
                "stream_id": stream_id,
                "security_config": security_config,
                "status": "configured",
                "configured_at": stream["security_updated_at"]
            }
            
        except Exception as exc:
            self._logger.error(f"Error configuring stream security for {stream_id}: {str(exc)}")
            raise
    
    # Helper methods
    
    async def _notify_subscribers(self, stream_id: str, event: Dict[str, Any]) -> None:
        """Notify all subscribers of a stream about an event."""
        subscribers = self._subscribers.get(stream_id, {})
        
        for subscriber_id, subscriber in subscribers.items():
            if subscriber["status"] == "active":
                queue_key = f"{stream_id}:{subscriber_id}"
                
                if queue_key in self._subscriber_queues:
                    try:
                        # Add event to subscriber queue (non-blocking)
                        self._subscriber_queues[queue_key].put_nowait(event)
                    except asyncio.QueueFull:
                        # Queue is full, remove oldest event
                        try:
                            self._subscriber_queues[queue_key].get_nowait()
                            self._subscriber_queues[queue_key].put_nowait(event)
                        except asyncio.QueueEmpty:
                            pass
    
    async def _cleanup_subscriber(self, stream_id: str, subscriber_id: str) -> None:
        """Clean up subscriber resources."""
        # Remove from subscribers
        if stream_id in self._subscribers:
            self._subscribers[stream_id].pop(subscriber_id, None)
            
            # Update stream subscriber count
            if stream_id in self._streams:
                self._streams[stream_id]["subscriber_count"] -= 1
        
        # Remove subscriber queue
        queue_key = f"{stream_id}:{subscriber_id}"
        if queue_key in self._subscriber_queues:
            del self._subscriber_queues[queue_key]
        
        # Update metrics
        self._streaming_metrics["total_subscribers"] -= 1
    
    def _calculate_stream_uptime(self, stream: Dict[str, Any]) -> int:
        """Calculate stream uptime in seconds."""
        if not stream or stream["status"] != "active":
            return 0
        
        created_at = datetime.fromisoformat(stream["created_at"])
        uptime = datetime.now(UTC) - created_at
        return int(uptime.total_seconds())
