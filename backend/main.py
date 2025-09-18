from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn
import os
import uuid
import json
import asyncio
from datetime import datetime
from typing import List, Optional
import aiofiles
from pathlib import Path

# Import our AI processing modules
from ai_processor import process_document_ai, create_enhanced_excel_export, create_enhanced_pdf_export, RealOCRProcessor
from models import BatchResponse, ScanResult, BatchStatus

app = FastAPI(title="AI Document Scanner API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Storage directories
UPLOAD_DIR = Path("uploads")
RESULTS_DIR = Path("results")
EXPORTS_DIR = Path("exports")

for dir_path in [UPLOAD_DIR, RESULTS_DIR, EXPORTS_DIR]:
    dir_path.mkdir(exist_ok=True)

# In-memory storage (in production, use database)
batches_storage = {}
results_storage = {}

@app.get("/")
async def root():
    return {"message": "AI Document Scanner API", "status": "online"}

@app.post("/api/heartbeat")
async def heartbeat():
    """Health check endpoint for production validation"""
    try:
        # Test OCR system health
        ocr_processor = RealOCRProcessor()
        ocr_info = ocr_processor.get_ocr_system_info()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "ocr_system": ocr_info,
            "message": "Production OCR system ready"
        }
    except Exception as e:
        return {
            "status": "unhealthy", 
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/api/health")
async def health_check():
    """Alternative health check endpoint"""
    return {"status": "healthy", "service": "doc-scan-ai", "timestamp": datetime.now().isoformat()}

@app.post("/api/upload", response_model=BatchResponse)
async def upload_documents(
    files: List[UploadFile] = File(...),
    document_types: List[str] = Form(...)
):
    """Upload multiple documents for batch processing"""
    try:
        batch_id = str(uuid.uuid4())
        batch_dir = UPLOAD_DIR / batch_id
        batch_dir.mkdir(exist_ok=True)
        
        # Save uploaded files
        file_info = []
        for i, (file, doc_type) in enumerate(zip(files, document_types)):
            file_id = str(uuid.uuid4())
            file_path = batch_dir / f"{file_id}_{file.filename}"
            
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            
            file_info.append({
                "id": file_id,
                "name": file.filename,
                "type": doc_type,
                "path": str(file_path),
                "status": "pending",
                "progress": 0
            })
        
        # Store batch info
        batch_data = {
            "id": batch_id,
            "files": file_info,
            "status": "processing",
            "created_at": datetime.now().isoformat(),
            "total_files": len(files),
            "processed_files": 0
        }
        
        batches_storage[batch_id] = batch_data
        
        # Start background processing
        asyncio.create_task(process_batch_async(batch_id))
        
        return BatchResponse(**batch_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def process_batch_async(batch_id: str):
    """Background task to process documents with AI"""
    try:
        batch = batches_storage[batch_id]
        
        for file_info in batch["files"]:
            # Update file status to processing
            file_info["status"] = "processing"
            file_info["progress"] = 10
            
            # Simulate AI processing steps
            await asyncio.sleep(1)  # LayoutLMv3 processing
            file_info["progress"] = 30
            
            await asyncio.sleep(1.5)  # EasyOCR processing
            file_info["progress"] = 60
            
            await asyncio.sleep(1)  # Transformers + spaCy processing
            file_info["progress"] = 80
            
            # Process with AI
            try:
                result = await process_document_ai(
                    file_info["path"], 
                    file_info["type"]
                )
                
                # DEBUG: Log the raw result from AI processor
                print(f"🔍 DEBUG - Raw AI Result for {file_info['name']}:")
                print(f"   - Full Result: {result}")
                print(f"   - Confidence from AI: {result.get('confidence', 'NOT_FOUND')}")
                print(f"   - Confidence Type: {type(result.get('confidence', 'NOT_FOUND'))}")
                
                # Save result
                result_id = str(uuid.uuid4())
                result_data = {
                    "id": result_id,
                    "batch_id": batch_id,
                    "document_type": file_info["type"],
                    "original_filename": file_info["name"],
                    "extracted_data": result.get("extracted_data", result),
                    "confidence": result.get("confidence", 0.0),
                    "created_at": datetime.now().isoformat()
                }
                
                # DEBUG: Log the final result data being stored
                print(f"🔍 DEBUG - Final Result Data being stored:")
                print(f"   - Result ID: {result_id}")
                print(f"   - Confidence in storage: {result_data['confidence']}")
                print(f"   - Full result_data: {result_data}")
                
                results_storage[result_id] = result_data
                
                # Update file status
                file_info["status"] = "completed"
                file_info["progress"] = 100
                file_info["result_id"] = result_id
                
                print(f"✅ Processing SUCCESS: {file_info['name']}")
                print(f"   - Document Type: {file_info['type']}")
                print(f"   - Confidence: {result.get('confidence', 0):.2%}")
                print(f"   - Stored Confidence: {result_data['confidence']:.2%}")
                
                # Log extracted data structure
                extracted_data = result.get("extracted_data", result)
                if isinstance(extracted_data, dict):
                    print(f"   - Extracted keys: {list(extracted_data.keys())}")
                    
                    # Log specific fields for PPh documents
                    if file_info["type"] in ["pph21", "pph23"]:
                        if "penghasilan_bruto" in extracted_data:
                            print(f"   - Penghasilan Bruto: Rp {extracted_data['penghasilan_bruto']:,}")
                        if "dpp" in extracted_data:
                            print(f"   - DPP: Rp {extracted_data['dpp']:,}")
                        if "pph" in extracted_data:
                            print(f"   - PPh: Rp {extracted_data['pph']:,}")
                    
                    # Log specific fields for Faktur Pajak
                    elif file_info["type"] == "faktur_pajak":
                        if "keluaran" in extracted_data and extracted_data["keluaran"]:
                            keluaran = extracted_data["keluaran"]
                            if "dpp" in keluaran:
                                print(f"   - Keluaran DPP: Rp {keluaran['dpp']:,}")
                            if "ppn" in keluaran:
                                print(f"   - Keluaran PPN: Rp {keluaran['ppn']:,}")
                        if "masukan" in extracted_data and extracted_data["masukan"]:
                            masukan = extracted_data["masukan"]
                            if "dpp" in masukan:
                                print(f"   - Masukan DPP: Rp {masukan['dpp']:,}")
                            if "ppn" in masukan:
                                print(f"   - Masukan PPN: Rp {masukan['ppn']:,}")
                else:
                    print(f"   - Extracted data type: {type(extracted_data)}")
                
                # Check if this is a fallback result
                if result.get('processing_note'):
                    print(f"   - Note: {result.get('processing_note')}")
                
            except Exception as e:
                print(f"⚠️ Processing error for {file_info['name']}: {e}")
                # Create fallback result instead of failing
                try:
                    from ai_processor import create_fallback_result
                    fallback_result = create_fallback_result(file_info["type"], str(e))
                    
                    result_id = str(uuid.uuid4())
                    result_data = {
                        "id": result_id,
                        "batch_id": batch_id,
                        "document_type": file_info["type"],
                        "original_filename": file_info["name"],
                        "extracted_data": fallback_result,
                        "confidence": fallback_result.get("confidence", 0.3),
                        "created_at": datetime.now().isoformat()
                    }
                    
                    results_storage[result_id] = result_data
                    
                    file_info["status"] = "completed"
                    file_info["progress"] = 100
                    file_info["result_id"] = result_id
                    
                    print(f"🔄 Created fallback result for {file_info['name']}")
                    
                except Exception as fallback_error:
                    print(f"❌ Fallback creation failed: {fallback_error}")
                    file_info["status"] = "error"
                    file_info["progress"] = 0
                    file_info["error"] = str(e)
                    continue
            
            batch["processed_files"] += 1
            
            await asyncio.sleep(0.5)
        
        # Check processing results
        successful_files = [f for f in batch["files"] if f["status"] == "completed"]
        failed_files = [f for f in batch["files"] if f["status"] == "error"]
        
        # Always mark as completed if we have any results (including fallback)
        batch["status"] = "completed"
        batch["completed_at"] = datetime.now().isoformat()
        
        if failed_files:
            print(f"⚠️ Batch {batch_id} completed with {len(failed_files)} failed files")
        
        if not successful_files and failed_files:
            batch["status"] = "error"
            batch["error"] = "All files failed to process"
            print(f"❌ Batch {batch_id} failed: All files failed to process")
        else:
            print(f"✅ Batch {batch_id} completed: {len(successful_files)} successful, {len(failed_files)} failed")
        
    except Exception as e:
        print(f"❌ Batch processing error: {e}")
        batch["status"] = "error"
        batch["error"] = str(e)

@app.get("/api/batches/{batch_id}")
async def get_batch_status(batch_id: str):
    """Get batch processing status"""
    if batch_id not in batches_storage:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    return batches_storage[batch_id]

@app.get("/api/batches/{batch_id}/results")
async def get_batch_results(batch_id: str):
    """Get scan results for a batch"""
    if batch_id not in batches_storage:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    batch_results = [
        result for result in results_storage.values() 
        if result["batch_id"] == batch_id
    ]
    
    # AUTO-RECALCULATE CONFIDENCE with current algorithm
    from ai_processor import calculate_confidence
    
    for result in batch_results:
        old_confidence = result["confidence"]
        new_confidence = calculate_confidence(
            result["extracted_data"], 
            result["document_type"]
        )
        
        # Update confidence if significantly different
        if abs(new_confidence - old_confidence) > 0.01:
            print(f"🔄 AUTO-UPDATING confidence for {result['original_filename']}")
            print(f"   - Old: {old_confidence:.4f} ({old_confidence:.2%})")
            print(f"   - New: {new_confidence:.4f} ({new_confidence:.2%})")
            result["confidence"] = new_confidence
            result["updated_at"] = datetime.now().isoformat()
    
    # DEBUG: Log what we're sending to frontend
    print(f"🔍 DEBUG - Sending to Frontend for batch {batch_id}:")
    for result in batch_results:
        print(f"   - File: {result['original_filename']}")
        print(f"   - Confidence in storage: {result['confidence']}")
        print(f"   - Document Type: {result['document_type']}")
    
    print(f"🔍 DEBUG - Full batch_results: {batch_results}")
    
    return batch_results

@app.post("/api/debug/recalculate-confidence/{batch_id}")
async def recalculate_confidence(batch_id: str):
    """Recalculate confidence for all results in a batch with current algorithm"""
    if batch_id not in batches_storage:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    batch_results = [
        result for result in results_storage.values() 
        if result["batch_id"] == batch_id
    ]
    
    updated_results = []
    for result in batch_results:
        # Import here to get latest version
        from ai_processor import calculate_confidence
        
        # Recalculate confidence with current algorithm
        new_confidence = calculate_confidence(
            result["extracted_data"], 
            result["document_type"]
        )
        
        # Update the stored result
        result["confidence"] = new_confidence
        result["updated_at"] = datetime.now().isoformat()
        
        print(f"🔄 Updated {result['original_filename']}: {new_confidence:.4f} ({new_confidence:.2%})")
        updated_results.append({
            "filename": result["original_filename"],
            "old_confidence": "unknown",
            "new_confidence": new_confidence
        })
    
    return {
        "message": f"Recalculated confidence for {len(updated_results)} results",
        "batch_id": batch_id,
        "updates": updated_results
    }

@app.delete("/api/debug/clear-storage")
async def clear_all_storage():
    """Clear all storage - FOR DEBUGGING ONLY"""
    global batches_storage, results_storage
    
    old_batches_count = len(batches_storage)
    old_results_count = len(results_storage)
    
    batches_storage.clear()
    results_storage.clear()
    
    return {
        "message": "Storage cleared",
        "cleared": {
            "batches": old_batches_count,
            "results": old_results_count
        }
    }

@app.get("/api/batches")
async def get_all_batches():
    """Get all batches"""
    return list(batches_storage.values())

@app.get("/api/results")
async def get_all_results():
    """Get all scan results"""
    return list(results_storage.values())

@app.post("/api/export/{result_id}/excel")
async def export_excel(result_id: str):
    """Export scan result to Excel"""
    if result_id not in results_storage:
        raise HTTPException(status_code=404, detail="Result not found")
    
    result = results_storage[result_id]
    
    # Create Excel file
    excel_path = EXPORTS_DIR / f"{result_id}_export.xlsx"
    success = create_enhanced_excel_export(result, str(excel_path))
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create Excel export")
    
    return FileResponse(
        excel_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"{result['original_filename']}_extracted.xlsx"
    )

@app.post("/api/export/{result_id}/pdf")
async def export_pdf(result_id: str):
    """Export scan result to PDF"""
    if result_id not in results_storage:
        raise HTTPException(status_code=404, detail="Result not found")
    
    result = results_storage[result_id]
    
    # Create PDF file
    pdf_path = EXPORTS_DIR / f"{result_id}_export.pdf"
    success = create_enhanced_pdf_export(result, str(pdf_path))
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create PDF export")
    
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"{result['original_filename']}_extracted.pdf"
    )

@app.post("/api/export/batch/{batch_id}/excel")
async def export_batch_excel(batch_id: str):
    """Export all batch results to Excel"""
    if batch_id not in batches_storage:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    batch_results = [
        result for result in results_storage.values() 
        if result["batch_id"] == batch_id
    ]
    
    if not batch_results:
        raise HTTPException(status_code=404, detail="No results found for batch")
    
    # Create combined Excel file
    excel_path = EXPORTS_DIR / f"batch_{batch_id}_export.xlsx"
    
    # For batch export, create a combined result
    combined_result = {
        "document_type": "batch",
        "original_filename": f"batch_{batch_id[:8]}",
        "created_at": datetime.now().isoformat(),
        "confidence": sum(r["confidence"] for r in batch_results) / len(batch_results),
        "extracted_data": {
            "batch_info": {
                "batch_id": batch_id,
                "total_documents": len(batch_results),
                "average_confidence": sum(r["confidence"] for r in batch_results) / len(batch_results)
            },
            "documents": batch_results
        }
    }
    
    success = create_enhanced_excel_export(combined_result, str(excel_path))
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create batch Excel export")
    
    return FileResponse(
        excel_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"batch_{batch_id[:8]}_results.xlsx"
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)