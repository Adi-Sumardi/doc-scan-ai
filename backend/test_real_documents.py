#!/usr/bin/env python3
"""
Comprehensive Test for Enhanced OCR with Real Documents
Test accuracy and pattern recognition for Indonesian tax documents
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple
import asyncio

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def detect_document_type_from_filename(filename: str) -> str:
    """Detect document type from filename"""
    filename_lower = filename.lower()
    
    if 'faktur' in filename_lower or 'fp' in filename_lower:
        return 'faktur_pajak'
    elif 'pph 21' in filename_lower or 'pph21' in filename_lower:
        return 'pph21'
    elif 'pph 23' in filename_lower or 'pph23' in filename_lower:
        return 'pph23'
    elif 'rekening' in filename_lower or 'koran' in filename_lower:
        return 'rekening_koran'
    elif 'invoice' in filename_lower:
        return 'invoice'
    else:
        return 'unknown'

def analyze_extraction_patterns(text: str, doc_type: str) -> Dict[str, Any]:
    """Analyze extracted text for common patterns"""
    import re
    
    patterns = {
        'numbers': len(re.findall(r'\d+', text)),
        'dates': len(re.findall(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', text)),
        'currency': len(re.findall(r'Rp\.?\s*[\d,\.]+', text)),
        'npwp': len(re.findall(r'\d{2}\.\d{3}\.\d{3}\.\d-\d{3}\.\d{3}', text)),
        'phone': len(re.findall(r'(\+62|0)\d{8,12}', text)),
        'email': len(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)),
        'total_chars': len(text),
        'total_words': len(text.split()),
        'total_lines': len(text.split('\n'))
    }
    
    # Document-specific patterns
    if doc_type == 'faktur_pajak':
        patterns.update({
            'faktur_keywords': len(re.findall(r'(faktur|pajak|ppn|dpp)', text, re.I)),
            'serial_numbers': len(re.findall(r'[0-9]{3}-[0-9]{2}\.[0-9]{8}', text))
        })
    elif doc_type in ['pph21', 'pph23']:
        patterns.update({
            'pph_keywords': len(re.findall(r'(pph|potong|penghasilan|bruto)', text, re.I)),
            'tarif_patterns': len(re.findall(r'\d+(\.\d+)?%', text))
        })
    
    return patterns

async def test_document_processing():
    """Test enhanced OCR with real documents from uploads folder"""
    try:
        logger.info("🚀 Starting Comprehensive Document Processing Test")
        logger.info("=" * 70)
        
        # Import processors
        from enhanced_ocr_processor import EnhancedOCRProcessor
        from ai_processor import IndonesianTaxDocumentParser
        
        # Initialize processors
        enhanced_ocr = EnhancedOCRProcessor()
        document_parser = IndonesianTaxDocumentParser()
        
        # Find all documents in uploads folder
        uploads_dir = Path('./uploads')
        test_files = []
        
        for batch_dir in uploads_dir.iterdir():
            if batch_dir.is_dir():
                for file_path in batch_dir.iterdir():
                    if file_path.suffix.lower() in ['.pdf', '.jpg', '.jpeg', '.png', '.tiff']:
                        test_files.append(file_path)
        
        if not test_files:
            logger.error("❌ No documents found in uploads folder")
            return False
        
        logger.info(f"📁 Found {len(test_files)} documents to test")
        
        # Process each document
        results = []
        
        for i, file_path in enumerate(test_files[:5]):  # Test first 5 files
            logger.info(f"\n📄 Processing document {i+1}/{min(len(test_files), 5)}")
            logger.info(f"📁 File: {file_path.name}")
            logger.info("-" * 50)
            
            # Detect document type
            doc_type = detect_document_type_from_filename(file_path.name)
            logger.info(f"🏷️ Detected type: {doc_type}")
            
            # Test 1: Enhanced OCR extraction
            start_time = time.time()
            ocr_result = enhanced_ocr.process_document(str(file_path))
            ocr_time = time.time() - start_time
            
            # Test 2: Full document parsing
            start_time = time.time()
            if doc_type != 'unknown':
                from ai_processor import process_document_ai
                parsed_result = await process_document_ai(str(file_path), doc_type)
            else:
                parsed_result = None
            parse_time = time.time() - start_time
            
            # Analyze patterns
            if ocr_result['success']:
                patterns = analyze_extraction_patterns(ocr_result['text'], doc_type)
            else:
                patterns = {}
            
            # Compile results
            test_result = {
                'file_name': file_path.name,
                'file_size': file_path.stat().st_size,
                'document_type': doc_type,
                'ocr_result': {
                    'success': ocr_result['success'],
                    'confidence': ocr_result.get('confidence', 0.0),
                    'processing_time': ocr_time,
                    'engine_used': ocr_result.get('details', {}).get('best_engine', 'unknown'),
                    'character_count': ocr_result.get('character_count', 0),
                    'word_count': ocr_result.get('word_count', 0)
                },
                'parsing_result': {
                    'success': parsed_result is not None and parsed_result.get('success', False),
                    'processing_time': parse_time,
                    'confidence': parsed_result.get('confidence', 0.0) if parsed_result else 0.0
                },
                'pattern_analysis': patterns
            }
            
            results.append(test_result)
            
            # Display results
            logger.info(f"🤖 OCR Results:")
            logger.info(f"   ✅ Success: {test_result['ocr_result']['success']}")
            logger.info(f"   📊 Confidence: {test_result['ocr_result']['confidence']:.2%}")
            logger.info(f"   🚀 Engine: {test_result['ocr_result']['engine_used']}")
            logger.info(f"   📝 Text: {test_result['ocr_result']['character_count']} chars, "
                       f"{test_result['ocr_result']['word_count']} words")
            logger.info(f"   ⏱️ Time: {ocr_time:.2f}s")
            
            if parsed_result:
                logger.info(f"📋 Parsing Results:")
                logger.info(f"   ✅ Success: {test_result['parsing_result']['success']}")
                logger.info(f"   📊 Confidence: {test_result['parsing_result']['confidence']:.2%}")
                logger.info(f"   ⏱️ Time: {parse_time:.2f}s")
            
            logger.info(f"🔍 Pattern Analysis:")
            logger.info(f"   🔢 Numbers found: {patterns.get('numbers', 0)}")
            logger.info(f"   📅 Dates found: {patterns.get('dates', 0)}")
            logger.info(f"   💰 Currency amounts: {patterns.get('currency', 0)}")
            logger.info(f"   🆔 NPWP numbers: {patterns.get('npwp', 0)}")
            
            # Show sample text if successful
            if ocr_result['success'] and ocr_result['text']:
                sample_text = ocr_result['text'][:200] + "..." if len(ocr_result['text']) > 200 else ocr_result['text']
                logger.info(f"📄 Sample extracted text:")
                logger.info(f"   {repr(sample_text)}")
            
            # Show parsed data structure if successful
            if parsed_result and parsed_result.get('success'):
                logger.info(f"🗂️ Parsed data structure:")
                extracted_data = parsed_result.get('extracted_data', {})
                if isinstance(extracted_data, dict):
                    for key, value in list(extracted_data.items())[:3]:  # Show first 3 keys
                        if isinstance(value, dict):
                            logger.info(f"   {key}: {len(value)} fields")
                        else:
                            logger.info(f"   {key}: {str(value)[:50]}...")
        
        # Generate summary report
        logger.info("\n" + "=" * 70)
        logger.info("📊 COMPREHENSIVE TEST SUMMARY")
        logger.info("=" * 70)
        
        total_tests = len(results)
        successful_ocr = sum(1 for r in results if r['ocr_result']['success'])
        successful_parsing = sum(1 for r in results if r['parsing_result']['success'])
        
        logger.info(f"📁 Total documents tested: {total_tests}")
        logger.info(f"✅ OCR success rate: {successful_ocr}/{total_tests} ({successful_ocr/max(total_tests,1)*100:.1f}%)")
        logger.info(f"✅ Parsing success rate: {successful_parsing}/{total_tests} ({successful_parsing/max(total_tests,1)*100:.1f}%)")
        
        if successful_ocr > 0:
            avg_confidence = sum(r['ocr_result']['confidence'] for r in results if r['ocr_result']['success']) / successful_ocr
            avg_chars = sum(r['ocr_result']['character_count'] for r in results if r['ocr_result']['success']) / successful_ocr
            avg_time = sum(r['ocr_result']['processing_time'] for r in results if r['ocr_result']['success']) / successful_ocr
            
            logger.info(f"📊 Average OCR confidence: {avg_confidence:.2%}")
            logger.info(f"📝 Average characters extracted: {avg_chars:.0f}")
            logger.info(f"⏱️ Average processing time: {avg_time:.2f}s")
            
            # Engine usage statistics
            engines_used = [r['ocr_result']['engine_used'] for r in results if r['ocr_result']['success']]
            engine_counts = {engine: engines_used.count(engine) for engine in set(engines_used)}
            logger.info(f"🤖 Engine usage: {engine_counts}")
        
        # Document type analysis
        doc_types = [r['document_type'] for r in results]
        type_counts = {doc_type: doc_types.count(doc_type) for doc_type in set(doc_types)}
        logger.info(f"📄 Document types tested: {type_counts}")
        
        # Pattern analysis summary
        logger.info(f"\n🔍 PATTERN ANALYSIS SUMMARY:")
        total_numbers = sum(r['pattern_analysis'].get('numbers', 0) for r in results)
        total_dates = sum(r['pattern_analysis'].get('dates', 0) for r in results)
        total_currency = sum(r['pattern_analysis'].get('currency', 0) for r in results)
        total_npwp = sum(r['pattern_analysis'].get('npwp', 0) for r in results)
        
        logger.info(f"🔢 Total numbers detected: {total_numbers}")
        logger.info(f"📅 Total dates detected: {total_dates}")
        logger.info(f"💰 Total currency amounts: {total_currency}")
        logger.info(f"🆔 Total NPWP numbers: {total_npwp}")
        
        # Save detailed results
        results_file = Path('./test_results.json')
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                'test_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'summary': {
                    'total_documents': total_tests,
                    'ocr_success_rate': successful_ocr / max(total_tests, 1),
                    'parsing_success_rate': successful_parsing / max(total_tests, 1),
                    'average_confidence': avg_confidence if successful_ocr > 0 else 0.0
                },
                'detailed_results': results
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Detailed results saved to: {results_file}")
        
        # Final assessment
        logger.info(f"\n🎯 FINAL ASSESSMENT:")
        if avg_confidence >= 0.90:
            logger.info(f"🏆 EXCELLENT: Average confidence {avg_confidence:.2%} - Production ready!")
        elif avg_confidence >= 0.80:
            logger.info(f"✅ GOOD: Average confidence {avg_confidence:.2%} - Suitable for production")
        elif avg_confidence >= 0.70:
            logger.info(f"⚠️ FAIR: Average confidence {avg_confidence:.2%} - May need tuning")
        else:
            logger.info(f"❌ POOR: Average confidence {avg_confidence:.2%} - Needs improvement")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    logger.info("🧪 Starting Comprehensive Document Processing Test")
    
    # Run async test
    success = asyncio.run(test_document_processing())
    
    if success:
        logger.info("🎉 Test completed successfully!")
    else:
        logger.error("❌ Test failed!")