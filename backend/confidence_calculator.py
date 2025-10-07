"""
Confidence Calculator Module
Handles document type detection and confidence scoring
"""

import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def detect_document_type_from_filename(filename: str) -> str:
    """Detect document type from filename patterns"""
    filename_lower = filename.lower()
    
    if 'faktur' in filename_lower or 'pajak' in filename_lower:
        return 'faktur_pajak'
    elif 'pph21' in filename_lower or 'pph_21' in filename_lower:
        return 'pph21'
    elif 'pph23' in filename_lower or 'pph_23' in filename_lower:
        return 'pph23'
    elif 'rekening' in filename_lower or 'koran' in filename_lower:
        return 'rekening_koran'
    elif 'invoice' in filename_lower or 'tagihan' in filename_lower:
        return 'invoice'
    else:
        # Default to faktur_pajak for unknown types
        return 'faktur_pajak'


def calculate_confidence(raw_text: str, document_type: str) -> float:
    """
    Calculate confidence score based on raw OCR text quality.
    
    Args:
        raw_text: Raw OCR text extracted from document
        document_type: Type of document (faktur_pajak, pph21, pph23, rekening_koran, invoice)
    
    Returns:
        Confidence score between 0.0 and 1.0
    """
    try:
        if not raw_text:
            return 0.0
            
        character_count = len(raw_text)
        line_count = len(raw_text.split('\n'))
        
        # Base confidence on text length and structure
        if character_count == 0:
            return 0.1
        
        # Text length factor
        if character_count >= 1500:
            length_confidence = 0.9
        elif character_count >= 1000:
            length_confidence = 0.8
        elif character_count >= 500:
            length_confidence = 0.7
        elif character_count >= 200:
            length_confidence = 0.6
        elif character_count >= 100:
            length_confidence = 0.4
        else:
            length_confidence = 0.2
        
        # Line structure factor (more lines usually means better OCR)
        if line_count >= 20:
            structure_confidence = 0.9
        elif line_count >= 10:
            structure_confidence = 0.8
        elif line_count >= 5:
            structure_confidence = 0.7
        elif line_count >= 2:
            structure_confidence = 0.5
        else:
            structure_confidence = 0.3
        
        # Check for document-specific keywords to boost confidence
        text_lower = raw_text.lower()
        keyword_bonus = 0.0
        
        if document_type == 'faktur_pajak':
            faktur_keywords = ['faktur', 'pajak', 'npwp', 'ppn', 'dpp']
            found_keywords = sum(1 for keyword in faktur_keywords if keyword in text_lower[:1000])  # Check first 1000 chars
            keyword_bonus = min(found_keywords * 0.05, 0.15)
        elif document_type in ['pph21', 'pph23']:
            pph_keywords = ['pph', 'bukti', 'potong', 'npwp', 'masa']
            found_keywords = sum(1 for keyword in pph_keywords if keyword in text_lower[:1000])
            keyword_bonus = min(found_keywords * 0.05, 0.15)
        elif document_type == 'rekening_koran':
            rekening_keywords = ['saldo', 'debit', 'kredit', 'transaksi', 'tanggal']
            found_keywords = sum(1 for keyword in rekening_keywords if keyword in text_lower[:1000])
            keyword_bonus = min(found_keywords * 0.05, 0.15)
        elif document_type == 'invoice':
            invoice_keywords = ['invoice', 'total', 'amount', 'date', 'vendor']
            found_keywords = sum(1 for keyword in invoice_keywords if keyword in text_lower[:1000])
            keyword_bonus = min(found_keywords * 0.05, 0.15)
        
        # Combine factors
        final_confidence = (length_confidence * 0.5) + (structure_confidence * 0.3) + (keyword_bonus * 0.2)
        
        # Ensure reasonable bounds
        return max(0.1, min(0.99, final_confidence))
        
    except Exception as e:
        logger.error(f"❌ Confidence calculation failed: {e}")
        return 0.3  # Default confidence if calculation fails


def validate_extracted_data(extracted_data: Dict[str, Any], document_type: str) -> bool:
    """
    Validate if extracted data meets minimum quality requirements
    
    Args:
        extracted_data: Parsed document data
        document_type: Type of document
    
    Returns:
        True if data is valid, False otherwise
    """
    try:
        if not isinstance(extracted_data, dict):
            return False
        
        # Check if any section has meaningful data
        has_meaningful_data = False
        for section_key, section_data in extracted_data.items():
            if isinstance(section_data, dict) and any(v for v in section_data.values() if v):
                has_meaningful_data = True
                break
        
        return has_meaningful_data
        
    except Exception as e:
        logger.error(f"❌ Data validation failed: {e}")
        return False
