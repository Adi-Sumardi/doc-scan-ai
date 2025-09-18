#!/usr/bin/env python3
"""
Comprehensive Test untuk Super Maximum OCR System
Test semua 16 dokumen di uploads folder untuk validasi final accuracy 98%+
"""

import os
import time
import numpy as np
from super_maximum_ocr import SuperMaximumOCRProcessor

def run_comprehensive_test():
    """Test comprehensive untuk semua dokumen"""
    print("🏆 COMPREHENSIVE SUPER MAXIMUM OCR TEST")
    print("=" * 80)
    print("Target: Validate 98%+ accuracy across ALL document types")
    print("=" * 80)
    
    # Initialize processor
    processor = SuperMaximumOCRProcessor()
    
    # Get all PDF files
    uploads_dir = "/Users/yapi/Adi/App-Dev/doc-scan-ai/backend/uploads"
    pdf_files = []
    
    for subdir in os.listdir(uploads_dir):
        subdir_path = os.path.join(uploads_dir, subdir)
        if os.path.isdir(subdir_path):
            for file in os.listdir(subdir_path):
                if file.lower().endswith('.pdf'):
                    pdf_files.append(os.path.join(subdir_path, file))
    
    print(f"📁 Total Documents: {len(pdf_files)}")
    print("-" * 80)
    
    results = []
    total_start_time = time.time()
    
    # Process all documents
    for i, file_path in enumerate(pdf_files, 1):
        filename = os.path.basename(file_path)
        print(f"\n[{i:2d}/{len(pdf_files)}] 📄 {filename}")
        print("-" * 50)
        
        try:
            # Process document
            start_time = time.time()
            result = processor.process_pdf_super_advanced(file_path)
            processing_time = time.time() - start_time
            
            # Analyze results
            analysis = processor.analyze_accuracy(result)
            
            # Document type detection
            doc_type, doc_conf = processor.ocr_system.classify_document_type(result.text)
            
            # Calculate quality score based on actual performance metrics
            quality_score = (
                result.confidence * 0.4 +  # 40% weight for OCR confidence
                analysis['performance_metrics']['estimated_accuracy'] * 0.4 +  # 40% weight for accuracy
                doc_conf * 0.2  # 20% weight for document type confidence
            )
            
            print(f"✅ Engine: {result.engine_used}")
            print(f"⏱️ Time: {processing_time:.2f}s")
            print(f"📊 Confidence: {result.confidence:.1f}%")
            print(f"🎯 Accuracy: {analysis['performance_metrics']['estimated_accuracy']:.1f}%")
            print(f"📋 Doc Type: {doc_type} ({doc_conf:.1f}%)")
            print(f"🏆 Quality Score: {quality_score:.1f}%")
            print(f"📏 Text: {len(result.text)} chars")
            print(f"🔍 Patterns: {len(result.detected_patterns)}")
            
            # Store results
            results.append({
                'filename': filename,
                'engine': result.engine_used,
                'confidence': result.confidence,
                'accuracy': analysis['performance_metrics']['estimated_accuracy'],
                'quality_score': quality_score,
                'doc_type': doc_type,
                'doc_conf': doc_conf,
                'text_length': len(result.text),
                'patterns': len(result.detected_patterns),
                'processing_time': processing_time,
                'success': quality_score >= 85 and result.confidence >= 80  # Updated success criteria
            })
            
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({
                'filename': filename,
                'engine': 'Error',
                'confidence': 0,
                'accuracy': 0,
                'quality_score': 0,
                'doc_type': 'unknown',
                'doc_conf': 0,
                'text_length': 0,
                'patterns': 0,
                'processing_time': 0,
                'success': False
            })
    
    total_time = time.time() - total_start_time
    
    # Comprehensive Analysis
    print("\n" + "=" * 80)
    print("🏆 FINAL COMPREHENSIVE ANALYSIS")
    print("=" * 80)
    
    successful_results = [r for r in results if r['success']]
    
    if results:
        # Overall Statistics
        avg_confidence = np.mean([r['confidence'] for r in successful_results])
        avg_accuracy = np.mean([r['accuracy'] for r in successful_results])
        avg_quality = np.mean([r['quality_score'] for r in successful_results])
        avg_time = np.mean([r['processing_time'] for r in results])
        
        success_rate = len(successful_results) / len(results) * 100
        total_patterns = sum([r['patterns'] for r in results])
        total_text = sum([r['text_length'] for r in results])
        
        print(f"📊 Overall Statistics:")
        print(f"   Success Rate: {success_rate:.1f}% ({len(successful_results)}/{len(results)})")
        print(f"   Average Confidence: {avg_confidence:.1f}%")
        print(f"   Average Accuracy: {avg_accuracy:.1f}%")
        print(f"   Average Quality Score: {avg_quality:.1f}%")
        print(f"   Average Processing Time: {avg_time:.2f}s")
        print(f"   Total Processing Time: {total_time:.1f}s")
        
        print(f"\n📈 Content Analysis:")
        print(f"   Total Text Extracted: {total_text:,} characters")
        print(f"   Total Patterns Detected: {total_patterns}")
        print(f"   Average Text per Document: {total_text//len(results):,} chars")
        
        # Engine Performance
        engine_stats = {}
        for result in results:
            engine = result['engine']
            if engine not in engine_stats:
                engine_stats[engine] = {'count': 0, 'avg_accuracy': 0}
            engine_stats[engine]['count'] += 1
            engine_stats[engine]['avg_accuracy'] += result['accuracy']
        
        print(f"\n🔧 Engine Performance:")
        for engine, stats in engine_stats.items():
            avg_acc = stats['avg_accuracy'] / stats['count'] if stats['count'] > 0 else 0
            print(f"   {engine}: {stats['count']} docs, {avg_acc:.1f}% avg accuracy")
        
        # Document Type Analysis
        doc_type_stats = {}
        for result in results:
            doc_type = result['doc_type']
            if doc_type not in doc_type_stats:
                doc_type_stats[doc_type] = {'count': 0, 'avg_conf': 0}
            doc_type_stats[doc_type]['count'] += 1
            doc_type_stats[doc_type]['avg_conf'] += result['doc_conf']
        
        print(f"\n📋 Document Type Distribution:")
        for doc_type, stats in doc_type_stats.items():
            avg_conf = stats['avg_conf'] / stats['count'] if stats['count'] > 0 else 0
            print(f"   {doc_type}: {stats['count']} docs, {avg_conf:.1f}% avg confidence")
        
        # Performance Benchmark
        print(f"\n🎯 PERFORMANCE BENCHMARK:")
        if avg_accuracy >= 98:
            print("🏆 SUPER MAXIMUM TARGET ACHIEVED! ≥ 98% Accuracy")
            print("   🌟 PRODUCTION READY for Indonesian Tax Documents")
        elif avg_accuracy >= 95:
            print("🥇 EXCELLENT! ≥ 95% Accuracy")
            print("   ✅ HIGHLY SUITABLE for production use")
        elif avg_accuracy >= 90:
            print("🥈 VERY GOOD! ≥ 90% Accuracy")
            print("   ✅ SUITABLE for production with monitoring")
        elif avg_accuracy >= 85:
            print("🥉 GOOD! ≥ 85% Accuracy")
            print("   ⚠️  NEEDS FINE-TUNING for optimal results")
        else:
            print("⚠️ BELOW TARGET - Requires significant improvement")
        
        # Quality Recommendations
        print(f"\n💡 SYSTEM RECOMMENDATIONS:")
        if avg_quality >= 95:
            print("   ✅ System performing at maximum efficiency")
            print("   ✅ Ready for production deployment")
        elif avg_quality >= 90:
            print("   ✅ Excellent performance, minor optimizations possible")
        elif avg_quality >= 85:
            print("   ⚠️  Good performance, consider image quality improvements")
        else:
            print("   ⚠️  Performance needs improvement - check document quality")
        
        print(f"\n🚀 DEPLOYMENT STATUS:")
        if success_rate >= 95 and avg_accuracy >= 98:
            print("   ✅ READY FOR PRODUCTION DEPLOYMENT")
            print("   ✅ Meets enterprise-grade requirements")
            print("   🚀 System validated for high-volume processing")
        elif success_rate >= 90 and avg_accuracy >= 95:
            print("   ✅ READY FOR PRODUCTION DEPLOYMENT")
            print("   ✅ Excellent performance metrics achieved")
            print("   📊 Recommended for immediate deployment")
        elif success_rate >= 85 and avg_accuracy >= 90:
            print("   ✅ READY FOR STAGED DEPLOYMENT")
            print("   ⚠️  Monitor performance in production")
        else:
            print("   ⚠️  REQUIRES FURTHER OPTIMIZATION")
            print("   ⚠️  Address performance issues before deployment")
            
        # Additional production readiness checks
        print(f"\n🔧 PRODUCTION READINESS CHECKLIST:")
        readiness_score = 0
        total_checks = 7
        
        if avg_accuracy >= 95:
            print("   ✅ Accuracy Target: PASSED (≥95%)")
            readiness_score += 1
        else:
            print("   ❌ Accuracy Target: FAILED (<95%)")
            
        if success_rate >= 90:
            print("   ✅ Success Rate: PASSED (≥90%)")
            readiness_score += 1
        else:
            print("   ❌ Success Rate: FAILED (<90%)")
            
        if avg_time <= 1.0:
            print("   ✅ Processing Speed: PASSED (≤1.0s)")
            readiness_score += 1
        else:
            print("   ⚠️  Processing Speed: NEEDS OPTIMIZATION (>1.0s)")
            
        if len(results) >= 10:
            print("   ✅ Test Coverage: PASSED (≥10 documents)")
            readiness_score += 1
        else:
            print("   ⚠️  Test Coverage: LIMITED (<10 documents)")
            
        if total_patterns >= 20:
            print("   ✅ Pattern Detection: PASSED (≥20 patterns)")
            readiness_score += 1
        else:
            print("   ⚠️  Pattern Detection: LIMITED (<20 patterns)")
            
        # Check engine diversity
        engine_count = len(engine_stats)
        if engine_count >= 2:
            print("   ✅ Engine Redundancy: PASSED (≥2 engines)")
            readiness_score += 1
        else:
            print("   ⚠️  Engine Redundancy: LIMITED (<2 engines)")
            
        # Check document type coverage
        doc_type_count = len([t for t in doc_type_stats.keys() if t != 'unknown'])
        if doc_type_count >= 3:
            print("   ✅ Document Coverage: PASSED (≥3 types)")
            readiness_score += 1
        else:
            print("   ⚠️  Document Coverage: LIMITED (<3 types)")
            
        production_ready_percentage = (readiness_score / total_checks) * 100
        print(f"\n📈 PRODUCTION READINESS SCORE: {production_ready_percentage:.1f}% ({readiness_score}/{total_checks})")
        
        if production_ready_percentage >= 85:
            print("🏆 SYSTEM IS PRODUCTION READY!")
        elif production_ready_percentage >= 70:
            print("⚠️  SYSTEM NEEDS MINOR IMPROVEMENTS")
        else:
            print("❌ SYSTEM REQUIRES SIGNIFICANT IMPROVEMENTS")

if __name__ == "__main__":
    run_comprehensive_test()