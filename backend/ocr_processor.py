"""
OCR Processor Module - Simplified Version
Handles all OCR operations using ONLY Google Document AI
Fallback OCR engines (PaddleOCR, EasyOCR, RapidOCR) have been removed
Smart Mapper GPT handles field extraction from raw OCR text
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Try to import Cloud AI Processor (Google Document AI ONLY)
try:
    from cloud_ai_processor import CloudAIProcessor
    HAS_CLOUD_AI = True
    logger.info("✅ Cloud AI Processor loaded successfully (Google Document AI)")
except ImportError:
    HAS_CLOUD_AI = False
    logger.error("❌ Cloud AI Processor not available - System cannot function!")
    logger.error("Install with: pip install google-cloud-documentai")


class RealOCRProcessor:
    """Simplified OCR processor using ONLY Google Document AI
    
    All fallback OCR engines (PaddleOCR, EasyOCR, RapidOCR) have been removed.
    Smart Mapper GPT handles intelligent field extraction from raw OCR text.
    """
    
    def __init__(self):
        self.initialized = False
        self._last_ocr_result = None

        # Initialize Google Document AI processor
        if not HAS_CLOUD_AI:
            logger.critical("❌ Google Document AI not available - system cannot function!")
            logger.critical("Install with: pip install google-cloud-documentai")
            logger.critical("Configure GCP credentials: GOOGLE_APPLICATION_CREDENTIALS environment variable")
            return

        try:
            self.cloud_processor = CloudAIProcessor()
            logger.info("🚀 Google Document AI initialized successfully")
            self.initialized = True
        except Exception as e:
            logger.critical(f"❌ Failed to initialize Google Document AI: {e}", exc_info=True)
            logger.critical("System cannot function without Google Document AI!")
            self.initialized = False
    
    async def extract_text(self, file_path: str) -> str:
        """Extract text using Google Document AI ONLY
        
        No fallback OCR engines. If Google Document AI fails, the system cannot process the document.
        Smart Mapper GPT handles field extraction from the raw OCR text.
        """
        if not self.initialized:
            logger.error("❌ OCR processor not initialized - Google Document AI unavailable")
            return ""
            
        if not os.path.exists(file_path):
            logger.error(f"❌ File not found: {file_path}")
            return ""
        
        file_ext = Path(file_path).suffix.lower()
        logger.info(f"🔍 Processing {file_ext} file with Google Document AI: {file_path}")
        
        # Use Google Document AI (ONLY option)
        try:
            result = await self.cloud_processor.process_with_google(file_path)
            
            if result and result.raw_text:
                logger.info(f"✅ Google Document AI success: {len(result.raw_text)} chars, {result.confidence:.1f}% confidence")
                self._last_ocr_result = {
                    'text': result.raw_text,
                    'extracted_fields': result.extracted_fields,
                    'confidence': result.confidence,
                    'engine_used': result.service_used,
                    'quality_score': result.confidence,
                    'processing_time': result.processing_time,
                    'raw_response': result.raw_response
                }
                return result.raw_text
            else:
                logger.error("❌ Google Document AI returned no text")
                logger.error("Check: 1) GCP credentials, 2) Processor ID, 3) GCP console logs")
                return ""
                
        except Exception as e:
            logger.error(f"❌ Google Document AI processing failed: {e}", exc_info=True)
            return ""
    
    def get_last_ocr_metadata(self) -> Optional[Dict[str, Any]]:
        """Get metadata from the last OCR operation"""
        return self._last_ocr_result
    
    def get_ocr_system_info(self) -> Dict[str, Any]:
        """Get information about OCR system (Google Document AI only)"""
        return {
            'ocr_engine': 'Google Document AI',
            'initialized': self.initialized,
            'fallback_engines': None,  # No fallbacks
            'smart_mapper_enabled': True
        }

# REMOVED METHODS:
# - preprocess_image() - No longer needed, Google Doc AI handles preprocessing
# - extract_text_easyocr() - EasyOCR removed
# - extract_text_tesseract() - Tesseract removed  
# - extract_text_from_pdf() - Google Doc AI handles PDFs directly
# All fallback OCR engines have been removed to simplify codebase
