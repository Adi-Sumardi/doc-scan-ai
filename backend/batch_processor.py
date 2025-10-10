"""
Batch Processor Module
Handles multiple document processing with progress tracking
Supports batch upload, batch processing, and batch export
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set
from pathlib import Path

from ai_processor import process_document_ai
from confidence_calculator import detect_document_type_from_filename

logger = logging.getLogger(__name__)


class BatchProcessor:
    """
    Process multiple documents in batch with progress tracking
    """
    
    def __init__(self):
        self.batches: Dict[str, Dict[str, Any]] = {}
        self._cancel_requests: Set[str] = set()
        logger.info("✅ Batch Processor initialized")
    
    async def create_batch(self, file_paths: List[str], document_type: str, user_id: Optional[str] = None) -> str:
        """
        Create a new batch processing job
        
        Args:
            file_paths: List of file paths to process
            document_type: Type of documents (or 'auto' for auto-detection)
            user_id: Optional user identifier
        
        Returns:
            batch_id: Unique identifier for this batch
        """
        batch_id = str(uuid.uuid4())
        
        batch_info = {
            "batch_id": batch_id,
            "user_id": user_id,
            "document_type": document_type,
            "total_files": len(file_paths),
            "processed_files": 0,
            "failed_files": 0,
            "status": "pending",  # pending, processing, completed, failed
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "files": [],
            "results": [],
            "errors": []
        }
        
        # Initialize file tracking
        for file_path in file_paths:
            filename = Path(file_path).name
            detected_type = detect_document_type_from_filename(filename) if document_type == 'auto' else document_type
            
            batch_info["files"].append({
                "file_path": file_path,
                "filename": filename,
                "document_type": detected_type,
                "status": "pending",  # pending, processing, completed, failed
                "result": None,
                "error": None
            })
        
        self.batches[batch_id] = batch_info
        logger.info(f"📦 Batch {batch_id} created with {len(file_paths)} files")
        
        return batch_id
    
    async def process_batch(self, batch_id: str) -> Dict[str, Any]:
        """
        Process all files in a batch
        
        Args:
            batch_id: Batch identifier
        
        Returns:
            Batch processing summary
        """
        if batch_id not in self.batches:
            raise ValueError(f"Batch {batch_id} not found")
        
        batch_info = self.batches[batch_id]
        batch_info["status"] = "processing"
        batch_info["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        logger.info(f"🚀 Starting batch processing for {batch_id}")
        
        # Process each file
        for idx, file_info in enumerate(batch_info["files"]):
            if self.is_cancelled(batch_id):
                logger.info("🛑 Batch %s cancellation requested. Halting remaining files.", batch_id)
                batch_info["status"] = "cancelled"
                batch_info["updated_at"] = datetime.now(timezone.utc).isoformat()
                break
            try:
                file_info["status"] = "processing"
                
                logger.info(f"📄 Processing file {idx + 1}/{batch_info['total_files']}: {file_info['filename']}")
                
                # Process document
                result = await process_document_ai(
                    file_path=file_info["file_path"],
                    document_type=file_info["document_type"]
                )
                
                # Add metadata
                result["filename"] = file_info["filename"]
                result["document_type"] = file_info["document_type"]
                result["batch_id"] = batch_id
                result["processed_at"] = datetime.now(timezone.utc).isoformat()
                
                # Store result
                file_info["result"] = result
                file_info["status"] = "completed"
                batch_info["results"].append(result)
                batch_info["processed_files"] += 1
                
                logger.info(f"✅ File {idx + 1} processed successfully (confidence: {result['confidence']:.2%})")
                
            except Exception as e:
                logger.error(f"❌ Failed to process file {file_info['filename']}: {e}")
                file_info["status"] = "failed"
                file_info["error"] = str(e)
                batch_info["failed_files"] += 1
                batch_info["errors"].append({
                    "filename": file_info["filename"],
                    "error": str(e)
                })
            
            # Update progress
            batch_info["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Update final status
        if self.is_cancelled(batch_id):
            batch_info["status"] = "cancelled"
            batch_info["completed_at"] = datetime.now(timezone.utc).isoformat()
            logger.info(f"🛑 Batch {batch_id} marked as cancelled")
        elif batch_info["failed_files"] == 0:
            batch_info["status"] = "completed"
        elif batch_info["processed_files"] == 0:
            batch_info["status"] = "failed"
        else:
            batch_info["status"] = "partial"  # Some succeeded, some failed
        
        batch_info["completed_at"] = datetime.now(timezone.utc).isoformat()
        
        logger.info(f"🏁 Batch {batch_id} processing completed: {batch_info['processed_files']} success, {batch_info['failed_files']} failed")
        self._cancel_requests.discard(batch_id)

        return self.get_batch_summary(batch_id)
    
    def get_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """
        Get current status of a batch
        
        Args:
            batch_id: Batch identifier
        
        Returns:
            Current batch status with progress
        """
        if batch_id not in self.batches:
            raise ValueError(f"Batch {batch_id} not found")
        
        batch_info = self.batches[batch_id]
        
        return {
            "batch_id": batch_id,
            "status": batch_info["status"],
            "total_files": batch_info["total_files"],
            "processed_files": batch_info["processed_files"],
            "failed_files": batch_info["failed_files"],
            "progress_percentage": (batch_info["processed_files"] / batch_info["total_files"] * 100) if batch_info["total_files"] > 0 else 0,
            "created_at": batch_info["created_at"],
            "updated_at": batch_info["updated_at"]
        }
    
    def get_batch_summary(self, batch_id: str) -> Dict[str, Any]:
        """
        Get complete summary of a batch
        
        Args:
            batch_id: Batch identifier
        
        Returns:
            Complete batch summary with all results
        """
        if batch_id not in self.batches:
            raise ValueError(f"Batch {batch_id} not found")
        
        batch_info = self.batches[batch_id]
        
        return {
            "batch_id": batch_id,
            "status": batch_info["status"],
            "document_type": batch_info["document_type"],
            "total_files": batch_info["total_files"],
            "processed_files": batch_info["processed_files"],
            "failed_files": batch_info["failed_files"],
            "results": batch_info["results"],
            "errors": batch_info["errors"],
            "created_at": batch_info["created_at"],
            "updated_at": batch_info["updated_at"],
            "completed_at": batch_info.get("completed_at")
        }
    
    def get_batch_results(self, batch_id: str) -> List[Dict[str, Any]]:
        """
        Get all successful results from a batch
        
        Args:
            batch_id: Batch identifier
        
        Returns:
            List of successful processing results
        """
        if batch_id not in self.batches:
            raise ValueError(f"Batch {batch_id} not found")
        
        return self.batches[batch_id]["results"]
    
    def delete_batch(self, batch_id: str) -> bool:
        """
        Delete a batch from memory
        
        Args:
            batch_id: Batch identifier
        
        Returns:
            True if deleted successfully
        """
        if batch_id in self.batches:
            del self.batches[batch_id]
            logger.info(f"🗑️ Batch {batch_id} deleted")
            return True
        return False
    
    def list_batches(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all batches, optionally filtered by user
        
        Args:
            user_id: Optional user identifier to filter
        
        Returns:
            List of batch summaries
        """
        batches = []
        
        for batch_id, batch_info in self.batches.items():
            if user_id is None or batch_info.get("user_id") == user_id:
                batches.append({
                    "batch_id": batch_id,
                    "status": batch_info["status"],
                    "total_files": batch_info["total_files"],
                    "processed_files": batch_info["processed_files"],
                    "failed_files": batch_info["failed_files"],
                    "created_at": batch_info["created_at"],
                    "updated_at": batch_info["updated_at"]
                })
        
        return batches

    def cancel_batch(self, batch_id: str) -> bool:
        """Signal that a batch should be cancelled."""
        self._cancel_requests.add(batch_id)

        if batch_id in self.batches:
            batch_info = self.batches[batch_id]
            batch_info["status"] = "cancelled"
            batch_info["updated_at"] = datetime.now(timezone.utc).isoformat()
        return True

    def is_cancelled(self, batch_id: str) -> bool:
        """Check whether a cancellation has been requested for a batch."""
        return batch_id in self._cancel_requests

    def clear_cancel_request(self, batch_id: str) -> None:
        """Remove cancellation flag after the job has fully stopped."""
        self._cancel_requests.discard(batch_id)


# Global batch processor instance
batch_processor = BatchProcessor()
