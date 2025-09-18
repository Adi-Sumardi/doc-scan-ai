#!/usr/bin/env python3
"""
Script untuk membersihkan storage dan recalculate confidence
"""

import requests
import json

def clear_backend_storage():
    """Clear all stored data and force recalculation"""
    try:
        # Get all batches
        response = requests.get("http://localhost:8000/api/batches")
        if response.status_code == 200:
            batches = response.json()
            print(f"🔍 Found {len(batches)} batches")
            
            for batch in batches:
                batch_id = batch['id']
                print(f"📁 Batch: {batch_id}")
                
                # Get results for this batch
                results_response = requests.get(f"http://localhost:8000/api/batches/{batch_id}/results")
                if results_response.status_code == 200:
                    results = results_response.json()
                    print(f"   - Found {len(results)} results")
                    
                    for result in results:
                        print(f"   - File: {result['original_filename']}")
                        print(f"   - Current confidence: {result['confidence']}")
        else:
            print(f"❌ Failed to get batches: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def add_clear_storage_endpoint():
    """Add endpoint to clear storage in backend"""
    print("🔧 Adding clear storage endpoint to backend...")

if __name__ == "__main__":
    print("🧹 Backend Storage Analysis")
    clear_backend_storage()