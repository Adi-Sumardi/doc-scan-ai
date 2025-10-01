from pydantic import BaseModel, EmailStr
from typing import List, Optional, Any, Dict
from datetime import datetime

# Authentication Models
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: Optional[str] = None
    is_active: bool
    is_admin: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Document Models
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