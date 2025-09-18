#!/usr/bin/env python3
"""
PRODUCTION-OPTIMIZED SUPER MAXIMUM OCR SYSTEM
Enhanced version for production deployment with improved error handling,
logging, memory optimization, and monitoring capabilities.
"""

import os
import gc
import logging
import time
from typing import Dict, List, Optional, Tuple, Any
from contextlib import contextmanager
import threading
from concurrent.futures import ThreadPoolExecutor
import traceback

# Import super maximum OCR system
from super_maximum_ocr import (
    SuperMaximumOCRProcessor, 
    OCRResult, 
    DocumentQualityMetrics
)

# Setup production logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ocr_production.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ProductionOCRProcessor:
    """Production-optimized OCR processor with enhanced reliability"""
    
    def __init__(self, max_workers: int = 2, memory_limit_mb: int = 1024):
        self.max_workers = max_workers
        self.memory_limit_mb = memory_limit_mb
        self.processing_stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'avg_processing_time': 0.0,
            'total_processing_time': 0.0
        }
        self.thread_lock = threading.Lock()
        
        # Initialize core OCR processor
        try:
            self.ocr_processor = SuperMaximumOCRProcessor()
            logger.info("✅ Production OCR Processor initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize OCR processor: {e}")
            raise
    
    @contextmanager
    def memory_monitor(self):
        """Memory monitoring context manager"""
        import psutil
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        try:
            yield
        finally:
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_used = current_memory - initial_memory
            
            if memory_used > self.memory_limit_mb * 0.8:  # 80% threshold
                logger.warning(f"High memory usage detected: {memory_used:.1f}MB")
                gc.collect()  # Force garbage collection
            
            logger.debug(f"Memory usage: {current_memory:.1f}MB (+{memory_used:.1f}MB)")
    
    def process_document_safe(self, file_path: str) -> Dict[str, Any]:
        """Safe document processing with comprehensive error handling"""
        start_time = time.time()
        result_data = {
            'success': False,
            'file_path': file_path,
            'filename': os.path.basename(file_path),
            'processing_time': 0.0,
            'error': None,
            'ocr_result': None,
            'extracted_data': None
        }
        
        try:
            with self.memory_monitor():
                # Validate file
                if not self._validate_file(file_path):
                    raise ValueError(f"Invalid file: {file_path}")
                
                # Process with OCR
                logger.info(f"Processing: {os.path.basename(file_path)}")
                ocr_result = self.ocr_processor.process_pdf_super_advanced(file_path)
                
                if not ocr_result or len(ocr_result.text.strip()) < 10:
                    raise ValueError("OCR extraction failed or insufficient text")
                
                # Extract structured data
                extracted_data = self._extract_structured_data(ocr_result)
                
                # Update result
                result_data.update({
                    'success': True,
                    'ocr_result': ocr_result,
                    'extracted_data': extracted_data,
                    'text_length': len(ocr_result.text),
                    'confidence': ocr_result.confidence,
                    'engine_used': ocr_result.engine_used,
                    'patterns_found': len(ocr_result.detected_patterns)
                })
                
                logger.info(f"✅ Successfully processed: {result_data['filename']} "
                           f"({result_data['text_length']} chars, "
                           f"{result_data['confidence']:.1f}% confidence)")
                
        except Exception as e:
            error_msg = f"Processing failed for {os.path.basename(file_path)}: {str(e)}"
            logger.error(error_msg)
            logger.debug(f"Full traceback: {traceback.format_exc()}")
            result_data['error'] = error_msg
            
        finally:
            processing_time = time.time() - start_time
            result_data['processing_time'] = processing_time
            
            # Update statistics
            with self.thread_lock:
                self.processing_stats['total_processed'] += 1
                self.processing_stats['total_processing_time'] += processing_time
                
                if result_data['success']:
                    self.processing_stats['successful'] += 1
                else:
                    self.processing_stats['failed'] += 1
                
                # Update average
                self.processing_stats['avg_processing_time'] = (
                    self.processing_stats['total_processing_time'] / 
                    self.processing_stats['total_processed']
                )
        
        return result_data
    
    def _validate_file(self, file_path: str) -> bool:
        """Validate file before processing"""
        try:
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return False
            
            if not file_path.lower().endswith('.pdf'):
                logger.error(f"Unsupported file type: {file_path}")
                return False
            
            file_size = os.path.getsize(file_path)
            if file_size > 50 * 1024 * 1024:  # 50MB limit
                logger.error(f"File too large: {file_size / 1024 / 1024:.1f}MB")
                return False
            
            if file_size < 1024:  # 1KB minimum
                logger.error(f"File too small: {file_size} bytes")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"File validation failed: {e}")
            return False
    
    def _extract_structured_data(self, ocr_result: OCRResult) -> Dict[str, Any]:
        """Extract structured data from OCR result"""
        try:
            # Document type classification
            doc_type, doc_confidence = self.ocr_processor.ocr_system.classify_document_type(ocr_result.text)
            
            # Extract key information based on document type
            extracted_data = {
                'document_type': doc_type,
                'document_confidence': doc_confidence,
                'text': ocr_result.text,
                'patterns': ocr_result.detected_patterns,
                'quality_metrics': {
                    'confidence': ocr_result.confidence,
                    'processing_time': ocr_result.processing_time,
                    'engine_used': ocr_result.engine_used
                }
            }
            
            # Document-specific extraction
            if doc_type == 'faktur_pajak':
                extracted_data.update(self._extract_faktur_pajak_data(ocr_result.text))
            elif doc_type in ['pph_21', 'pph_23']:
                extracted_data.update(self._extract_pph_data(ocr_result.text))
            elif doc_type == 'rekening_koran':
                extracted_data.update(self._extract_rekening_data(ocr_result.text))
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Data extraction failed: {e}")
            return {'error': str(e)}
    
    def _extract_faktur_pajak_data(self, text: str) -> Dict[str, Any]:
        """Extract Faktur Pajak specific data"""
        import re
        
        data = {}
        
        # No Seri Faktur Pajak
        seri_match = re.search(r'(?:Nomor|No\.?)\s*(?:Seri\s*)?(?:Faktur\s*Pajak)?[:\s]*(\d{3}-?\d{2}\.?\d{8,12})', text, re.IGNORECASE)
        if seri_match:
            data['nomor_seri_faktur'] = seri_match.group(1)
        
        # NPWP
        npwp_matches = re.findall(r'\b\d{2}\.?\d{3}\.?\d{3}\.?\d{1}-?\d{3}\.?\d{3}\b', text)
        if npwp_matches:
            data['npwp_list'] = npwp_matches
        
        # DPP dan PPN
        dpp_match = re.search(r'(?:DPP|Dasar Pengenaan Pajak)[:\s]*Rp\.?\s*([\d.,]+)', text, re.IGNORECASE)
        if dpp_match:
            data['dpp'] = dpp_match.group(1)
        
        ppn_match = re.search(r'(?:PPN|Pajak Pertambahan Nilai)[:\s]*Rp\.?\s*([\d.,]+)', text, re.IGNORECASE)
        if ppn_match:
            data['ppn'] = ppn_match.group(1)
        
        return data
    
    def _extract_pph_data(self, text: str) -> Dict[str, Any]:
        """Extract PPh specific data"""
        import re
        
        data = {}
        
        # Masa Pajak
        masa_match = re.search(r'(?:Masa\s*Pajak)[:\s]*(\w+\s*\d{4})', text, re.IGNORECASE)
        if masa_match:
            data['masa_pajak'] = masa_match.group(1)
        
        # Jumlah Penghasilan Bruto
        bruto_match = re.search(r'(?:Penghasilan\s*Bruto|Jumlah\s*Bruto)[:\s]*Rp\.?\s*([\d.,]+)', text, re.IGNORECASE)
        if bruto_match:
            data['penghasilan_bruto'] = bruto_match.group(1)
        
        return data
    
    def _extract_rekening_data(self, text: str) -> Dict[str, Any]:
        """Extract Rekening Koran specific data"""
        import re
        
        data = {}
        
        # Nomor Rekening
        rek_match = re.search(r'(?:No\.?\s*Rekening|Account\s*No)[:\s]*(\d+)', text, re.IGNORECASE)
        if rek_match:
            data['nomor_rekening'] = rek_match.group(1)
        
        # Saldo
        saldo_matches = re.findall(r'(?:Saldo|Balance)[:\s]*Rp\.?\s*([\d.,]+)', text, re.IGNORECASE)
        if saldo_matches:
            data['saldo_list'] = saldo_matches
        
        return data
    
    def process_batch(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """Process multiple documents in batch with parallel processing"""
        logger.info(f"Starting batch processing of {len(file_paths)} documents")
        
        results = []
        
        # Process in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {
                executor.submit(self.process_document_safe, file_path): file_path 
                for file_path in file_paths
            }
            
            for future in future_to_file:
                try:
                    result = future.result(timeout=30)  # 30 second timeout per document
                    results.append(result)
                except Exception as e:
                    file_path = future_to_file[future]
                    logger.error(f"Batch processing failed for {file_path}: {e}")
                    results.append({
                        'success': False,
                        'file_path': file_path,
                        'filename': os.path.basename(file_path),
                        'error': f"Timeout or processing error: {str(e)}"
                    })
        
        # Log batch statistics
        successful = len([r for r in results if r['success']])
        logger.info(f"Batch processing completed: {successful}/{len(file_paths)} successful")
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics"""
        with self.thread_lock:
            stats = self.processing_stats.copy()
            
        if stats['total_processed'] > 0:
            stats['success_rate'] = (stats['successful'] / stats['total_processed']) * 100
        else:
            stats['success_rate'] = 0.0
            
        return stats
    
    def health_check(self) -> Dict[str, Any]:
        """System health check"""
        try:
            # Test with dummy processing
            health_status = {
                'status': 'healthy',
                'ocr_engines_available': [],
                'memory_usage_mb': 0.0,
                'disk_space_available': True,
                'statistics': self.get_statistics()
            }
            
            # Check OCR engines
            ocr_system = self.ocr_processor.ocr_system
            if hasattr(ocr_system, 'paddle_ocr') and ocr_system.paddle_ocr:
                health_status['ocr_engines_available'].append('PaddleOCR')
            if hasattr(ocr_system, 'easy_ocr') and ocr_system.easy_ocr:
                health_status['ocr_engines_available'].append('EasyOCR')
            
            # Memory check
            import psutil
            process = psutil.Process()
            health_status['memory_usage_mb'] = process.memory_info().rss / 1024 / 1024
            
            # Disk space check
            disk_usage = psutil.disk_usage('/')
            free_gb = disk_usage.free / 1024 / 1024 / 1024
            health_status['disk_space_available'] = free_gb > 1.0  # At least 1GB free
            
            logger.info("Health check completed successfully")
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }

def test_production_system():
    """Test production OCR system"""
    print("🚀 PRODUCTION OCR SYSTEM TEST")
    print("=" * 60)
    
    try:
        # Initialize production processor
        processor = ProductionOCRProcessor(max_workers=2, memory_limit_mb=512)
        
        # Health check
        health = processor.health_check()
        print(f"📊 System Health: {health['status'].upper()}")
        print(f"🔧 OCR Engines: {', '.join(health['ocr_engines_available'])}")
        print(f"💾 Memory Usage: {health['memory_usage_mb']:.1f}MB")
        
        # Get test files
        uploads_dir = "/Users/yapi/Adi/App-Dev/doc-scan-ai/backend/uploads"
        test_files = []
        
        for subdir in os.listdir(uploads_dir):
            subdir_path = os.path.join(uploads_dir, subdir)
            if os.path.isdir(subdir_path):
                for file in os.listdir(subdir_path):
                    if file.lower().endswith('.pdf'):
                        test_files.append(os.path.join(subdir_path, file))
                        if len(test_files) >= 3:  # Test with 3 files
                            break
                if len(test_files) >= 3:
                    break
        
        if not test_files:
            print("❌ No test files found")
            return
        
        print(f"\n📄 Testing with {len(test_files)} documents...")
        
        # Process batch
        start_time = time.time()
        results = processor.process_batch(test_files)
        total_time = time.time() - start_time
        
        # Display results
        print(f"\n📊 PRODUCTION TEST RESULTS")
        print("-" * 40)
        
        successful = [r for r in results if r['success']]
        
        for i, result in enumerate(results, 1):
            status = "✅" if result['success'] else "❌"
            print(f"{status} [{i}] {result['filename']}")
            
            if result['success']:
                print(f"    📊 Confidence: {result['confidence']:.1f}%")
                print(f"    📏 Text: {result['text_length']} chars")
                print(f"    🔧 Engine: {result['engine_used']}")
                print(f"    ⏱️ Time: {result['processing_time']:.2f}s")
                
                if result['extracted_data'] and 'document_type' in result['extracted_data']:
                    doc_type = result['extracted_data']['document_type']
                    print(f"    📋 Type: {doc_type}")
            else:
                print(f"    ❌ Error: {result['error']}")
        
        # Statistics
        stats = processor.get_statistics()
        print(f"\n📈 FINAL STATISTICS")
        print("-" * 40)
        print(f"Success Rate: {stats['success_rate']:.1f}%")
        print(f"Total Processing Time: {total_time:.2f}s")
        print(f"Average Time per Document: {stats['avg_processing_time']:.2f}s")
        print(f"Successful: {stats['successful']}/{stats['total_processed']}")
        
        # Production readiness
        if stats['success_rate'] >= 95:
            print("\n🏆 PRODUCTION READY! ✅")
        elif stats['success_rate'] >= 90:
            print("\n✅ PRODUCTION SUITABLE with monitoring")
        else:
            print("\n⚠️  NEEDS IMPROVEMENT before production")
            
    except Exception as e:
        logger.error(f"Production test failed: {e}")
        print(f"❌ Production test failed: {e}")

if __name__ == "__main__":
    test_production_system()