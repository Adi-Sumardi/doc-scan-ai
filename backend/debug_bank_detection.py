"""
Debug script untuk check kenapa bank detection gagal
Run this untuk diagnose detection issues
"""

import sys
import json
import logging
from bank_adapters.detector import BankDetector
from bank_adapters.ai_detector import AIBankDetector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def debug_detection(ocr_result_path: str):
    """
    Debug bank detection untuk OCR result file
    
    Args:
        ocr_result_path: Path ke OCR result JSON file
    """
    # Load OCR result
    try:
        with open(ocr_result_path, 'r', encoding='utf-8') as f:
            ocr_result = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load OCR result: {e}")
        return
    
    logger.info("=" * 80)
    logger.info("BANK DETECTION DEBUG")
    logger.info("=" * 80)
    
    # 1. Extract text
    text = BankDetector._extract_text(ocr_result)
    logger.info(f"\n📄 OCR Text Length: {len(text)} characters")
    logger.info(f"\n📝 First 500 characters:")
    logger.info(text[:500])
    logger.info("\n" + "=" * 80)
    
    # 2. Test keyword detection
    logger.info("\n🔍 KEYWORD DETECTION TEST:")
    logger.info("=" * 80)
    detection_result = BankDetector.test_detection(ocr_result)
    
    logger.info(f"\n✅ Detected Bank: {detection_result['detected_bank']}")
    logger.info(f"\n📊 Detection Scores (Top 5):")
    for i, score in enumerate(detection_result['detection_scores'][:5], 1):
        logger.info(f"\n{i}. {score['bank_name']} ({score['bank_code']})")
        logger.info(f"   Match: {score['keyword_matches']}/{score['total_keywords']} ({score['match_percentage']:.1f}%)")
        logger.info(f"   Detected: {'✅ YES' if score['is_detected'] else '❌ NO'}")
        if score['matched_keywords']:
            logger.info(f"   Keywords found: {', '.join(score['matched_keywords'][:5])}")
    
    # 3. Test AI detection
    logger.info("\n" + "=" * 80)
    logger.info("\n🤖 AI DETECTION TEST:")
    logger.info("=" * 80)
    try:
        ai_detector = AIBankDetector()
        ai_result = ai_detector.detect(ocr_result, verbose=True)
        logger.info(f"\n✅ AI Detected: {ai_result}")
    except Exception as e:
        logger.error(f"\n❌ AI Detection failed: {e}")
    
    # 4. Check table structure
    logger.info("\n" + "=" * 80)
    logger.info("\n📊 TABLE STRUCTURE:")
    logger.info("=" * 80)
    
    if 'tables' in ocr_result:
        tables = ocr_result['tables']
        logger.info(f"\nTotal tables found: {len(tables)}")
        
        for idx, table in enumerate(tables[:3], 1):  # Show first 3 tables
            rows = table.get('rows', [])
            logger.info(f"\nTable {idx}:")
            logger.info(f"  Rows: {len(rows)}")
            
            if rows:
                # Show first row structure
                first_row_cells = rows[0].get('cells', [])
                logger.info(f"  Columns in first row: {len(first_row_cells)}")
                
                # Show first row content
                logger.info(f"  First row content:")
                for cell_idx, cell in enumerate(first_row_cells[:10], 1):  # First 10 cells
                    cell_text = cell.get('text', '').strip()
                    logger.info(f"    Cell {cell_idx}: {cell_text}")
                
                # Check if rows have consistent column count
                col_counts = [len(row.get('cells', [])) for row in rows[:5]]
                logger.info(f"  Column count pattern (first 5 rows): {col_counts}")
    else:
        logger.info("\n❌ No tables found in OCR result")
    
    logger.info("\n" + "=" * 80)
    logger.info("DEBUG COMPLETE")
    logger.info("=" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_bank_detection.py <path_to_ocr_result.json>")
        sys.exit(1)
    
    debug_detection(sys.argv[1])
