"""
WebSocket Manager for Real-time Progress Tracking
Provides WebSocket connections for real-time updates during document processing
"""

import json
import asyncio
import logging
from typing import Dict, Set, List
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections for real-time progress updates"""
    
    def __init__(self):
        # Active connections per batch
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # General connections (for system-wide updates)
        self.general_connections: Set[WebSocket] = set()
        
    async def connect(self, websocket: WebSocket, batch_id: str = None):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        if batch_id:
            # Connection for specific batch
            if batch_id not in self.active_connections:
                self.active_connections[batch_id] = set()
            self.active_connections[batch_id].add(websocket)
            logger.info(f"Client connected to batch {batch_id}")
        else:
            # General connection for system updates
            self.general_connections.add(websocket)
            logger.info("Client connected to general updates")
    
    def disconnect(self, websocket: WebSocket, batch_id: str = None):
        """Remove a WebSocket connection"""
        if batch_id and batch_id in self.active_connections:
            self.active_connections[batch_id].discard(websocket)
            if not self.active_connections[batch_id]:
                del self.active_connections[batch_id]
            logger.info(f"Client disconnected from batch {batch_id}")
        else:
            self.general_connections.discard(websocket)
            logger.info("Client disconnected from general updates")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific WebSocket"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
    
    async def broadcast_to_batch(self, message: dict, batch_id: str):
        """Send a message to all connections monitoring a specific batch"""
        if batch_id not in self.active_connections:
            return
        
        message_str = json.dumps(message)
        disconnected = []
        
        # Create a copy to avoid "Set changed size during iteration" error
        connections_copy = list(self.active_connections[batch_id])
        
        for connection in connections_copy:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error(f"Error broadcasting to batch {batch_id}: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for connection in disconnected:
            self.active_connections[batch_id].discard(connection)
    
    async def broadcast_general(self, message: dict):
        """Send a message to all general connections"""
        message_str = json.dumps(message)
        disconnected = []
        
        # Create a copy to avoid "Set changed size during iteration" error
        connections_copy = list(self.general_connections)
        
        for connection in connections_copy:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error(f"Error broadcasting general message: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for connection in disconnected:
            self.general_connections.discard(connection)
    
    async def send_batch_progress(self, batch_id: str, progress_data: dict):
        """Send progress update for a specific batch"""
        message = {
            "type": "batch_progress",
            "batch_id": batch_id,
            "timestamp": datetime.now().isoformat(),
            "data": progress_data
        }
        await self.broadcast_to_batch(message, batch_id)
    
    async def send_file_progress(self, batch_id: str, file_data: dict):
        """Send file processing update for a specific batch"""
        message = {
            "type": "file_progress", 
            "batch_id": batch_id,
            "timestamp": datetime.now().isoformat(),
            "data": file_data
        }
        await self.broadcast_to_batch(message, batch_id)
    
    async def send_batch_complete(self, batch_id: str, results: dict):
        """Send batch completion notification"""
        message = {
            "type": "batch_complete",
            "batch_id": batch_id, 
            "timestamp": datetime.now().isoformat(),
            "data": results
        }
        await self.broadcast_to_batch(message, batch_id)
    
    async def send_batch_error(self, batch_id: str, error_data: dict):
        """Send batch error notification"""
        message = {
            "type": "batch_error",
            "batch_id": batch_id,
            "timestamp": datetime.now().isoformat(),
            "data": error_data
        }
        await self.broadcast_to_batch(message, batch_id)
    
    async def send_system_status(self, status_data: dict):
        """Send system-wide status update"""
        message = {
            "type": "system_status",
            "timestamp": datetime.now().isoformat(),
            "data": status_data
        }
        await self.broadcast_general(message)
    
    def get_connection_stats(self) -> dict:
        """Get statistics about active connections"""
        batch_connections = sum(len(connections) for connections in self.active_connections.values())
        
        return {
            "total_connections": batch_connections + len(self.general_connections),
            "batch_connections": batch_connections,
            "general_connections": len(self.general_connections),
            "active_batches": len(self.active_connections),
            "batch_details": {
                batch_id: len(connections) 
                for batch_id, connections in self.active_connections.items()
            }
        }

# Global connection manager instance
manager = ConnectionManager()