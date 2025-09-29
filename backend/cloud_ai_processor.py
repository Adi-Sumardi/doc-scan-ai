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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CloudOCRResult:
    """Cloud OCR result with metadata"""
    text: str
    confidence: float
    service_used: str
    processing_time: float
    extracted_fields: Dict[str, Any]
    bounding_boxes: List[Dict]
    document_type: str
    language_detected: str

class CloudAIProcessor:
    """Enterprise-grade Cloud AI Document Processing"""
    
    def __init__(self):
        """Initialize cloud AI services"""
        self.services = {}
        self._init_cloud_services()
        logger.info("☁️ Cloud AI Processor initialized")
    
    def _init_cloud_services(self):
        """Initialize cloud AI services"""
        try:
            # 1. Azure Document Intelligence
            try:
                from azure.cognitiveservices.vision.computervision import ComputerVisionClient
                from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
                from msrest.authentication import CognitiveServicesCredentials
                
                # Initialize with environment variables
                endpoint = os.getenv('AZURE_COGNITIVE_ENDPOINT')
                key = os.getenv('AZURE_COGNITIVE_KEY')
                
                if endpoint and key:
                    self.services['azure'] = ComputerVisionClient(endpoint, CognitiveServicesCredentials(key))
                    logger.info("✅ Azure Document Intelligence initialized")
                else:
                    logger.warning("⚠️ Azure credentials not found")
                    
            except ImportError:
                logger.warning("⚠️ Azure SDK not available")
            
            # 2. Google Document AI
            try:
                from google.cloud import documentai
                
                # Initialize with service account
                project_id = os.getenv('GOOGLE_CLOUD_PROJECT_ID')
                if project_id:
                    self.services['google'] = documentai.DocumentProcessorServiceClient()
                    logger.info("✅ Google Document AI initialized")
                else:
                    logger.warning("⚠️ Google Cloud credentials not found")
                    
            except ImportError:
                logger.warning("⚠️ Google Cloud SDK not available")
            
            # 3. AWS Textract
            try:
                import boto3
                
                # Initialize with AWS credentials
                access_key = os.getenv('AWS_ACCESS_KEY_ID')
                secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
                
                if access_key and secret_key:
                    self.services['aws'] = boto3.client(
                        'textract',
                        aws_access_key_id=access_key,
                        aws_secret_access_key=secret_key,
                        region_name=os.getenv('AWS_REGION', 'us-east-1')
                    )
                    logger.info("✅ AWS Textract initialized")
                else:
                    logger.warning("⚠️ AWS credentials not found")
                    
            except ImportError:
                logger.warning("⚠️ AWS SDK not available")
                
        except Exception as e:
            logger.error(f"❌ Cloud services initialization failed: {e}")
    
    async def process_with_azure(self, file_path: str) -> CloudOCRResult:
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
                    text=full_text,
                    confidence=avg_confidence * 100,
                    service_used="Azure Document Intelligence",
                    processing_time=processing_time,
                    extracted_fields=self._extract_tax_fields_azure(full_text),
                    bounding_boxes=bounding_boxes,
                    document_type="tax_document",
                    language_detected="id"
                )
                
        except Exception as e:
            logger.error(f"❌ Azure processing failed: {e}")
            return CloudOCRResult("", 0.0, "Azure (Failed)", 0.0, {}, [], "unknown", "unknown")
    
    async def process_with_google(self, file_path: str) -> CloudOCRResult:
        """Process document with Google Document AI"""
        try:
            if 'google' not in self.services:
                raise Exception("Google service not available")
            
            start_time = asyncio.get_event_loop().time()
            
            project_id = os.getenv('GOOGLE_CLOUD_PROJECT_ID')
            location = 'us'  # Format is 'us' or 'eu'
            processor_id = os.getenv('GOOGLE_PROCESSOR_ID', 'general')  # Replace with your processor ID
            
            # The full resource name of the processor
            name = f"projects/{project_id}/locations/{location}/processors/{processor_id}"
            
            # Read document
            with open(file_path, "rb") as document:
                document_content = document.read()
                
            # Configure the process request
            request = {
                "name": name,
                "raw_document": {
                    "content": document_content,
                    "mime_type": "application/pdf" if file_path.endswith('.pdf') else "image/jpeg"
                }
            }
            
            # Process document
            result = self.services['google'].process_document(request=request)
            document = result.document
            
            # Extract text and confidence
            full_text = document.text
            avg_confidence = 0.9  # Google typically has high confidence
            
            # Extract fields
            extracted_fields = {}
            for entity in document.entities:
                extracted_fields[entity.type_] = entity.text_anchor.content
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            return CloudOCRResult(
                text=full_text,
                confidence=avg_confidence * 100,
                service_used="Google Document AI",
                processing_time=processing_time,
                extracted_fields=extracted_fields,
                bounding_boxes=[],
                document_type="tax_document",
                language_detected="id"
            )
            
        except Exception as e:
            logger.error(f"❌ Google processing failed: {e}")
            return CloudOCRResult("", 0.0, "Google (Failed)", 0.0, {}, [], "unknown", "unknown")
    
    async def process_with_aws(self, file_path: str) -> CloudOCRResult:
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
            
            # Extract key-value pairs
            extracted_fields = {}
            for block in response['Blocks']:
                if block['BlockType'] == 'KEY_VALUE_SET' and 'KEY' in block['EntityTypes']:
                    key_text = self._get_text_from_relationships(block, response['Blocks'])
                    value_text = self._get_value_from_key(block, response['Blocks'])
                    if key_text and value_text:
                        extracted_fields[key_text] = value_text
            
            return CloudOCRResult(
                text=full_text,
                confidence=avg_confidence * 100,
                service_used="AWS Textract",
                processing_time=processing_time,
                extracted_fields=extracted_fields,
                bounding_boxes=bounding_boxes,
                document_type="tax_document",
                language_detected="id"
            )
            
        except Exception as e:
            logger.error(f"❌ AWS processing failed: {e}")
            return CloudOCRResult("", 0.0, "AWS (Failed)", 0.0, {}, [], "unknown", "unknown")
    
    async def process_ensemble_cloud(self, file_path: str) -> CloudOCRResult:
        """Ensemble processing with multiple cloud services"""
        try:
            # Run all available services concurrently
            tasks = []
            
            if 'azure' in self.services:
                tasks.append(self.process_with_azure(file_path))
            if 'google' in self.services:
                tasks.append(self.process_with_google(file_path))
            if 'aws' in self.services:
                tasks.append(self.process_with_aws(file_path))
            
            if not tasks:
                logger.error("❌ No cloud services available")
                return CloudOCRResult("", 0.0, "None", 0.0, {}, [], "unknown", "unknown")
            
            # Wait for all results
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter successful results
            successful_results = [r for r in results if isinstance(r, CloudOCRResult) and r.confidence > 0]
            
            if not successful_results:
                logger.error("❌ All cloud services failed")
                return CloudOCRResult("", 0.0, "All Failed", 0.0, {}, [], "unknown", "unknown")
            
            # Select best result based on confidence
            best_result = max(successful_results, key=lambda x: x.confidence)
            
            logger.info(f"✅ Best cloud result: {best_result.service_used} ({best_result.confidence:.1f}%)")
            return best_result
            
        except Exception as e:
            logger.error(f"❌ Ensemble cloud processing failed: {e}")
            return CloudOCRResult("", 0.0, "Ensemble Failed", 0.0, {}, [], "unknown", "unknown")
    
    def _extract_tax_fields_azure(self, text: str) -> Dict[str, Any]:
        """Extract Indonesian tax document fields from Azure result"""
        import re
        
        fields = {}
        
        # Nomor Faktur Pajak
        nomor_pattern = r'(?:No\.|Nomor)\s*(?:Faktur|Pajak)?\s*:?\s*(\d{3}\.\d{3}-\d+)'
        match = re.search(nomor_pattern, text, re.IGNORECASE)
        if match:
            fields['nomor_faktur'] = match.group(1)
        
        # NPWP
        npwp_pattern = r'NPWP\s*:?\s*(\d{2}\.\d{3}\.\d{3}\.\d{1}-\d{3}\.\d{3})'
        match = re.search(npwp_pattern, text)
        if match:
            fields['npwp'] = match.group(1)
        
        # DPP (Dasar Pengenaan Pajak)
        dpp_pattern = r'DPP\s*:?\s*(?:Rp\.?\s*)?([0-9.,]+)'
        match = re.search(dpp_pattern, text, re.IGNORECASE)
        if match:
            fields['dpp'] = match.group(1)
        
        # PPN
        ppn_pattern = r'PPN\s*:?\s*(?:Rp\.?\s*)?([0-9.,]+)'
        match = re.search(ppn_pattern, text, re.IGNORECASE)
        if match:
            fields['ppn'] = match.group(1)
        
        return fields
    
    def _get_text_from_relationships(self, block, blocks):
        """Helper function for AWS Textract"""
        text = ""
        if 'Relationships' in block:
            for relationship in block['Relationships']:
                if relationship['Type'] == 'CHILD':
                    for child_id in relationship['Ids']:
                        child_block = next((b for b in blocks if b['Id'] == child_id), None)
                        if child_block and child_block['BlockType'] == 'WORD':
                            text += child_block['Text'] + " "
        return text.strip()
    
    def _get_value_from_key(self, key_block, blocks):
        """Helper function for AWS Textract"""
        if 'Relationships' in key_block:
            for relationship in key_block['Relationships']:
                if relationship['Type'] == 'VALUE':
                    for value_id in relationship['Ids']:
                        value_block = next((b for b in blocks if b['Id'] == value_id), None)
                        if value_block:
                            return self._get_text_from_relationships(value_block, blocks)
        return ""

# Example usage
async def main():
    processor = CloudAIProcessor()
    result = await processor.process_ensemble_cloud("sample.pdf")
    print(f"✅ Cloud processing: {result.service_used}")
    print(f"Confidence: {result.confidence:.1f}%")
    print(f"Extracted fields: {len(result.extracted_fields)}")

if __name__ == "__main__":
    asyncio.run(main())