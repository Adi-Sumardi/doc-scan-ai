#!/usr/bin/env python3
"""
Simple Direct Test for Enhanced OCR
"""

import os
import sys
import time
sys.path.append('.')

def simple_test():
    print("🚀 Testing Enhanced OCR with Real Document")
    print("=" * 50)
    
    # Test file
    test_file = "uploads/4a61e2a3-ae18-4bea-a038-acbd939e1252/d4488c96-f3a3-403b-88d3-17444159e306_103. FAKTUR PAJAK 103.pdf"
    
    if not os.path.exists(test_file):
        print("❌ Test file not found")
        return
    
    print(f"📄 File: FAKTUR PAJAK 103.pdf")
    print(f"📁 Path: {test_file}")
    
    try:
        # Try basic PDF text extraction first
        print("\n📋 Testing PDF Text Extraction...")
        
        try:
            import PyPDF2
            with open(test_file, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
                
                if text.strip():
                    print(f"✅ Direct PDF extraction successful!")
                    print(f"📊 Characters extracted: {len(text)}")
                    print(f"📄 Sample text:")
                    print(f"   {repr(text[:200])}...")
                    
                    # Basic pattern analysis
                    import re
                    patterns = {
                        'Numbers': len(re.findall(r'\d+', text)),
                        'NPWP format': len(re.findall(r'\d{2}\.\d{3}\.\d{3}\.\d-\d{3}\.\d{3}', text)),
                        'Currency (Rp)': len(re.findall(r'Rp\.?\s*[\d,\.]+', text)),
                        'Dates': len(re.findall(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', text)),
                        'DPP/PPN keywords': len(re.findall(r'(dpp|ppn|faktur|pajak)', text, re.I))
                    }
                    
                    print(f"\n🔍 Pattern Analysis:")
                    for pattern, count in patterns.items():
                        print(f"   {pattern}: {count}")
                    
                    # Check if it looks like Faktur Pajak
                    faktur_keywords = ['faktur', 'pajak', 'ppn', 'dpp', 'npwp']
                    found_keywords = [kw for kw in faktur_keywords if kw.lower() in text.lower()]
                    
                    print(f"\n📋 Document Analysis:")
                    print(f"   Document type: Faktur Pajak")
                    print(f"   Keywords found: {found_keywords}")
                    print(f"   Confidence: {'High' if len(found_keywords) >= 3 else 'Medium' if len(found_keywords) >= 2 else 'Low'}")
                    
                    return True
                else:
                    print("⚠️ PDF appears to be image-based, need OCR")
                    
        except Exception as e:
            print(f"⚠️ PDF extraction failed: {e}")
        
        # Test Enhanced OCR
        print("\n🤖 Testing Enhanced OCR...")
        
        from enhanced_ocr_processor import EnhancedOCRProcessor
        
        start_time = time.time()
        processor = EnhancedOCRProcessor()
        init_time = time.time() - start_time
        print(f"⚡ Processor initialized in {init_time:.2f}s")
        print(f"🤖 Available engines: {list(processor.multi_ocr.engines.keys())}")
        
        # Process document
        start_time = time.time()
        result = processor.process_document(test_file)
        process_time = time.time() - start_time
        
        print(f"\n📊 Enhanced OCR Results:")
        print(f"   ✅ Success: {result['success']}")
        print(f"   ⏱️ Processing time: {process_time:.2f}s")
        
        if result['success']:
            print(f"   📊 Confidence: {result['confidence']:.2%}")
            print(f"   📝 Characters: {result['character_count']}")
            print(f"   📖 Words: {result['word_count']}")
            print(f"   📋 Lines: {result['line_count']}")
            
            if 'details' in result:
                method = result['details'].get('method', 'unknown')
                engine = result['details'].get('best_engine', 'unknown')
                print(f"   🔧 Method: {method}")
                if engine != 'unknown':
                    print(f"   🤖 Best engine: {engine}")
            
            # Show sample
            text = result['text']
            sample = text[:300] + "..." if len(text) > 300 else text
            print(f"\n📄 Extracted text sample:")
            print(f"   {repr(sample)}")
            
            return True
        else:
            print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = simple_test()
    print(f"\n{'🎉 Test completed!' if success else '❌ Test failed!'}")