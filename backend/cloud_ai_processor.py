#!/usr/bin/env python3
"""
CLOUD AI INTEGRATION
Azure Document Intelligence + Google Document AI + AWS Textract
Ultra-high accuracy dengan enterprise-grade AI services
"""

import os
import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json
import mimetypes
import gc  # ✅ NEW: For memory management

from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure environment variables from .env are available when this module is imported
load_dotenv()

@dataclass
class CloudOCRResult:
    """Cloud OCR result with metadata"""
    raw_text: str
    confidence: float
    service_used: str
    processing_time: float
    extracted_fields: Dict[str, Any]
    raw_response: Dict[str, Any] # Store the full raw response for debugging
    document_type: str
    language_detected: str

class CloudAIProcessor:
    """Enterprise-grade Cloud AI Document Processing"""
    
    def __init__(self):
        """Initialize cloud AI services"""
        self.services: Dict[str, Any] = {}
        self._init_cloud_services()
        logger.info("☁️ Cloud AI Processor initialized")
    
    def _init_cloud_services(self):
        """Initialize cloud AI services - Google Document AI only"""
        try:
            # Google Document AI - Primary OCR Engine
            try:
                from google.cloud import documentai_v1 as documentai
                from google.oauth2 import service_account
                
                # Load credentials explicitly
                creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
                project_id = os.getenv('GOOGLE_CLOUD_PROJECT_ID')
                location = os.getenv('GOOGLE_PROCESSOR_LOCATION')
                processor_id = os.getenv('GOOGLE_PROCESSOR_ID')

                if not all([creds_path, project_id, location, processor_id]):
                    try:
                        from config import settings as _settings
                    except ModuleNotFoundError:  # pragma: no cover
                        from .config import settings as _settings
                    creds_path = creds_path or _settings.google_application_credentials
                    project_id = project_id or _settings.google_cloud_project_id
                    location = location or _settings.google_processor_location
                    processor_id = processor_id or _settings.google_processor_id
                
                if creds_path and project_id and location and processor_id:
                    # Load credentials from file
                    credentials = service_account.Credentials.from_service_account_file(creds_path)
                    
                    # The client options are important for specifying the regional endpoint
                    client_options = {"api_endpoint": f"{location}-documentai.googleapis.com"}
                    self.services['google'] = {
                        'credentials': credentials,
                        'client_options': client_options,
                        'project_id': project_id,
                        'location': location,
                        'processor_id': processor_id
                    }
                    logger.info("✅ Google Document AI initialized with explicit credentials")
                else:
                    logger.warning("⚠️ Google Cloud credentials not found")
                    
            except ImportError:
                logger.warning("⚠️ Google Cloud SDK not available")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Google Document AI: {e}")
                
        except Exception as e:
            logger.error(f"❌ Cloud services initialization failed: {e}")
    
    # Azure and AWS methods removed - Google Document AI only
    
    async def _REMOVED_process_with_azure(self, file_path: str) -> CloudOCRResult:
        """Process document with Azure Document Intelligence"""
        try:
            if 'azure' not in self.services:
                raise Exception("Azure service not available")
            
            start_time = asyncio.get_event_loop().time()
            
            # Read document
            with open(file_path, 'rb') as document:
                # Analyze document
                read_response = self.services['azure'].read_in_stream(document, raw=True)
                
                # Get operation ID
                operation_id = read_response.headers["Operation-Location"].split("/")[-1]
                
                # Wait for result
                while True:
                    read_result = self.services['azure'].get_read_result(operation_id)
                    if read_result.status not in ['notStarted', 'running']:
                        break
                    await asyncio.sleep(1)
                
                # Extract text
                text_results = []
                confidence_scores = []
                bounding_boxes = []
                
                if read_result.status == 'succeeded':
                    for text_result in read_result.analyze_result.read_results:
                        for line in text_result.lines:
                            text_results.append(line.text)
                            confidence_scores.append(line.appearance.style.confidence if line.appearance else 0.8)
                            bounding_boxes.append({
                                'text': line.text,
                                'bounding_box': line.bounding_box,
                                'confidence': line.appearance.style.confidence if line.appearance else 0.8
                            })
                
                full_text = ' '.join(text_results)
                avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
                processing_time = asyncio.get_event_loop().time() - start_time
                
                return CloudOCRResult(
                    raw_text=full_text,
                    confidence=avg_confidence * 100,
                    service_used="Azure Document Intelligence",
                    processing_time=processing_time,
                    extracted_fields=self._extract_tax_fields_azure(full_text),
                    raw_response={"bounding_boxes": bounding_boxes, "read_result": "success"},
                    document_type="tax_document",
                    language_detected="id"
                )
                
        except Exception as e:
            logger.error(f"❌ Azure processing failed: {e}")
            return CloudOCRResult(
                raw_text="",
                confidence=0.0,
                service_used="Azure (Failed)",
                processing_time=0.0,
                extracted_fields={},
                raw_response={"error": str(e)},
                document_type="unknown",
                language_detected="unknown"
            )
    
    async def process_with_google(self, file_path: str) -> CloudOCRResult:
        """Process document with Google Document AI"""
        try:
            from google.cloud import documentai_v1 as documentai

            if 'google' not in self.services:
                raise Exception("Google service not available")
            
            start_time = asyncio.get_event_loop().time()
            
            service_info = self.services['google']
            project_id = service_info.get('project_id')
            location = service_info.get('location', 'us')
            processor_id = service_info.get('processor_id')
            
            # Validate required configuration
            if not project_id:
                raise Exception("GOOGLE_CLOUD_PROJECT_ID not configured")
            if not processor_id:
                raise Exception("GOOGLE_PROCESSOR_ID not configured")

            # The full resource name of the processor
            name = f"projects/{project_id}/locations/{location}/processors/{processor_id}"
            logger.info(f"📄 Processing with Google Document AI: {name}")
            
            # ✅ CRITICAL FIX: Check file size before reading to prevent OOM
            file_size_bytes = os.path.getsize(file_path)
            file_size_mb = file_size_bytes / (1024 * 1024)
            logger.info(f"📊 File size: {file_size_mb:.1f} MB")
            
            # Google Document AI limit: 20MB for synchronous, 1GB for async
            # We use 100MB as safety limit
            if file_size_mb > 100:
                logger.error(f"❌ File too large for processing: {file_size_mb:.1f}MB (>100MB limit)")
                logger.error(f"❌ This file MUST be chunked before processing!")
                logger.error(f"❌ Please ensure chunking is enabled and threshold is low enough")
                raise Exception(f"File too large: {file_size_mb:.1f}MB. Chunking required.")
            
            # Read document
            logger.info(f"📄 Reading file into memory: {file_size_mb:.1f}MB")
            with open(file_path, "rb") as document:
                document_content = document.read()
            logger.info(f"✅ File read complete: {len(document_content)} bytes")
                
            # Infer the MIME type
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = 'application/pdf' if file_path.lower().endswith('.pdf') else 'image/jpeg'

            # ✅ OPTIMIZED: Enhanced OCR config for better table detection
            # Based on Google Document AI best practices for table extraction
            process_options = documentai.ProcessOptions(
                ocr_config=documentai.OcrConfig(
                    enable_native_pdf_parsing=True,  # Better PDF text extraction
                    enable_image_quality_scores=True,  # Get quality metrics
                    enable_symbol=True,  # Enable symbol detection (helps with table borders)
                    # Character box detection enabled by default - helps identify table structure
                    # disable_character_boxes_detection=False (default)
                )
            )

            # Configure the process request with OCR options
            request = {
                "name": name,
                "raw_document": {
                    "content": document_content,
                    "mime_type": mime_type
                },
                "process_options": process_options
            }
            
            # Process document using a client bound to the current event loop
            client = documentai.DocumentProcessorServiceAsyncClient(
                credentials=service_info['credentials'],
                client_options=service_info['client_options']
            )
            try:
                result = await client.process_document(request=request)
            finally:
                transport = getattr(client, 'transport', None)
                if transport and hasattr(transport, 'close'):
                    maybe_coro = transport.close()
                    if asyncio.iscoroutine(maybe_coro):
                        await maybe_coro
            document = result.document
            
            # Extract text and confidence
            raw_text = document.text
            logger.info(f"📊 Google Document AI extracted {len(raw_text)} characters")

            # ✅ Log image quality scores if available
            for i, page in enumerate(document.pages, 1):
                if hasattr(page, 'image_quality_scores') and page.image_quality_scores:
                    quality = page.image_quality_scores.quality_score
                    logger.info(f"   📷 Page {i} quality score: {quality:.3f}")
                    if hasattr(page.image_quality_scores, 'detected_defects'):
                        for defect in page.image_quality_scores.detected_defects:
                            if defect.confidence > 0.5:
                                logger.warning(f"   ⚠️ Page {i} defect: {defect.type_} (confidence: {defect.confidence:.2f})")
            
            # Calculate average confidence from pages
            # The 'Page' object does not have a confidence attribute.
            # We will calculate the average confidence from all the tokens in the document.
            all_token_confidences = []
            for page in document.pages:
                for token in page.tokens:
                    if token.layout and token.layout.confidence > 0:
                        all_token_confidences.append(token.layout.confidence)
            avg_confidence = (sum(all_token_confidences) / len(all_token_confidences)) if all_token_confidences else 0.9 # Default high confidence
            
            # Extract fields
            extracted_fields = {}
            for entity in document.entities:
                # Clean up key
                key = entity.type_.replace('/', '_')
                value = entity.mention_text
                confidence = entity.confidence
                
                extracted_fields[key] = {
                    "value": value,
                    "confidence": round(confidence, 4)
                }
            
            processing_time = asyncio.get_event_loop().time() - start_time

            # ✅ FIX: Convert protobuf to dict AND add the full text field
            # Document.to_dict() doesn't include the top-level 'text' field, so we add it manually
            raw_response_dict = documentai.Document.to_dict(document) # type: ignore
            raw_response_dict['text'] = raw_text  # Add full document text to the dict

            # 🔍 DEBUG: Log table detection
            total_tables = 0
            if 'pages' in raw_response_dict:
                for i, page in enumerate(raw_response_dict['pages'], 1):
                    if isinstance(page, dict) and 'tables' in page:
                        page_table_count = len(page['tables'])
                        total_tables += page_table_count
                        if page_table_count > 0:
                            logger.info(f"   📊 Page {i}: detected {page_table_count} tables")

            if total_tables == 0:
                logger.warning(f"   ⚠️ Google Document AI detected 0 tables in document")
                logger.info(f"   🔧 Will fallback to line-based synthetic table construction")
                # ✅ Create synthetic tables from lines for better Claude processing
                self._create_synthetic_tables_from_lines(raw_response_dict)

            return CloudOCRResult(
                raw_text=raw_text,
                confidence=avg_confidence * 100,
                service_used="Google Document AI",
                processing_time=processing_time,
                extracted_fields=extracted_fields,
                raw_response=raw_response_dict,  # Now includes 'text' field
                document_type=result.document.entities[0].type_ if result.document.entities else "unknown",
                language_detected=document.pages[0].detected_languages[0].language_code if document.pages and document.pages[0].detected_languages else "id"
            )
            
        except Exception as e:
            logger.error(f"❌ Google processing failed: {e}")
            raise Exception(f"Google Document AI processing failed: {e}")
    
    async def _REMOVED_process_with_aws(self, file_path: str) -> CloudOCRResult:
        """Process document with AWS Textract"""
        try:
            if 'aws' not in self.services:
                raise Exception("AWS service not available")
            
            start_time = asyncio.get_event_loop().time()
            
            # Read document
            with open(file_path, 'rb') as document:
                document_bytes = document.read()
            
            # Analyze document
            response = self.services['aws'].analyze_document(
                Document={'Bytes': document_bytes},
                FeatureTypes=['TABLES', 'FORMS']
            )
            
            # Extract text
            text_blocks = []
            confidence_scores = []
            bounding_boxes = []
            
            for block in response['Blocks']:
                if block['BlockType'] == 'LINE':
                    text_blocks.append(block['Text'])
                    confidence_scores.append(block['Confidence'] / 100.0)
                    bounding_boxes.append({
                        'text': block['Text'],
                        'confidence': block['Confidence'],
                        'geometry': block['Geometry']
                    })
            
            full_text = ' '.join(text_blocks)
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
            processing_time = asyncio.get_event_loop().time() - start_time
            
            # Create block index for O(1) lookup instead of O(n) for each block
            block_map = {block['Id']: block for block in response['Blocks']}
            
            # Extract key-value pairs with optimized lookup
            extracted_fields = {}
            for block in response['Blocks']:
                if block['BlockType'] == 'KEY_VALUE_SET' and 'KEY' in block['EntityTypes']:
                    key_text = self._get_text_from_relationships(block, block_map)
                    value_text = self._get_value_from_key(block, block_map)
                    if key_text and value_text:
                        extracted_fields[key_text] = value_text
            
            return CloudOCRResult(
                raw_text=full_text,
                confidence=avg_confidence * 100,
                service_used="AWS Textract",
                processing_time=processing_time,
                extracted_fields=extracted_fields,
                raw_response=response,
                document_type="tax_document",
                language_detected="id"
            )
            
        except Exception as e:
            logger.error(f"❌ AWS processing failed: {e}")
            return CloudOCRResult(
                raw_text="",
                confidence=0.0,
                service_used="AWS (Failed)",
                processing_time=0.0,
                extracted_fields={},
                raw_response={"error": str(e)},
                document_type="unknown",
                language_detected="unknown"
            )

    def _create_synthetic_tables_from_lines(self, raw_response_dict: dict) -> None:
        """
        ✅ SYNTHETIC TABLE CONSTRUCTION
        When Google Document AI fails to detect tables (0 tables),
        this method creates pseudo-table structures from lines/paragraphs.
        This helps Claude process structured data without hitting token limits.

        Strategy:
        1. Group consecutive lines on same Y-coordinate (horizontal alignment)
        2. Detect repeating patterns (likely transaction rows)
        3. Create synthetic table structure
        """
        try:
            if 'pages' not in raw_response_dict:
                return

            full_text = raw_response_dict.get('text', '')
            if not full_text:
                return

            total_synth_tables = 0

            for page_idx, page in enumerate(raw_response_dict['pages']):
                if not isinstance(page, dict):
                    continue

                # Skip if page already has tables
                if page.get('tables') and len(page.get('tables', [])) > 0:
                    continue

                # Get lines from page
                lines = page.get('lines', [])
                if not lines or len(lines) < 3:  # Need at least 3 lines to form a table
                    continue

                # Group lines into potential table rows
                # Lines are already in reading order from Document AI
                synthetic_rows = []
                current_row_cells = []
                prev_y_avg = None
                y_threshold = 10  # pixels - lines within this threshold are considered same row

                for line in lines:
                    if not isinstance(line, dict):
                        continue

                    layout = line.get('layout', {})
                    if not layout:
                        continue

                    # Get line text
                    text_anchor = layout.get('text_anchor', {})
                    text_segments = text_anchor.get('text_segments', [])
                    if not text_segments:
                        continue

                    segment = text_segments[0]
                    start_idx = int(segment.get('start_index', 0))
                    end_idx = int(segment.get('end_index', 0))
                    line_text = full_text[start_idx:end_idx].strip()

                    if not line_text:
                        continue

                    # Get Y coordinate (vertical position)
                    bounding_poly = layout.get('bounding_poly', {})
                    vertices = bounding_poly.get('vertices', [])
                    if len(vertices) < 2:
                        continue

                    # Average Y coordinate of top edge
                    y_avg = (vertices[0].get('y', 0) + vertices[1].get('y', 0)) / 2.0

                    # Check if this line is on same row as previous (similar Y coordinate)
                    if prev_y_avg is not None and abs(y_avg - prev_y_avg) < y_threshold:
                        # Same row - add as cell
                        current_row_cells.append(line_text)
                    else:
                        # New row
                        if current_row_cells:
                            synthetic_rows.append(current_row_cells)
                        current_row_cells = [line_text]
                        prev_y_avg = y_avg

                # Add last row
                if current_row_cells:
                    synthetic_rows.append(current_row_cells)

                # Convert rows to table structure (if we have enough rows)
                if len(synthetic_rows) >= 3:
                    # Assume first row might be header
                    header_rows = [{'cells': [{'layout': {'text_anchor': {'content': cell}}} for cell in synthetic_rows[0]]}]
                    body_rows = [{'cells': [{'layout': {'text_anchor': {'content': cell}}} for cell in row]} for row in synthetic_rows[1:]]

                    synthetic_table = {
                        'layout': {},
                        'header_rows': header_rows,
                        'body_rows': body_rows
                    }

                    # Add synthetic table to page
                    if 'tables' not in page:
                        page['tables'] = []
                    page['tables'].append(synthetic_table)
                    total_synth_tables += 1

                    logger.info(f"   ✅ Page {page_idx + 1}: Created synthetic table with {len(synthetic_rows)} rows")

            if total_synth_tables > 0:
                logger.info(f"   🎯 Created {total_synth_tables} synthetic tables from line layout")

        except Exception as e:
            logger.warning(f"   ⚠️ Synthetic table creation failed: {e}")
            # Don't raise - this is a fallback enhancement, not critical


# Example usage
async def main():
    processor = CloudAIProcessor()
    # Now using only Google Document AI
    result = await processor.process_with_google("sample.pdf")
    print(f"✅ Cloud processing: {result.service_used}")
    print(f"Confidence: {result.confidence:.1f}%")
    print(f"Extracted fields: {len(result.extracted_fields)}")

if __name__ == "__main__":
    asyncio.run(main())