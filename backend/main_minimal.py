#!/usr/bin/env python3
"""
Minimal FastAPI Backend untuk Hostinger
Version tanpa advanced OCR libraries jika tidak tersedia
"""

import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

try:
    from fastapi import FastAPI, UploadFile, File, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    import uvicorn
except ImportError as e:
    print(f"❌ Critical import error: {e}")
    print("Please install: pip install --user fastapi uvicorn python-multipart")
    sys.exit(1)

# Optional imports with fallbacks
try:
    from database import get_db_session, Document
    DATABASE_AVAILABLE = True
except ImportError:
    print("⚠️  Database module not available - running without persistence")
    DATABASE_AVAILABLE = False

try:
    from ai_processor import IndonesianTaxDocumentParser
    OCR_AVAILABLE = True
except ImportError:
    print("⚠️  OCR processor not available - using text fallback")
    OCR_AVAILABLE = False

# Initialize FastAPI
app = FastAPI(
    title="Doc Scan AI - Minimal",
    description="Document scanning with OCR processing (Hostinger version)",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://docscan.adilabs.id", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock OCR processor jika tidak tersedia
class MockOCRProcessor:
    def process_document(self, file_path: str, doc_type: str):
        return {
            "raw_text": f"Mock OCR result for {doc_type}\nFile: {file_path}\nThis is a placeholder when OCR libraries are not available.",
            "document_type": doc_type,
            "confidence": 0.95,
            "processing_time": 0.1
        }
    
    def parse_faktur_pajak(self, text: str):
        return {"raw_text": text, "document_type": "faktur_pajak"}
    
    def parse_pph21(self, text: str):
        return {"raw_text": text, "document_type": "pph21"}
    
    def parse_pph23(self, text: str):
        return {"raw_text": text, "document_type": "pph23"}
    
    def parse_rekening_koran(self, text: str):
        return {"raw_text": text, "document_type": "rekening_koran"}
    
    def parse_invoice(self, text: str):
        return {"raw_text": text, "document_type": "invoice"}

# Initialize processor
if OCR_AVAILABLE:
    ocr_processor = IndonesianTaxDocumentParser()
else:
    ocr_processor = MockOCRProcessor()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database": DATABASE_AVAILABLE,
        "ocr": OCR_AVAILABLE,
        "message": "Doc Scan AI backend is running"
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Doc Scan AI Backend",
        "version": "1.0.0",
        "status": "running",
        "endpoints": ["/health", "/upload", "/documents"]
    }

@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = "auto"
):
    """Upload and process document"""
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Create uploads directory if not exists
        uploads_dir = Path("uploads")
        uploads_dir.mkdir(exist_ok=True)
        
        # Save file
        file_path = uploads_dir / file.filename
        content = await file.read()
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Process with OCR (or mock)
        if OCR_AVAILABLE:
            result = ocr_processor.process_document(str(file_path), document_type)
        else:
            result = ocr_processor.process_document(str(file_path), document_type)
        
        # Save to database if available
        if DATABASE_AVAILABLE:
            try:
                with get_db_session() as db:
                    doc = Document(
                        filename=file.filename,
                        document_type=document_type,
                        raw_text=result.get("raw_text", ""),
                        status="completed"
                    )
                    db.add(doc)
                    db.commit()
                    result["document_id"] = doc.id
            except Exception as e:
                print(f"Database error: {e}")
        
        return JSONResponse({
            "success": True,
            "filename": file.filename,
            "document_type": document_type,
            "result": result
        })
        
    except Exception as e:
        print(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents")
async def get_documents():
    """Get all documents"""
    if DATABASE_AVAILABLE:
        try:
            with get_db_session() as db:
                documents = db.query(Document).all()
                return [
                    {
                        "id": doc.id,
                        "filename": doc.filename,
                        "document_type": doc.document_type,
                        "raw_text": doc.raw_text,
                        "status": doc.status,
                        "created_at": doc.created_at.isoformat() if doc.created_at else None
                    }
                    for doc in documents
                ]
        except Exception as e:
            print(f"Database error: {e}")
            return []
    else:
        return [
            {
                "id": 1,
                "filename": "sample.pdf",
                "document_type": "faktur_pajak",
                "raw_text": "Sample document text (database not available)",
                "status": "completed",
                "created_at": "2025-09-29T12:00:00"
            }
        ]

if __name__ == "__main__":
    print("🚀 Starting Doc Scan AI Backend (Minimal Version)")
    print("=" * 50)
    print(f"📍 Working directory: {os.getcwd()}")
    print(f"🗄️  Database available: {DATABASE_AVAILABLE}")
    print(f"🔍 OCR available: {OCR_AVAILABLE}")
    print("=" * 50)
    
    # Start server
    uvicorn.run(
        "main_minimal:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )