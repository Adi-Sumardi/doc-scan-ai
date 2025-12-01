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
from pathlib import Path

# Import modular components
from ocr_processor import RealOCRProcessor
from document_parser import IndonesianTaxDocumentParser
from confidence_calculator import (
    calculate_confidence,
    detect_document_type_from_filename,
    validate_extracted_data
)
from pdf_chunker import pdf_chunker

logger = logging.getLogger(__name__)

# Import modular exporter system
HAS_EXPORTERS = False
try:
    from exporters import ExportFactory
    HAS_EXPORTERS = True
    logger.info("✅ Modular Exporter System Loaded")
except ImportError as e:
    logger.warning(f"⚠️ Modular exporter system not available: {e}")

HAS_SMART_MAPPER = False
try:
    from smart_mapper import smart_mapper_service

    HAS_SMART_MAPPER = getattr(smart_mapper_service, "enabled", False)
    if HAS_SMART_MAPPER:
        logger.info("✅ Smart Mapper service loaded")
    else:
        logger.warning("⚠️ Smart Mapper available but disabled")
except ImportError as e:
    smart_mapper_service = None  # type: ignore
    logger.warning(f"⚠️ Smart Mapper service not available: {e}")


# Global instances
ocr_processor = RealOCRProcessor()
parser = IndonesianTaxDocumentParser()


async def process_with_chunking(file_path: str, document_type: str) -> tuple:
    """
    Process large PDF file with chunking strategy

    Args:
        file_path: Path to large PDF file
        document_type: Type of document (rekening_koran, etc.)

    Returns:
        tuple: (merged_text, merged_metadata)
    """
    try:
        logger.info("=" * 80)
        logger.info("🔄 CHUNKING MODE ACTIVATED")
        logger.info("=" * 80)

        # Get page count
        page_count = pdf_chunker.get_page_count(file_path)

        # Import settings
        try:
            from config import settings
            chunk_size = settings.pdf_chunk_size
        except:
            chunk_size = 15

        logger.info(f"📄 File: {Path(file_path).name}")
        logger.info(f"📊 Total pages: {page_count}")
        logger.info(f"📦 Chunk size: {chunk_size} pages")
        logger.info(f"🔢 Expected chunks: {(page_count + chunk_size - 1) // chunk_size}")

        # Split PDF into chunks
        chunk_dir = str(Path(file_path).parent / "chunks")
        chunks = pdf_chunker.split_pdf_to_chunks(file_path, output_dir=chunk_dir)

        if not chunks:
            raise Exception("Failed to split PDF into chunks")

        logger.info(f"✅ Successfully created {len(chunks)} chunks")
        logger.info("=" * 80)

        # Process each chunk
        chunk_results = []

        for i, chunk_info in enumerate(chunks, 1):
            logger.info(f"")
            logger.info(f"{'=' * 40} CHUNK {i}/{len(chunks)} {'=' * 40}")
            logger.info(f"📄 Pages: {chunk_info['start_page']}-{chunk_info['end_page']}")
            logger.info(f"📁 File: {Path(chunk_info['path']).name}")

            try:
                # Extract text from chunk using OCR
                chunk_text = await ocr_processor.extract_text(chunk_info['path'])

                if not chunk_text:
                    logger.warning(f"⚠️ Chunk {i} returned no text")
                    continue

                logger.info(f"✅ Extracted {len(chunk_text)} characters from chunk {i}")

                # Get OCR metadata for this chunk
                chunk_ocr_metadata = ocr_processor.get_last_ocr_metadata()

                # Build OCR result for this chunk (needed for enhanced_bank_processor)
                tables = []
                if chunk_ocr_metadata:
                    raw_response = chunk_ocr_metadata.get('raw_response')
                    if raw_response and isinstance(raw_response, dict):
                        pages = raw_response.get('pages', [])
                        for page in pages:
                            if isinstance(page, dict) and 'tables' in page:
                                page_tables = page.get('tables', [])
                                if isinstance(page_tables, list):
                                    tables.extend(page_tables)

                        logger.info(f"   📊 Chunk {i}: Extracted {len(tables)} tables")

                # Create chunk result with proper structure
                chunk_result = {
                    'raw_text': chunk_text,
                    'extracted_text': chunk_text,
                    'extracted_data': {
                        'raw_response': chunk_ocr_metadata.get('raw_response') if chunk_ocr_metadata else {}
                    },
                    'chunk_info': chunk_info,
                    'tables': tables
                }

                chunk_results.append(chunk_result)

            except Exception as e:
                logger.error(f"❌ Chunk {i} processing failed: {e}")
                import traceback
                logger.error(traceback.format_exc())
                # Continue with other chunks

        logger.info("")
        logger.info("=" * 80)
        logger.info("🔗 MERGING CHUNK RESULTS")
        logger.info("=" * 80)

        # Cleanup chunk files
        logger.info("🧹 Cleaning up temporary chunk files...")
        pdf_chunker.cleanup_chunks([c['path'] for c in chunks])
        logger.info("✅ Cleanup complete")

        if not chunk_results:
            raise Exception("All chunks failed to process - no valid data extracted")

        logger.info(f"✅ Successfully processed {len(chunk_results)} out of {len(chunks)} chunks")

        # Merge chunk results
        logger.info("🔗 Merging extracted data from all chunks...")
        merged = pdf_chunker.merge_extracted_data(chunk_results, document_type)

        # Extract merged text and metadata
        merged_text = merged.get('raw_text', '') or merged.get('extracted_text', '')

        # Build metadata structure compatible with main flow
        merged_metadata = {
            'text': merged_text,
            'extracted_fields': {},
            'confidence': 90.0,  # Average confidence for chunked processing
            'engine_used': f'Google Document AI (Chunked: {len(chunk_results)} chunks)',
            'quality_score': 90.0,
            'processing_time': 0,
            'raw_response': merged.get('extracted_data', {}).get('raw_response', {})
        }

        logger.info(f"✅ Merge complete: {len(merged_text)} total characters")
        logger.info("=" * 80)

        return merged_text, merged_metadata

    except Exception as e:
        logger.error(f"❌ Chunking process failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


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

        # STEP 1: Extract text using OCR (with smart chunking for large rekening koran)
        # Check if file needs chunking (only for rekening_koran with many pages)
        needs_chunking = False
        page_count = 0

        if document_type == 'rekening_koran' and file_path.lower().endswith('.pdf'):
            try:
                page_count = pdf_chunker.get_page_count(file_path)
                logger.info(f"📄 Rekening Koran PDF: {page_count} pages")

                # Import settings to check chunking config
                try:
                    from config import settings
                    chunk_enabled = settings.enable_page_chunking
                    chunk_threshold = settings.pdf_chunk_size
                except:
                    chunk_enabled = True
                    chunk_threshold = 15

                if chunk_enabled and page_count > chunk_threshold:
                    needs_chunking = True
                    logger.info(f"📚 File needs chunking ({page_count} pages > {chunk_threshold} threshold)")
            except Exception as e:
                logger.warning(f"⚠️ Could not determine page count: {e}")

        if needs_chunking:
            logger.info(f"📚 Processing with CHUNKING: {page_count} pages")
            extracted_text, ocr_metadata = await process_with_chunking(file_path, document_type)
        else:
            logger.info("📄 Processing as SINGLE DOCUMENT (no chunking needed)")
            extracted_text = await ocr_processor.extract_text(file_path)
            ocr_metadata = ocr_processor.get_last_ocr_metadata()
        
        if not extracted_text:
            raise Exception("OCR failed to extract any text from the document. The file might be blank, corrupted, or unsupported.")
        
        logger.info(f"📝 Extracted {len(extracted_text)} characters of text")
        logger.info(f"📝 Sample text: {extracted_text[:200]}...")
        
        # STEP 2: Parse document based on type
        if document_type == 'faktur_pajak':
            extracted_data = parser.parse_faktur_pajak(extracted_text, file_path=file_path)
            # Merge structured fields from Google Document AI if available
            ocr_metadata = ocr_processor.get_last_ocr_metadata()
            if ocr_metadata:
                cloud_fields = ocr_metadata.get('extracted_fields', {})
                if cloud_fields:
                    logger.info("✅ Merging structured data from Google Document AI")
                    extracted_data['extracted_content']['structured_fields'] = cloud_fields
            if HAS_SMART_MAPPER and smart_mapper_service and isinstance(extracted_data, dict):
                template = smart_mapper_service.load_template(document_type)
                ocr_metadata = ocr_processor.get_last_ocr_metadata()
                ocr_meta_dict = ocr_metadata if isinstance(ocr_metadata, dict) else {}
                raw_response = ocr_meta_dict.get('raw_response')
                if template and raw_response:
                    mapped = smart_mapper_service.map_document(
                        doc_type=document_type,
                        document_json=raw_response,
                        template=template,
                        extracted_fields=ocr_meta_dict.get('extracted_fields'),
                        fallback_fields=extracted_data.get('structured_data'),
                    )
                    if mapped:
                        extracted_data.setdefault('structured_data', {})
                        extracted_data['structured_data']['smart_mapper'] = mapped
                        extracted_data['smart_mapped'] = mapped
        elif document_type == 'pph21':
            extracted_data = parser.parse_pph21(extracted_text)
            # Merge structured fields from Google Document AI if available
            ocr_metadata = ocr_processor.get_last_ocr_metadata()
            if ocr_metadata:
                cloud_fields = ocr_metadata.get('extracted_fields', {})
                if cloud_fields:
                    logger.info("✅ Merging structured data from Google Document AI for PPh 21")
                    extracted_data['extracted_content']['structured_fields'] = cloud_fields
            # Apply Smart Mapper for PPh 21
            if HAS_SMART_MAPPER and smart_mapper_service and isinstance(extracted_data, dict):
                template = smart_mapper_service.load_template(document_type)
                ocr_metadata = ocr_processor.get_last_ocr_metadata()
                ocr_meta_dict = ocr_metadata if isinstance(ocr_metadata, dict) else {}
                raw_response = ocr_meta_dict.get('raw_response')
                if template and raw_response:
                    logger.info("🤖 Applying Smart Mapper GPT-4o for PPh 21")
                    mapped = smart_mapper_service.map_document(
                        doc_type=document_type,
                        document_json=raw_response,
                        template=template,
                        extracted_fields=ocr_meta_dict.get('extracted_fields'),
                        fallback_fields=extracted_data.get('structured_data'),
                    )
                    if mapped:
                        logger.info("✅ Smart Mapper PPh 21 successful!")
                        extracted_data.setdefault('structured_data', {})
                        extracted_data['structured_data']['smart_mapper'] = mapped
                        extracted_data['smart_mapped'] = mapped
                    else:
                        logger.warning("⚠️ Smart Mapper PPh 21 returned no data")
                else:
                    if not template:
                        logger.warning(f"⚠️ No template found for {document_type}")
                    if not raw_response:
                        logger.warning("⚠️ No raw OCR response available for Smart Mapper")
        elif document_type == 'pph23':
            extracted_data = parser.parse_pph23(extracted_text)
            # Merge structured fields from Google Document AI if available
            ocr_metadata = ocr_processor.get_last_ocr_metadata()
            if ocr_metadata:
                cloud_fields = ocr_metadata.get('extracted_fields', {})
                if cloud_fields:
                    logger.info("✅ Merging structured data from Google Document AI for PPh 23")
                    extracted_data['extracted_content']['structured_fields'] = cloud_fields
            # Apply Smart Mapper for PPh 23
            if HAS_SMART_MAPPER and smart_mapper_service and isinstance(extracted_data, dict):
                template = smart_mapper_service.load_template(document_type)
                ocr_metadata = ocr_processor.get_last_ocr_metadata()
                ocr_meta_dict = ocr_metadata if isinstance(ocr_metadata, dict) else {}
                raw_response = ocr_meta_dict.get('raw_response')
                if template and raw_response:
                    logger.info("🤖 Applying Smart Mapper GPT-4o for PPh 23")
                    mapped = smart_mapper_service.map_document(
                        doc_type=document_type,
                        document_json=raw_response,
                        template=template,
                        extracted_fields=ocr_meta_dict.get('extracted_fields'),
                        fallback_fields=extracted_data.get('structured_data'),
                    )
                    if mapped:
                        logger.info("✅ Smart Mapper PPh 23 successful!")
                        extracted_data.setdefault('structured_data', {})
                        extracted_data['structured_data']['smart_mapper'] = mapped
                        extracted_data['smart_mapped'] = mapped
                    else:
                        logger.warning("⚠️ Smart Mapper PPh 23 returned no data")
                else:
                    if not template:
                        logger.warning(f"⚠️ No template found for {document_type}")
                    if not raw_response:
                        logger.warning("⚠️ No raw OCR response available for Smart Mapper")
        elif document_type == 'rekening_koran':
            # ============================================================
            # SIMPLIFIED REKENING KORAN PROCESSING
            # ============================================================
            # NEW FLOW: Google Document AI (OCR) → Claude AI → Excel
            # NO MORE: Bank detection, bank adapters, rule-based parsing
            # ============================================================

            logger.info("=" * 60)
            logger.info("🏦 REKENING KORAN - SIMPLIFIED CLAUDE AI PROCESSING")
            logger.info("=" * 60)

            # Get OCR metadata
            if not ocr_metadata:
                ocr_metadata = ocr_processor.get_last_ocr_metadata()

            # Get raw_response for Smart Mapper
            ocr_meta_dict = ocr_metadata if isinstance(ocr_metadata, dict) else {}
            raw_response = ocr_meta_dict.get('raw_response')

            # 🔍 DEBUG: Check what we have
            logger.info(f"🔍 DEBUG - ocr_metadata type: {type(ocr_metadata)}")
            logger.info(f"🔍 DEBUG - ocr_metadata keys: {list(ocr_meta_dict.keys()) if ocr_meta_dict else 'None'}")
            logger.info(f"🔍 DEBUG - raw_response available: {raw_response is not None}")
            logger.info(f"🔍 DEBUG - HAS_SMART_MAPPER: {HAS_SMART_MAPPER}")

            # Parse rekening koran (now returns raw text for Smart Mapper)
            extracted_data = await parser.parse_rekening_koran(extracted_text)

            # ALWAYS use Smart Mapper (Claude AI) for Rekening Koran
            if HAS_SMART_MAPPER and smart_mapper_service:
                logger.info("🤖 Using Claude AI (Smart Mapper) for universal bank statement extraction")
                template = smart_mapper_service.load_template(document_type)
                logger.info(f"🔍 DEBUG - template loaded: {template is not None}")

                if template and raw_response:
                    logger.info("📋 Template loaded, calling Claude AI...")
                    mapped = smart_mapper_service.map_document(
                        doc_type=document_type,
                        document_json=raw_response,
                        template=template,
                        extracted_fields=ocr_meta_dict.get('extracted_fields'),
                        fallback_fields=extracted_data.get('structured_data'),
                    )
                    if mapped:
                        logger.info("✅ Claude AI extraction successful!")
                        extracted_data.setdefault('structured_data', {})
                        extracted_data['structured_data']['smart_mapper'] = mapped
                        extracted_data['smart_mapped'] = mapped
                        logger.info(f"🔍 DEBUG - smart_mapped added to extracted_data, keys now: {list(extracted_data.keys())}")

                        # Update transactions if extracted
                        if mapped.get('transactions'):
                            extracted_data['transactions'] = mapped['transactions']
                            logger.info(f"   📊 Extracted {len(mapped['transactions'])} transactions")
                    else:
                        logger.warning("⚠️ Claude AI returned no data (mapped is None/empty)")
                else:
                    if not template:
                        logger.warning(f"⚠️ No template found for {document_type}")
                    if not raw_response:
                        logger.warning("⚠️ No raw OCR response available - CANNOT CALL CLAUDE AI!")
            else:
                logger.warning("⚠️ Smart Mapper not available, returning raw OCR text only")

            # 🔍 DEBUG: Final check before returning
            logger.info(f"🔍 DEBUG - FINAL extracted_data keys: {list(extracted_data.keys())}")
            logger.info(f"🔍 DEBUG - FINAL has smart_mapped: {'smart_mapped' in extracted_data}")
        elif document_type == 'invoice':
            extracted_data = parser.parse_invoice(extracted_text)
            # Merge structured fields from Google Document AI if available
            ocr_metadata = ocr_processor.get_last_ocr_metadata()
            if ocr_metadata:
                cloud_fields = ocr_metadata.get('extracted_fields', {})
                if cloud_fields:
                    logger.info("✅ Merging structured data from Google Document AI for Invoice")
                    extracted_data['extracted_content']['structured_fields'] = cloud_fields
            # Apply Smart Mapper for Invoice
            if HAS_SMART_MAPPER and smart_mapper_service and isinstance(extracted_data, dict):
                template = smart_mapper_service.load_template(document_type)
                ocr_metadata = ocr_processor.get_last_ocr_metadata()
                ocr_meta_dict = ocr_metadata if isinstance(ocr_metadata, dict) else {}
                raw_response = ocr_meta_dict.get('raw_response')
                if template and raw_response:
                    logger.info("🤖 Applying Smart Mapper GPT-4o for Invoice")
                    mapped = smart_mapper_service.map_document(
                        doc_type=document_type,
                        document_json=raw_response,
                        template=template,
                        extracted_fields=ocr_meta_dict.get('extracted_fields'),
                        fallback_fields=extracted_data.get('structured_data'),
                    )
                    if mapped:
                        logger.info("✅ Smart Mapper Invoice successful!")
                        extracted_data.setdefault('structured_data', {})
                        extracted_data['structured_data']['smart_mapper'] = mapped
                        extracted_data['smart_mapped'] = mapped
                    else:
                        logger.warning("⚠️ Smart Mapper Invoice returned no data")
                else:
                    if not template:
                        logger.warning(f"⚠️ No template found for {document_type}")
                    if not raw_response:
                        logger.warning("⚠️ No raw OCR response available for Smart Mapper")
        else:
            logger.warning(f"⚠️ Unknown document type: {document_type}, defaulting to faktur_pajak")
            extracted_data = parser.parse_faktur_pajak(extracted_text, file_path=file_path)
        
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

        # Get raw OCR result for debugging/inspection
        ocr_metadata = ocr_processor.get_last_ocr_metadata()
        raw_ocr_json = None
        if ocr_metadata and 'raw_response' in ocr_metadata:
            raw_response = ocr_metadata['raw_response']
            # Convert Document AI proto to dict for JSON serialization
            try:
                from google.protobuf.json_format import MessageToDict
                if hasattr(raw_response, 'DESCRIPTOR'):  # It's a protobuf message
                    raw_ocr_json = MessageToDict(raw_response, preserving_proto_field_name=True)
                elif isinstance(raw_response, dict):
                    raw_ocr_json = raw_response
            except Exception as e:
                logger.warning(f"⚠️ Could not convert raw OCR to JSON: {e}")

        result = {
            "extracted_data": extracted_data,
            "confidence": confidence,
            "raw_text": extracted_text,
            "raw_ocr_result": raw_ocr_json,  # Add raw OCR JSON
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

async def _process_document_chunked(file_path: str, document_type: str, start_time: float) -> Dict[str, Any]:
    """
    Process large multi-page PDF by splitting into chunks

    Args:
        file_path: Path to PDF file
        document_type: Document type
        start_time: Processing start time

    Returns:
        Merged extraction result from all chunks
    """
    try:
        page_count = pdf_chunker.get_page_count(file_path)
        logger.info(f"📚 Processing {page_count}-page rekening koran in chunks")

        # Split PDF into chunks
        chunks = pdf_chunker.split_pdf_to_chunks(file_path)

        if not chunks:
            raise Exception("Failed to split PDF into chunks")

        logger.info(f"✅ Split into {len(chunks)} chunks")

        # Process each chunk
        chunk_results = []

        for i, chunk_info in enumerate(chunks, 1):
            logger.info(f"🔄 Processing chunk {i}/{len(chunks)}: pages {chunk_info['start_page']}-{chunk_info['end_page']}")

            try:
                # Extract text from chunk WITH full OCR result
                chunk_text = await ocr_processor.extract_text(chunk_info['path'])

                if not chunk_text:
                    logger.warning(f"⚠️ Chunk {i} extraction failed - skipping")
                    continue

                # Get OCR metadata and result for hybrid processor
                chunk_ocr_metadata = ocr_processor.get_last_ocr_metadata()

                # ✅ CRITICAL FIX: Build proper ocr_result structure (same as normal processing path)
                # The hybrid processor expects: {'text': ..., 'tables': ..., 'raw_response': ...}
                # Extract tables from raw_response (Google Document AI format)
                tables = []
                raw_response = chunk_ocr_metadata.get('raw_response') if chunk_ocr_metadata else None

                logger.info(f"   🔍 DEBUG CHUNKED: chunk_ocr_metadata exists = {chunk_ocr_metadata is not None}")
                logger.info(f"   🔍 DEBUG CHUNKED: raw_response type = {type(raw_response)}")

                if raw_response and isinstance(raw_response, dict):
                    # Tables might be in raw_response.pages[].tables
                    pages = raw_response.get('pages', [])
                    logger.info(f"   🔍 DEBUG CHUNKED: Found {len(pages)} pages in raw_response")
                    for idx, page in enumerate(pages, 1):
                        if isinstance(page, dict) and 'tables' in page:
                            page_tables = page.get('tables', [])
                            logger.info(f"   🔍 DEBUG CHUNKED: Page {idx} has {len(page_tables)} tables")
                            if isinstance(page_tables, list):
                                tables.extend(page_tables)
                        else:
                            page_keys = list(page.keys())[:5] if isinstance(page, dict) else 'not a dict'
                            logger.info(f"   🔍 DEBUG CHUNKED: Page {idx} - no 'tables' key (keys: {page_keys})")

                    logger.info(f"   📊 CHUNKED: Extracted {len(tables)} tables from Google Document AI response")
                else:
                    logger.warning(f"   ⚠️ CHUNKED: raw_response is None or not a dict")

                chunk_ocr_result = {
                    'text': chunk_text,
                    'tables': tables,  # ← Now has actual tables!
                    'raw_response': raw_response
                }

                # Calculate page offset for this chunk (page 1 = offset 0, page 4 = offset 3)
                page_offset = chunk_info['start_page'] - 1
                if page_offset > 0:
                    logger.info(f"   📄 Applying page offset: {page_offset} (chunk starts at page {chunk_info['start_page']})")

                # Parse chunk (rekening_koran specific) WITH OCR result for Hybrid Processor
                chunk_extracted_data = await parser.parse_rekening_koran(
                    chunk_text,
                    ocr_result=chunk_ocr_result,
                    ocr_metadata=chunk_ocr_metadata,
                    page_offset=page_offset
                )

                # ✨ NEW STRATEGY: ALWAYS refine with GPT-4o (Option A)
                # Bank adapter runs first (fast, free), then GPT refines (cheap, accurate)
                if HAS_SMART_MAPPER and smart_mapper_service:
                    ocr_metadata = ocr_processor.get_last_ocr_metadata()
                    ocr_meta_dict = ocr_metadata if isinstance(ocr_metadata, dict) else {}
                    raw_response = ocr_meta_dict.get('raw_response')

                    if raw_response:
                        logger.info(f"✨ Refining chunk {i} with GPT-4o (Always Refine Strategy)")

                        # Use lightweight refinement instead of full extraction
                        refined = smart_mapper_service.refine_adapter_result(
                            adapter_result=chunk_extracted_data,
                            ocr_json=raw_response,
                            doc_type=document_type
                        )

                        if refined:
                            # Replace with refined result
                            chunk_extracted_data = refined
                            logger.info(f"✨ Chunk {i} refined successfully")
                        else:
                            logger.warning(f"⚠️ Chunk {i} refinement failed - using adapter result")

                # ✅ FIX: Store raw_ocr_result for this chunk
                chunk_raw_ocr = chunk_ocr_metadata.get('raw_response') if chunk_ocr_metadata else None

                # Store chunk result
                chunk_result = {
                    'extracted_data': chunk_extracted_data,
                    'raw_text': chunk_text,
                    'extracted_text': chunk_text,
                    'chunk_number': i,
                    'pages': f"{chunk_info['start_page']}-{chunk_info['end_page']}",
                    'raw_ocr_result': chunk_raw_ocr  # Include raw OCR for split view
                }

                chunk_results.append(chunk_result)
                logger.info(f"✅ Chunk {i} processed successfully")

            except Exception as e:
                logger.error(f"❌ Error processing chunk {i}: {e}")
                # Continue with other chunks

        # Cleanup chunk files
        chunk_paths = [c['path'] for c in chunks]
        pdf_chunker.cleanup_chunks(chunk_paths)

        if not chunk_results:
            raise Exception("All chunks failed to process")

        # Merge results
        logger.info(f"🔗 Merging {len(chunk_results)} chunk results")
        merged_result = pdf_chunker.merge_extracted_data(chunk_results, document_type)

        # Calculate final confidence using raw_text (not extracted_data)
        merged_raw_text = merged_result.get('raw_text', '')
        if not merged_raw_text:
            # Fallback: concatenate raw_text from chunks if merge didn't preserve it
            merged_raw_text = '\n'.join(chunk.get('raw_text', '') for chunk in chunk_results)

        final_confidence = calculate_confidence(
            merged_raw_text,
            document_type
        )

        # Calculate processing time
        processing_time = asyncio.get_event_loop().time() - start_time

        # ✅ FIX: Merge raw_ocr_result from all chunks for split view
        # Use the first chunk's raw_ocr_result (it has all pages already from Google Document AI)
        merged_raw_ocr = None
        if chunk_results and chunk_results[0].get('raw_ocr_result'):
            merged_raw_ocr = chunk_results[0]['raw_ocr_result']
            logger.info(f"✅ Including raw_ocr_result from first chunk for split view")

        # Return final result - matching normal processing structure
        final_result = {
            'extracted_data': merged_result.get('extracted_data', {}),
            'confidence': final_confidence,
            'raw_text': merged_result.get('raw_text', ''),
            'raw_ocr_result': merged_raw_ocr,  # Add for split view display
            'processing_time': processing_time,
            # Additional metadata for chunked processing
            'ocr_engine_used': 'Google Document AI (Chunked)',
            'chunks_processed': len(chunk_results),
            'total_pages': page_count
        }

        logger.info(f"✅ Chunked processing complete: {len(chunk_results)} chunks, {page_count} pages, {processing_time:.2f}s")
        logger.info(f"✅ Merged extracted data keys: {list(final_result['extracted_data'].keys()) if isinstance(final_result['extracted_data'], dict) else 'N/A'}")

        return final_result

    except Exception as e:
        logger.error(f"❌ Chunked processing failed: {e}", exc_info=True)
        raise


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
