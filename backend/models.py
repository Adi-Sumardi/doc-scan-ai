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
    refresh_token: Optional[str] = None
    token_type: str
    expires_in: Optional[int] = None  # Token expiry in seconds

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

# Tax Reconciliation Models

class ReconciliationProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    period_start: datetime
    period_end: datetime

class ReconciliationProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    period_start: datetime
    period_end: datetime
    status: str
    total_invoices: int
    total_transactions: int
    matched_count: int
    unmatched_invoices: int
    unmatched_transactions: int
    total_invoice_amount: float
    total_transaction_amount: float
    variance_amount: float
    user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TaxInvoiceCreate(BaseModel):
    project_id: str
    invoice_number: str
    invoice_date: datetime
    invoice_type: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_npwp: Optional[str] = None
    dpp: float
    ppn: float
    total_amount: float
    notes: Optional[str] = None

class TaxInvoiceResponse(BaseModel):
    id: str
    project_id: str
    scan_result_id: Optional[str] = None
    invoice_number: str
    invoice_date: datetime
    invoice_type: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_npwp: Optional[str] = None
    dpp: float
    ppn: float
    total_amount: float
    match_status: str
    match_confidence: float
    matched_transaction_id: Optional[str] = None
    matched_by: Optional[str] = None
    matched_at: Optional[datetime] = None
    notes: Optional[str] = None
    dispute_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class BankTransactionCreate(BaseModel):
    project_id: str
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    account_holder: Optional[str] = None
    transaction_date: datetime
    posting_date: Optional[datetime] = None
    effective_date: Optional[datetime] = None
    description: Optional[str] = None
    transaction_type: Optional[str] = None
    reference_number: Optional[str] = None
    debit: float = 0.0
    credit: float = 0.0
    balance: Optional[float] = None
    notes: Optional[str] = None

class BankTransactionResponse(BaseModel):
    id: str
    project_id: str
    scan_result_id: Optional[str] = None
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    account_holder: Optional[str] = None
    transaction_date: datetime
    posting_date: Optional[datetime] = None
    effective_date: Optional[datetime] = None
    description: Optional[str] = None
    transaction_type: Optional[str] = None
    reference_number: Optional[str] = None
    debit: float
    credit: float
    balance: Optional[float] = None
    match_status: str
    match_confidence: float
    matched_invoice_id: Optional[str] = None
    matched_by: Optional[str] = None
    matched_at: Optional[datetime] = None
    notes: Optional[str] = None
    dispute_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ReconciliationMatchCreate(BaseModel):
    project_id: str
    invoice_id: str
    transaction_id: str
    match_type: str  # auto, manual, suggested
    match_confidence: float
    notes: Optional[str] = None

class ReconciliationMatchResponse(BaseModel):
    id: str
    project_id: str
    invoice_id: str
    transaction_id: str
    match_type: str
    match_confidence: float
    match_score: float
    amount_variance: float
    date_variance_days: int
    score_amount: float
    score_date: float
    score_vendor: float
    score_reference: float
    status: str
    confirmed: bool
    confirmed_by: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    matched_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AutoMatchRequest(BaseModel):
    project_id: str
    min_confidence: Optional[float] = 0.8

class AutoMatchResponse(BaseModel):
    project_id: str
    total_invoices: int
    total_transactions: int
    matches_found: int
    high_confidence_matches: int
    medium_confidence_matches: int
    low_confidence_matches: int
    processing_time_seconds: float