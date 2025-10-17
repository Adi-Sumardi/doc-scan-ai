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

        # SPECIAL HANDLING: Check if PDF needs chunking (for rekening_koran with 10+ pages)
        file_ext = Path(file_path).suffix.lower()
        is_pdf = file_ext == '.pdf'
        is_rekening_koran = document_type in ['rekening_koran', 'rekening koran']

        if is_pdf and is_rekening_koran and pdf_chunker.needs_chunking(file_path, threshold=10):
            logger.info("📚 Multi-page rekening koran detected - using chunked processing")
            return await _process_document_chunked(file_path, document_type, start_time)

        # STEP 1: Extract text using OCR (normal flow for single documents or small PDFs)
        extracted_text = await ocr_processor.extract_text(file_path)
        
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
            # Get OCR metadata for enhanced processing
            ocr_metadata = ocr_processor.get_last_ocr_metadata()

            # Build OCR result structure for bank adapters
            ocr_result = {
                'text': extracted_text,
                'tables': ocr_metadata.get('tables', []) if ocr_metadata else [],
                'raw_response': ocr_metadata.get('raw_response') if ocr_metadata else None
            }

            # Use Enhanced Hybrid Processor (Bank Adapters + Smart Mapper)
            logger.info("🏦 Processing Rekening Koran with Enhanced Hybrid Processor")
            extracted_data = await parser.parse_rekening_koran(
                extracted_text,
                ocr_result=ocr_result,
                ocr_metadata=ocr_metadata,
                page_offset=0  # No offset for non-chunked files
            )

            # If enhanced processor returned structured data, we're done!
            if extracted_data and extracted_data.get('transactions'):
                logger.info(f"✅ Enhanced processor returned {len(extracted_data.get('transactions', []))} transactions")
                # Merge any Cloud AI structured fields if available
                if ocr_metadata:
                    cloud_fields = ocr_metadata.get('extracted_fields', {})
                    if cloud_fields:
                        logger.info("✅ Merging structured data from Google Document AI for Rekening Koran")
                        if 'extracted_content' not in extracted_data:
                            extracted_data['extracted_content'] = {}
                        extracted_data['extracted_content']['structured_fields'] = cloud_fields

            # Fallback: If enhanced processor failed, try Smart Mapper only
            elif HAS_SMART_MAPPER and smart_mapper_service and isinstance(extracted_data, dict):
                logger.warning("⚠️ Enhanced processor failed, trying Smart Mapper fallback...")
                logger.info("✅ Smart Mapper conditions met, loading template...")
                template = smart_mapper_service.load_template(document_type)
                ocr_meta_dict = ocr_metadata if isinstance(ocr_metadata, dict) else {}
                raw_response = ocr_meta_dict.get('raw_response')
                logger.info(f"🔍 DEBUG: template={template is not None}, raw_response={raw_response is not None}")
                if template and raw_response:
                    logger.info("🤖 Applying Smart Mapper GPT-4o for Rekening Koran")
                    mapped = smart_mapper_service.map_document(
                        doc_type=document_type,
                        document_json=raw_response,
                        template=template,
                        extracted_fields=ocr_meta_dict.get('extracted_fields'),
                        fallback_fields=extracted_data.get('structured_data'),
                    )
                    if mapped:
                        logger.info("✅ Smart Mapper Rekening Koran successful!")
                        extracted_data.setdefault('structured_data', {})
                        extracted_data['structured_data']['smart_mapper'] = mapped
                        extracted_data['smart_mapped'] = mapped
                    else:
                        logger.warning("⚠️ Smart Mapper Rekening Koran returned no data")
                else:
                    if not template:
                        logger.warning(f"⚠️ No template found for {document_type}")
                    if not raw_response:
                        logger.warning("⚠️ No raw OCR response available for Smart Mapper")
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
                # NOT just the raw_response alone!
                chunk_ocr_result = {
                    'text': chunk_text,
                    'tables': chunk_ocr_metadata.get('tables', []) if chunk_ocr_metadata else [],
                    'raw_response': chunk_ocr_metadata.get('raw_response') if chunk_ocr_metadata else None
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

                # Apply Smart Mapper if available
                if HAS_SMART_MAPPER and smart_mapper_service:
                    template = smart_mapper_service.load_template(document_type)
                    ocr_metadata = ocr_processor.get_last_ocr_metadata()
                    ocr_meta_dict = ocr_metadata if isinstance(ocr_metadata, dict) else {}
                    raw_response = ocr_meta_dict.get('raw_response')

                    if template and raw_response:
                        logger.info(f"🤖 Applying Smart Mapper to chunk {i}")
                        mapped = smart_mapper_service.map_document(
                            doc_type=document_type,
                            document_json=raw_response,
                            template=template,
                            extracted_fields=ocr_meta_dict.get('extracted_fields'),
                            fallback_fields=chunk_extracted_data.get('structured_data'),
                        )
                        if mapped:
                            chunk_extracted_data.setdefault('structured_data', {})
                            chunk_extracted_data['structured_data']['smart_mapper'] = mapped
                            chunk_extracted_data['smart_mapped'] = mapped

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
