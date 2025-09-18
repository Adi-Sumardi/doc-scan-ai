#!/usr/bin/env python3
"""
Quick Test for Enhanced OCR with Real Documents
"""

import os
import sys
import time
import logging
from pathlib import Path

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def quick_test():
    """Quick test of enhanced OCR"""
    try:
        from enhanced_ocr_processor import EnhancedOCRProcessor
        
        logger.info("🚀 Quick Enhanced OCR Test")
        logger.info("=" * 40)
        
        # Initialize processor
        processor = EnhancedOCRProcessor()
        
        # Find first document
        uploads_dir = Path('./uploads')
        test_file = None
        
        for batch_dir in uploads_dir.iterdir():
            if batch_dir.is_dir():
                for file_path in batch_dir.iterdir():
                    if file_path.suffix.lower() in ['.pdf', '.jpg', '.jpeg', '.png']:
                        test_file = file_path
                        break
                if test_file:
                    break
        
        if not test_file:
            logger.error("❌ No test files found")
            return False
        
        logger.info(f"📄 Testing file: {test_file.name}")
        
        # Process document
        start_time = time.time()
        result = processor.process_document(str(test_file))
        processing_time = time.time() - start_time
        
        # Display results
        logger.info(f"⏱️ Processing time: {processing_time:.2f}s")
        logger.info(f"✅ Success: {result['success']}")
        
        if result['success']:
            logger.info(f"📊 Confidence: {result['confidence']:.2%}")
            logger.info(f"📝 Characters: {result['character_count']}")
            logger.info(f"📖 Words: {result['word_count']}")
            logger.info(f"📋 Lines: {result['line_count']}")
            
            # Show engines used
            details = result.get('details', {})
            if 'best_engine' in details:
                logger.info(f"🤖 Best engine: {details['best_engine']}")
            
            # Show sample text
            text = result['text']
            sample = text[:300] + "..." if len(text) > 300 else text
            logger.info(f"📄 Sample text:")
            logger.info(f"   {repr(sample)}")
            
            # Quick pattern analysis
            import re
            patterns = {
                'numbers': len(re.findall(r'\d+', text)),
                'dates': len(re.findall(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', text)),
                'currency': len(re.findall(r'Rp\.?\s*[\d,\.]+', text)),
                'npwp': len(re.findall(r'\d{2}\.\d{3}\.\d{3}\.\d-\d{3}\.\d{3}', text))
            }
            
            logger.info(f"🔍 Patterns found:")
            for pattern, count in patterns.items():
                logger.info(f"   {pattern}: {count}")
        
        return result['success']
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = quick_test()
    
    if success:
        logger.info("🎉 Quick test completed successfully!")
    else:
        logger.error("❌ Quick test failed!")