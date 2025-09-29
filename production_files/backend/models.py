from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from datetime import datetime

class DocumentFile(BaseModel):
    id: str
    name: str
    type: str
    status: str
    progress: int
    result_id: Optional[str] = None

class BatchResponse(BaseModel):
    id: str
    files: List[DocumentFile]
    status: str
    created_at: str
    total_files: int
    processed_files: int
    completed_at: Optional[str] = None
    error: Optional[str] = None

class ScanResult(BaseModel):
    id: str
    batch_id: str
    document_type: str
    original_filename: str
    extracted_data: Dict[str, Any]
    confidence: float
    created_at: str

class BatchStatus(BaseModel):
    batch_id: str
    status: str
    progress: float
    message: str