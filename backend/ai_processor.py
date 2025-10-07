"""
AI Document Processor Module - Main Orchestrator
Coordinates OCR extraction, document parsing, confidence calculation, and export
Supports: Faktur Pajak, PPh21, PPh23, Rekening Koran, Invoice
Export: Excel & PDF (via modular exporter system)
"""

import os
import asyncio
import logging
from typing import Dict, Any

# Import modular components
from ocr_processor import RealOCRProcessor
from document_parser import IndonesianTaxDocumentParser
from confidence_calculator import (
    calculate_confidence,
    detect_document_type_from_filename,
    validate_extracted_data
)

logger = logging.getLogger(__name__)

# Import modular exporter system
HAS_EXPORTERS = False
try:
    from exporters import ExportFactory
    HAS_EXPORTERS = True
    logger.info("✅ Modular Exporter System Loaded")
except ImportError as e:
    logger.warning(f"⚠️ Modular exporter system not available: {e}")


# Global instances
ocr_processor = RealOCRProcessor()
parser = IndonesianTaxDocumentParser()


async def process_document_ai(file_path: str, document_type: str) -> Dict[str, Any]:
    """
    Main orchestrator function - Coordinates OCR → Parse → Confidence → Export
    
    Args:
        file_path: Path to document file
        document_type: Type of document (faktur_pajak, pph21, pph23, rekening_koran, invoice)
    
    Returns:
        Dictionary with extracted_data, confidence, raw_text, processing_time
    """
    start_time = asyncio.get_event_loop().time()
    try:
        logger.info(f"🔍 Processing {document_type} document: {file_path}")
        
        # Validate file exists
        if not os.path.exists(file_path):
            raise Exception(f"File not found: {file_path}")
        
        # Auto-detect document type from filename if needed
        if '.' in document_type and len(document_type) > 10:
            logger.warning(f"⚠️ Document type looks like filename: {document_type}")
            detected_type = detect_document_type_from_filename(document_type)
            logger.info(f"🔍 Auto-detected document type: {detected_type}")
            document_type = detected_type
        
        # STEP 1: Extract text using OCR
        extracted_text = await ocr_processor.extract_text(file_path)
        
        if not extracted_text:
            raise Exception("OCR failed to extract any text from the document. The file might be blank, corrupted, or unsupported.")
        
        logger.info(f"📝 Extracted {len(extracted_text)} characters of text")
        logger.info(f"📝 Sample text: {extracted_text[:200]}...")
        
        # STEP 2: Parse document based on type
        if document_type == 'faktur_pajak':
            extracted_data = parser.parse_faktur_pajak(extracted_text)
            # Merge structured fields from Cloud AI if available
            if ocr_processor.use_cloud_ai and ocr_processor.get_last_ocr_metadata():
                cloud_fields = ocr_processor.get_last_ocr_metadata().get('extracted_fields', {})
                if cloud_fields:
                    logger.info("✅ Merging structured data from Google Document AI")
                    extracted_data['extracted_content']['structured_fields'] = cloud_fields
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
        
        # STEP 3: Validate extracted data
        if not validate_extracted_data(extracted_data, document_type):
            logger.warning(f"⚠️ Limited data extracted from {document_type} document")
            # Don't raise exception - let it proceed with whatever data we have
        
        # Debug log
        logger.info(f"📊 EXTRACTED DATA for {document_type}:")
        if isinstance(extracted_data, dict):
            for section_key, section_data in extracted_data.items():
                if isinstance(section_data, dict):
                    non_empty_fields = {k: v for k, v in section_data.items() if v and str(v).strip()}
                    logger.info(f"   - {section_key}: {len(non_empty_fields)} non-empty fields")
                    for k, v in non_empty_fields.items():
                        logger.info(f"     • {k}: '{str(v)[:50]}{'...' if len(str(v)) > 50 else ''}'")
                else:
                    logger.info(f"   - {section_key}: {section_data}")

        # STEP 4: Calculate confidence
        confidence = calculate_confidence(extracted_text, document_type)
        logger.info(f"🎯 Final confidence for {document_type}: {confidence:.2%}")
        
        # Low confidence warning
        if confidence < 0.05:
            logger.warning(f"⚠️ Low OCR parsing confidence ({confidence:.2%}) but proceeding")
        
        # STEP 5: Prepare result
        processing_time = asyncio.get_event_loop().time() - start_time
        result = {
            "extracted_data": extracted_data,
            "confidence": confidence,
            "raw_text": extracted_text,
            "processing_time": processing_time
        }
        
        logger.info(f"✅ Successfully processed {document_type} with {confidence:.2%} confidence in {processing_time:.2f}s")
        logger.info(f"✅ Extracted data keys: {list(extracted_data.keys()) if isinstance(extracted_data, dict) else 'N/A'}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Failed to process document {file_path}: {e}")
        raise Exception(f"Real OCR processing failed: {e}")


# ============================================================================
# EXPORT FUNCTIONS (using modular exporter system)
# ============================================================================

def create_enhanced_excel_export(result: Dict[str, Any], output_path: str) -> bool:
    """Create enhanced Excel export using modular exporter system"""
    try:
        if not HAS_EXPORTERS:
            logger.error("❌ Modular exporters not available")
            return False
        
        # Get document type and select appropriate exporter
        doc_type = result.get('document_type', 'faktur_pajak')
        exporter = ExportFactory.get_exporter(doc_type)
        
        # Use exporter to create Excel
        return exporter.export_to_excel(result, output_path)
        
    except Exception as e:
        logger.error(f"❌ Excel export failed: {e}", exc_info=True)
        return False


def create_enhanced_pdf_export(result: Dict[str, Any], output_path: str) -> bool:
    """Create enhanced PDF export using modular exporter system"""
    try:
        if not HAS_EXPORTERS:
            logger.error("❌ Modular exporters not available")
            return False
        
        # Get document type and select appropriate exporter
        doc_type = result.get('document_type', 'faktur_pajak')
        exporter = ExportFactory.get_exporter(doc_type)
        
        # Use exporter to create PDF
        return exporter.export_to_pdf(result, output_path)
        
    except Exception as e:
        logger.error(f"❌ PDF export failed: {e}", exc_info=True)
        return False


def create_batch_excel_export(batch_id: str, results: list, output_path: str) -> bool:
    """Create batch Excel export using modular exporter system"""
    try:
        if not HAS_EXPORTERS:
            logger.error("❌ Modular exporters not available for batch Excel export")
            return False
        
        if not results:
            logger.error("❌ No results to export")
            return False
        
        # Get document type from first result (assume all same type in batch)
        doc_type = results[0].get('document_type', 'faktur_pajak')
        exporter = ExportFactory.get_exporter(doc_type)
        
        # Use exporter to create batch Excel
        return exporter.batch_export_to_excel(batch_id, results, output_path)
        
    except Exception as e:
        logger.error(f"❌ Batch Excel export failed: {e}", exc_info=True)
        return False


def create_batch_pdf_export(batch_id: str, results: list, output_path: str) -> bool:
    """Create batch PDF export using modular exporter system"""
    try:
        if not HAS_EXPORTERS:
            logger.error("❌ Modular exporters not available for batch PDF export")
            return False
        
        if not results:
            logger.error("❌ No results to export")
            return False
        
        # Get document type from first result (assume all same type in batch)
        doc_type = results[0].get('document_type', 'faktur_pajak')
        exporter = ExportFactory.get_exporter(doc_type)
        
        # Use exporter to create batch PDF
        return exporter.batch_export_to_pdf(batch_id, results, output_path)
        
    except Exception as e:
        logger.error(f"❌ Batch PDF export failed: {e}", exc_info=True)
        return False


# ============================================================================
# BACKWARD COMPATIBILITY - Re-export classes for existing code
# ============================================================================

# Re-export for backward compatibility
__all__ = [
    'RealOCRProcessor',
    'IndonesianTaxDocumentParser',
    'process_document_ai',
    'calculate_confidence',
    'detect_document_type_from_filename',
    'create_enhanced_excel_export',
    'create_enhanced_pdf_export',
    'create_batch_excel_export',
    'create_batch_pdf_export',
    'ocr_processor',
    'parser'
]
