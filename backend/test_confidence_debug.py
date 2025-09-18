#!/usr/bin/env python3
"""
Test script untuk debug confidence calculation
"""

import asyncio
import json
from ai_processor import process_document_ai, calculate_confidence

async def test_confidence():
    print("🔍 Testing Confidence Calculation")
    
    # Test data similar to what you showed
    test_data = {
        "keluaran": {
            "nama_lawan_transaksi": "",
            "no_seri_fp": "",
            "alamat": "",
            "npwp": "",
            "keterangan_barang": [],
            "quantity": 0,
            "diskon": 0,
            "harga": 0,
            "dpp": 0,
            "ppn": 0,
            "tgl_faktur": "",
            "keterangan_lain": "",
            "tgl_rekam": "2025-09-18"
        },
        "masukan": {
            "nama_lawan_transaksi": "Barang Kena Pajak / Jasa Kena PajakHarga Jual / Penggantian /",
            "no_seri_fp": "",
            "alamat": "GEDUNG TELKOM LANDMARK TOWER LT 27, JL JEND GATOT SUBROTO KAV 52 ,  RT 000,  RW",
            "npwp": "0010712446093000",
            "email": "grouptax@mitratel.co.id",
            "keterangan_barang": [],
            "quantity": 165000000,
            "diskon": 0,
            "harga": 0,
            "dpp": 0,
            "ppn": 165000000,
            "tgl_faktur": "",
            "keterangan_lain": "",
            "tgl_rekam": "2025-09-18"
        }
    }
    
    print("\n📊 Test Data:")
    print(json.dumps(test_data, indent=2))
    
    # Test confidence calculation
    confidence = calculate_confidence(test_data, "faktur_pajak")
    
    print(f"\n🎯 Calculated Confidence: {confidence:.4f} ({confidence:.2%})")
    
    # Manual analysis
    masukan_data = test_data.get('masukan', {})
    keluaran_data = test_data.get('keluaran', {})
    
    masukan_count = sum(1 for k, v in masukan_data.items() 
                      if v and str(v).strip() and k not in ['parsing_error', 'raw_text_sample'])
    keluaran_count = sum(1 for k, v in keluaran_data.items() 
                       if v and str(v).strip() and k not in ['parsing_error', 'raw_text_sample'])
    
    print(f"\n📈 Analysis:")
    print(f"   - Masukan non-empty fields: {masukan_count}")
    print(f"   - Keluaran non-empty fields: {keluaran_count}")
    print(f"   - Total non-empty fields: {masukan_count + keluaran_count}")
    
    print(f"\n🔍 Masukan non-empty fields:")
    for k, v in masukan_data.items():
        if v and str(v).strip():
            print(f"   - {k}: {v}")
    
    print(f"\n🔍 Keluaran non-empty fields:")
    for k, v in keluaran_data.items():
        if v and str(v).strip():
            print(f"   - {k}: {v}")

if __name__ == "__main__":
    asyncio.run(test_confidence())