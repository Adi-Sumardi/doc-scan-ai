#!/usr/bin/env python3
"""
Script untuk test recalculate confidence via API
"""

import requests
import json

def test_recalculate():
    """Test recalculating confidence"""
    try:
        batch_id = "941c0117-c752-4e02-b28b-01fc28fccd0b"  # Your batch ID
        
        print("🔍 Before recalculation:")
        response = requests.get(f"http://localhost:8000/api/batches/{batch_id}/results")
        if response.status_code == 200:
            results = response.json()
            for result in results:
                print(f"   - {result['original_filename']}: {result['confidence']:.4f} ({result['confidence']:.2%})")
        
        print("\n🔄 Recalculating confidence...")
        recalc_response = requests.post(f"http://localhost:8000/api/debug/recalculate-confidence/{batch_id}")
        
        if recalc_response.status_code == 200:
            recalc_result = recalc_response.json()
            print(f"✅ {recalc_result['message']}")
            
            for update in recalc_result['updates']:
                print(f"   - {update['filename']}: {update['new_confidence']:.4f} ({update['new_confidence']:.2%})")
        
        print("\n🔍 After recalculation:")
        response = requests.get(f"http://localhost:8000/api/batches/{batch_id}/results")
        if response.status_code == 200:
            results = response.json()
            for result in results:
                print(f"   - {result['original_filename']}: {result['confidence']:.4f} ({result['confidence']:.2%})")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_recalculate()