#!/usr/bin/env python3
"""
SYNC WRAPPER untuk ASYNC OCR Functions
Untuk compatibility dengan sistem existing
"""

import asyncio
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

def process_document_ai_sync(file_path: str, document_type: str) -> Dict[str, Any]:
    """Synchronous wrapper for async process_document_ai"""
    try:
        from ai_processor import process_document_ai
        
        # Run the async function in a new event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If there's already a running loop, we need to use a different approach
                import concurrent.futures
                import threading
                
                def run_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(process_document_ai(file_path, document_type))
                    finally:
                        new_loop.close()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_thread)
                    return future.result()
            else:
                return loop.run_until_complete(process_document_ai(file_path, document_type))
        except RuntimeError:
            # No event loop, create a new one
            return asyncio.run(process_document_ai(file_path, document_type))
            
    except Exception as e:
        logger.error(f"❌ Sync wrapper failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "extracted_data": {},
            "confidence": 0.0,
            "processing_time": 0.0,
            "ocr_text": ""
        }

# For backward compatibility, we'll also provide the old sync version
def process_document_ai_legacy(file_path: str, document_type: str) -> Dict[str, Any]:
    """Legacy sync version for backward compatibility"""
    try:
        from ai_processor import parser
        
        logger.info(f"🔍 Processing {document_type} document: {file_path}")
        
        # Use sync version of OCR extraction
        extracted_text = ""
        
        # Try to extract text using fallback methods
        if parser.ocr_processor.use_nextgen:
            logger.info("⚠️ Next-gen OCR requires async, falling back to sync methods")
        
        # Use enhanced or basic OCR processors
        if hasattr(parser.ocr_processor, 'enhanced_processor') and parser.ocr_processor.use_enhanced:
            try:
                result = parser.ocr_processor.enhanced_processor.process_document(file_path)
                if result['success'] and result['text']:
                    extracted_text = result['text']
                    logger.info(f"✅ Enhanced OCR extracted {len(extracted_text)} characters")
            except Exception as e:
                logger.error(f"❌ Enhanced OCR failed: {e}")
        
        # Fallback to basic methods if needed
        if not extracted_text:
            logger.info("📎 Using basic OCR fallback methods")
            
            # Try EasyOCR
            if hasattr(parser.ocr_processor, 'readers') and 'easyocr' in parser.ocr_processor.readers:
                try:
                    import cv2
                    image = cv2.imread(file_path)
                    if image is not None:
                        result = parser.ocr_processor.readers['easyocr'].readtext(image)
                        extracted_text = ' '.join([item[1] for item in result if item[1]])
                        logger.info(f"✅ EasyOCR extracted {len(extracted_text)} characters")
                except Exception as e:
                    logger.error(f"❌ EasyOCR fallback failed: {e}")
        
        if not extracted_text:
            raise Exception("OCR failed - no text could be extracted from the document")
        
        # Parse based on document type
        if document_type == 'faktur_pajak':
            extracted_data = parser.parse_faktur_pajak(extracted_text)
        elif document_type == 'pph21':
            extracted_data = parser.parse_pph21(extracted_text)
        elif document_type == 'pph23':
            extracted_data = parser.parse_pph23(extracted_text)
        elif document_type == 'rekening_koran':
            extracted_data = parser.parse_rekening_koran(extracted_text)
        elif document_type == 'invoice':
            extracted_data = parser.parse_invoice(extracted_text)
        else:
            logger.warning(f"⚠️ Unknown document type: {document_type}, defaulting to faktur_pajak")
            extracted_data = parser.parse_faktur_pajak(extracted_text)
        
        # Calculate confidence
        from ai_processor import calculate_confidence
        confidence = calculate_confidence(extracted_data, document_type)
        
        return {
            "success": True,
            "extracted_data": extracted_data,
            "confidence": confidence,
            "processing_time": 1.0,  # Dummy value
            "ocr_text": extracted_text,
            "file_path": file_path,
            "document_type": document_type
        }
        
    except Exception as e:
        logger.error(f"❌ Legacy OCR processing failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "extracted_data": {},
            "confidence": 0.0,
            "processing_time": 0.0,
            "ocr_text": ""
        }