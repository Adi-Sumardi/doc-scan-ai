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
from utils.pdf_page_analyzer import PDFPageAnalyzer, get_pdf_page_count

logger = logging.getLogger(__name__)


class BatchProcessor:
    """
    Process multiple documents in batch with progress tracking
    Supports parallel processing with configurable concurrency limit
    """

    def __init__(self, max_concurrent_tasks: int = 5, max_pages_per_chunk: int = 10):
        """
        Initialize batch processor with parallel processing support

        Args:
            max_concurrent_tasks: Maximum number of files to process simultaneously
                                 Default: 5 (to avoid API rate limits)
            max_pages_per_chunk: Maximum pages to process per PDF chunk
                                Default: 10 pages
        """
        self.batches: Dict[str, Dict[str, Any]] = {}
        self._cancel_requests: Set[str] = set()
        self.max_concurrent_tasks = max_concurrent_tasks
        self.max_pages_per_chunk = max_pages_per_chunk
        self._semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self._pdf_analyzer = PDFPageAnalyzer(max_pages_per_chunk=max_pages_per_chunk)
        logger.info(f"✅ Batch Processor initialized with max {max_concurrent_tasks} concurrent tasks, {max_pages_per_chunk} pages per chunk")
    
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
        
        # Count total pages for PDFs
        total_pages = 0
        for file_path in file_paths:
            if str(file_path).lower().endswith('.pdf'):
                page_count = get_pdf_page_count(file_path)
                total_pages += page_count

        batch_info = {
            "batch_id": batch_id,
            "user_id": user_id,
            "document_type": document_type,
            "total_files": len(file_paths),
            "total_pages": total_pages,  # NEW: Total pages across all PDFs
            "processed_files": 0,
            "processed_pages": 0,  # NEW: Track page-level progress
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

            # Get page count for PDFs
            page_count = 0
            if str(file_path).lower().endswith('.pdf'):
                page_count = get_pdf_page_count(file_path)

            batch_info["files"].append({
                "file_path": file_path,
                "filename": filename,
                "document_type": detected_type,
                "page_count": page_count,  # NEW: Track pages per file
                "processed_pages": 0,  # NEW: Track processed pages
                "status": "pending",  # pending, processing, completed, failed
                "result": None,
                "error": None
            })
        
        self.batches[batch_id] = batch_info
        if total_pages > 0:
            logger.info(f"📦 Batch {batch_id} created with {len(file_paths)} files ({total_pages} total pages)")
        else:
            logger.info(f"📦 Batch {batch_id} created with {len(file_paths)} files")
        
        return batch_id
    
    async def _process_single_file(
        self,
        batch_id: str,
        file_info: Dict[str, Any],
        idx: int,
        total_files: int
    ) -> None:
        """
        Process a single file with semaphore control for rate limiting

        Args:
            batch_id: Batch identifier
            file_info: File information dictionary
            idx: File index (0-based)
            total_files: Total number of files in batch
        """
        async with self._semaphore:  # Limit concurrent processing
            if self.is_cancelled(batch_id):
                logger.info(f"⏭️ Skipping file {idx + 1}/{total_files} (batch cancelled)")
                return

            try:
                file_info["status"] = "processing"
                batch_info = self.batches[batch_id]

                logger.info(f"📄 Processing file {idx + 1}/{total_files}: {file_info['filename']}")

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

                logger.info(f"✅ File {idx + 1}/{total_files} processed successfully (confidence: {result['confidence']:.2%})")

            except Exception as e:
                logger.error(f"❌ Failed to process file {file_info['filename']}: {e}")
                file_info["status"] = "failed"
                file_info["error"] = str(e)
                batch_info = self.batches[batch_id]
                batch_info["failed_files"] += 1
                batch_info["errors"].append({
                    "filename": file_info["filename"],
                    "error": str(e)
                })

            finally:
                # Update progress timestamp
                batch_info = self.batches[batch_id]
                batch_info["updated_at"] = datetime.now(timezone.utc).isoformat()

    async def process_batch(self, batch_id: str) -> Dict[str, Any]:
        """
        Process all files in a batch with PARALLEL processing

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

        logger.info(f"🚀 Starting PARALLEL batch processing for {batch_id} ({len(batch_info['files'])} files, max {self.max_concurrent_tasks} concurrent)")

        # Create tasks for parallel processing
        tasks = []
        for idx, file_info in enumerate(batch_info["files"]):
            task = self._process_single_file(
                batch_id=batch_id,
                file_info=file_info,
                idx=idx,
                total_files=batch_info["total_files"]
            )
            tasks.append(task)

        # Process all files in parallel with asyncio.gather
        await asyncio.gather(*tasks, return_exceptions=True)

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
            Current batch status with progress (file and page level)
        """
        if batch_id not in self.batches:
            raise ValueError(f"Batch {batch_id} not found")

        batch_info = self.batches[batch_id]

        status = {
            "batch_id": batch_id,
            "status": batch_info["status"],
            "total_files": batch_info["total_files"],
            "processed_files": batch_info["processed_files"],
            "failed_files": batch_info["failed_files"],
            "progress_percentage": (batch_info["processed_files"] / batch_info["total_files"] * 100) if batch_info["total_files"] > 0 else 0,
            "created_at": batch_info["created_at"],
            "updated_at": batch_info["updated_at"]
        }

        # Add page-level progress if available
        if batch_info.get("total_pages", 0) > 0:
            status["total_pages"] = batch_info["total_pages"]
            status["processed_pages"] = batch_info.get("processed_pages", 0)
            status["page_progress_percentage"] = (batch_info.get("processed_pages", 0) / batch_info["total_pages"] * 100)

        return status
    
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


# Global batch processor instance with config-based concurrency
# Import config here to avoid circular dependency
try:
    from config import settings
    batch_processor = BatchProcessor(
        max_concurrent_tasks=settings.max_concurrent_processing,
        max_pages_per_chunk=settings.pdf_chunk_size
    )
    logger.info(f"🚀 Batch processor initialized: {settings.max_concurrent_processing} concurrent tasks, {settings.pdf_chunk_size} pages per chunk")
except ImportError:
    # Fallback if config not available
    batch_processor = BatchProcessor(max_concurrent_tasks=5, max_pages_per_chunk=10)
    logger.warning("⚠️ Config not available, using defaults: 5 concurrent tasks, 10 pages per chunk")
