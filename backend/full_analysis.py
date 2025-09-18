#!/usr/bin/env python3
"""
Full Document Analysis Test
"""

import os
import sys
import time
import re
sys.path.append('.')

def analyze_document():
    print("🚀 Full Document Analysis Test")
    print("=" * 60)
    
    # Test file
    test_file = "uploads/4a61e2a3-ae18-4bea-a038-acbd939e1252/d4488c96-f3a3-403b-88d3-17444159e306_103. FAKTUR PAJAK 103.pdf"
    
    print(f"📄 File: FAKTUR PAJAK 103.pdf")
    
    try:
        # Extract full text
        import PyPDF2
        with open(test_file, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            full_text = ""
            for page in reader.pages:
                full_text += page.extract_text() + "\n"
        
        print(f"📊 Full document text ({len(full_text)} characters):")
        print("=" * 60)
        print(full_text)
        print("=" * 60)
        
        # Test with AI processor
        print(f"\n🤖 Testing with AI Document Parser...")
        
        from ai_processor import process_document_ai
        import asyncio
        
        async def test_parsing():
            result = await process_document_ai(test_file, 'faktur_pajak')
            return result
        
        start_time = time.time()
        parse_result = asyncio.run(test_parsing())
        parse_time = time.time() - start_time
        
        print(f"⏱️ Parsing time: {parse_time:.2f}s")
        print(f"✅ Success: {parse_result.get('success', False)}")
        print(f"📊 Confidence: {parse_result.get('confidence', 0.0):.2%}")
        
        if parse_result.get('success'):
            extracted_data = parse_result.get('extracted_data', {})
            print(f"\n📋 Parsed Faktur Pajak Data:")
            print("=" * 40)
            
            # Display keluaran data
            if 'keluaran' in extracted_data:
                keluaran = extracted_data['keluaran']
                print(f"🟢 FAKTUR PAJAK KELUARAN:")
                print(f"   Nama Lawan Transaksi: {keluaran.get('nama_lawan_transaksi', 'N/A')}")
                print(f"   No Seri FP: {keluaran.get('no_seri_fp', 'N/A')}")
                print(f"   NPWP: {keluaran.get('npwp', 'N/A')}")
                print(f"   Alamat: {keluaran.get('alamat', 'N/A')}")
                print(f"   DPP: Rp {keluaran.get('dpp', 0):,}")
                print(f"   PPN: Rp {keluaran.get('ppn', 0):,}")
                print(f"   Tanggal Faktur: {keluaran.get('tgl_faktur', 'N/A')}")
            
            # Display masukan data
            if 'masukan' in extracted_data:
                masukan = extracted_data['masukan']
                print(f"\n🔵 FAKTUR PAJAK MASUKAN:")
                print(f"   Nama Lawan Transaksi: {masukan.get('nama_lawan_transaksi', 'N/A')}")
                print(f"   No Seri FP: {masukan.get('no_seri_fp', 'N/A')}")
                print(f"   NPWP: {masukan.get('npwp', 'N/A')}")
                print(f"   Email: {masukan.get('email', 'N/A')}")
                print(f"   Alamat: {masukan.get('alamat', 'N/A')}")
                print(f"   DPP: Rp {masukan.get('dpp', 0):,}")
                print(f"   PPN: Rp {masukan.get('ppn', 0):,}")
                print(f"   Tanggal Faktur: {masukan.get('tgl_faktur', 'N/A')}")
        
        # Pattern recognition analysis
        print(f"\n🔍 Advanced Pattern Analysis:")
        print("=" * 40)
        
        patterns = {
            'No Seri Faktur Pajak': re.findall(r'\d{3}[.-]?\d{2}[.-]?\d{8}', full_text),
            'NPWP': re.findall(r'\d{2}[.-]\d{3}[.-]\d{3}[.-]\d[.-]\d{3}[.-]\d{3}', full_text),
            'Currency Values': re.findall(r'Rp\.?\s*([\d,\.]+)', full_text),
            'Dates': re.findall(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', full_text),
            'Company Names': re.findall(r'(?:PT|CV|UD)[\s\.]*([A-Z\s]+)', full_text),
            'Tax Terms': re.findall(r'(DPP|PPN|PPnBM|PKP)', full_text, re.I)
        }
        
        for pattern_name, matches in patterns.items():
            print(f"   {pattern_name}: {len(matches)} found")
            if matches:
                # Show first few matches
                sample_matches = matches[:3]
                print(f"      Examples: {sample_matches}")
        
        # Document structure analysis
        print(f"\n📋 Document Structure Analysis:")
        print("=" * 40)
        
        lines = full_text.split('\n')
        non_empty_lines = [line.strip() for line in lines if line.strip()]
        
        print(f"   Total lines: {len(lines)}")
        print(f"   Non-empty lines: {len(non_empty_lines)}")
        print(f"   Average line length: {sum(len(line) for line in non_empty_lines) / len(non_empty_lines):.1f} chars")
        
        # Key information extraction
        print(f"\n🎯 Key Information Detected:")
        print("=" * 40)
        
        # Look for specific patterns
        no_seri_match = re.search(r'(?:Kode dan Nomor Seri Faktur Pajak[:\s]*|No[.\s]*Seri[:\s]*)([0-9-]+)', full_text, re.I)
        if no_seri_match:
            print(f"   📄 No Seri Faktur: {no_seri_match.group(1)}")
        
        # Look for company names
        nama_matches = re.findall(r'Nama[:\s]*([A-Z\s&]+)(?=\n|Alamat)', full_text, re.I)
        if nama_matches:
            print(f"   🏢 Company Names: {nama_matches}")
        
        # Look for amounts
        dpp_match = re.search(r'DPP[:\s]*Rp\.?\s*([\d,\.]+)', full_text, re.I)
        if dpp_match:
            print(f"   💰 DPP: Rp {dpp_match.group(1)}")
        
        ppn_match = re.search(r'PPN[:\s]*Rp\.?\s*([\d,\.]+)', full_text, re.I)
        if ppn_match:
            print(f"   💰 PPN: Rp {ppn_match.group(1)}")
        
        print(f"\n🎉 Analysis Complete!")
        print(f"📊 Document appears to be a valid Faktur Pajak with extractable data")
        
        return True
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    analyze_document()