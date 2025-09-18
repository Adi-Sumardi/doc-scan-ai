#!/usr/bin/env python3
"""
Test script untuk parsing faktur pajak yang sudah diperbaiki
"""

import sys
import os
import asyncio

# Add the backend directory to Python path
sys.path.append('/Users/yapi/Adi/App-Dev/doc-scan-ai/backend')

from ai_processor import IndonesianTaxDocumentParser

# Create global parser instance
parser = IndonesianTaxDocumentParser()

async def test_improved_parsing():
    """Test improved faktur pajak parsing"""
    
    # Sample text that represents the data we extracted
    sample_text = """
    GEDUNG TELKOM LANDMARK TOWER LT 27, JL JEND GATOT SUBROTO KAV 52 ,  RT 000,  RW
    NPWP: 0010712446093000
    Barang Kena Pajak / Jasa Kena PajakHarga Jual / Penggantian /
    grouptax@mitratel.co.id
    PPN: 165000000
    """
    
    print("🔍 Testing Improved Faktur Pajak Parsing")
    print("\n📝 Sample Text:")
    print(sample_text)
    
    # Parse with improved logic using the correct parser instance
    result = parser.parse_faktur_pajak(sample_text)
    
    print("\n📊 Parsing Result:")
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    print("\n🔍 Analysis:")
    print(f"Keluaran fields filled: {sum(1 for k,v in result['keluaran'].items() if v and str(v).strip())}")
    print(f"Masukan fields filled: {sum(1 for k,v in result['masukan'].items() if v and str(v).strip())}")

if __name__ == "__main__":
    asyncio.run(test_improved_parsing())