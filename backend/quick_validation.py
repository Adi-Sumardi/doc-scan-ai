#!/usr/bin/env python3
"""
QUICK PRODUCTION VALIDATION
Simple validation untuk check system readiness
"""

import requests
import time

def test_backend():
    """Quick backend test"""
    try:
        print("🔍 Testing Backend...")
        response = requests.get("http://localhost:8000/api/batches", timeout=5)
        if response.status_code == 200:
            print("✅ Backend: RESPONSIVE")
            return True
        else:
            print(f"❌ Backend: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend: {e}")
        return False

def test_frontend():
    """Quick frontend test"""
    try:
        print("🌐 Testing Frontend...")
        response = requests.get("http://localhost:5173", timeout=5)
        if response.status_code == 200:
            print("✅ Frontend: RESPONSIVE")
            return True
        else:
            print(f"❌ Frontend: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Frontend: {e}")
        return False

def test_ocr_system():
    """Quick OCR test"""
    try:
        print("⚡ Testing OCR System...")
        from production_ocr import ProductionOCRProcessor
        processor = ProductionOCRProcessor(max_workers=1, memory_limit_mb=256)
        health = processor.health_check()
        
        if health['status'] == 'healthy':
            print(f"✅ OCR: {health['status'].upper()}")
            print(f"   Engines: {', '.join(health['ocr_engines_available'])}")
            print(f"   Memory: {health['memory_usage_mb']:.1f}MB")
            return True
        else:
            print(f"❌ OCR: {health['status']}")
            return False
    except Exception as e:
        print(f"❌ OCR: {e}")
        return False

def main():
    print("🚀 QUICK PRODUCTION VALIDATION")
    print("=" * 40)
    
    backend_ok = test_backend()
    frontend_ok = test_frontend()
    ocr_ok = test_ocr_system()
    
    print("\n📊 RESULTS:")
    print(f"Backend:  {'✅' if backend_ok else '❌'}")
    print(f"Frontend: {'✅' if frontend_ok else '❌'}")
    print(f"OCR:      {'✅' if ocr_ok else '❌'}")
    
    all_ok = backend_ok and frontend_ok and ocr_ok
    print(f"\n🎯 PRODUCTION READY: {'YES ✅' if all_ok else 'NO ❌'}")
    
    if all_ok:
        print("🚀 System siap untuk production!")
    else:
        print("⚠️  Masih ada issues yang perlu diperbaiki")
    
    return all_ok

if __name__ == "__main__":
    main()