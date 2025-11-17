"""
Bank Detector - Auto-detect bank dari OCR result
Mencoba setiap adapter sampai menemukan yang cocok
"""

from typing import Optional, Dict, Any, List
from .base import BaseBankAdapter
from .mandiri_v1 import MandiriV1Adapter
from .mandiri_v2 import MandiriV2Adapter
from .mufg import MufgBankAdapter
from .permata import PermataBankAdapter
from .bni_v1 import BniV1Adapter
from .bni_v2 import BniV2Adapter
from .bri import BriAdapter
from .bca import BcaAdapter
from .bca_syariah import BcaSyariahAdapter
from .ocbc import OcbcBankAdapter
from .bsi_syariah import BsiSyariahAdapter
from .cimb_niaga import CimbNiagaAdapter


class BankDetector:
    """
    Auto-detect bank dari OCR result menggunakan keywords matching
    """

    # Registry semua adapters
    # PENTING: ORDER MATTERS! Yang lebih spesifik harus di-check dulu
    ADAPTERS = [
        # Mandiri V2 sebelum V1 (V2 punya keywords lebih spesifik)
        MandiriV2Adapter,
        MandiriV1Adapter,

        # BNI V2 sebelum V1 (V2 punya keywords lebih spesifik)
        BniV2Adapter,
        BniV1Adapter,

        # BCA Syariah sebelum BCA reguler (Syariah lebih spesifik)
        BcaSyariahAdapter,
        BcaAdapter,

        # Bank lain (tidak ada konflik keywords)
        CimbNiagaAdapter,
        MufgBankAdapter,
        PermataBankAdapter,
        BriAdapter,
        OcbcBankAdapter,
        BsiSyariahAdapter,
    ]

    @classmethod
    def detect(cls, ocr_result: Dict[str, Any], verbose: bool = True) -> Optional[BaseBankAdapter]:
        """
        Auto-detect bank dan return adapter yang sesuai

        Args:
            ocr_result: Raw OCR result dari Google Document AI
            verbose: Print detection messages

        Returns:
            Instance of specific BankAdapter atau None jika tidak terdeteksi
        """
        # Extract text untuk detection
        text = cls._extract_text(ocr_result)

        if verbose:
            print(f"\n🔍 Detecting bank from OCR text ({len(text)} characters)...")

        # Try setiap adapter
        for adapter_class in cls.ADAPTERS:
            adapter = adapter_class()

            if adapter.detect(text):
                if verbose:
                    print(f"✓ Detected: {adapter.BANK_NAME} ({adapter.BANK_CODE})")
                    print(f"  Keywords matched: {adapter.DETECTION_KEYWORDS[:3]}")
                return adapter

        if verbose:
            print("✗ Bank tidak terdeteksi!")
            print("  Supported banks:")
            for adapter_class in cls.ADAPTERS:
                adapter = adapter_class()
                print(f"    - {adapter.BANK_NAME} ({adapter.BANK_CODE})")

        return None

    @classmethod
    def detect_bank_name(cls, ocr_result: Dict[str, Any]) -> str:
        """
        Quick detect bank name saja (untuk logging/display)

        Args:
            ocr_result: Raw OCR result

        Returns:
            Bank name atau "Unknown Bank"
        """
        adapter = cls.detect(ocr_result, verbose=False)
        return adapter.BANK_NAME if adapter else "Unknown Bank"

    @classmethod
    def detect_bank_code(cls, ocr_result: Dict[str, Any]) -> str:
        """
        Quick detect bank code saja

        Args:
            ocr_result: Raw OCR result

        Returns:
            Bank code atau "UNKNOWN"
        """
        adapter = cls.detect(ocr_result, verbose=False)
        return adapter.BANK_CODE if adapter else "UNKNOWN"

    @classmethod
    def _extract_text(cls, ocr_result: Dict[str, Any]) -> str:
        """
        Extract full text dari OCR result untuk detection

        Args:
            ocr_result: OCR result dict

        Returns:
            Full text string
        """
        # Try direct text field
        if 'text' in ocr_result:
            return ocr_result['text']

        # Try to extract from pages
        text_parts = []

        if 'pages' in ocr_result:
            for page in ocr_result.get('pages', []):
                # Try blocks
                if 'blocks' in page:
                    for block in page.get('blocks', []):
                        if 'text' in block:
                            text_parts.append(block['text'])

                # Try paragraphs
                if 'paragraphs' in page:
                    for para in page.get('paragraphs', []):
                        if 'text' in para:
                            text_parts.append(para['text'])

                # Try lines (last resort)
                if 'lines' in page and not text_parts:
                    for line in page.get('lines', []):
                        if 'text' in line:
                            text_parts.append(line['text'])

        # Try document level
        if 'document' in ocr_result and not text_parts:
            doc = ocr_result['document']
            if 'text' in doc:
                return doc['text']

        return '\n'.join(text_parts)

    @classmethod
    def get_supported_banks(cls) -> List[Dict[str, Any]]:
        """
        Get list of supported banks dengan detail

        Returns:
            List of dict dengan bank info
        """
        banks = []

        for adapter_class in cls.ADAPTERS:
            adapter = adapter_class()
            banks.append({
                'code': adapter.BANK_CODE,
                'name': adapter.BANK_NAME,
                'keywords': adapter.DETECTION_KEYWORDS,
            })

        return banks

    @classmethod
    def get_adapter_by_code(cls, bank_code: str) -> Optional[BaseBankAdapter]:
        """
        Get adapter by bank code (untuk manual selection)

        Args:
            bank_code: Bank code (e.g., "MANDIRI_V1", "BNI_V2")

        Returns:
            Instance of BankAdapter atau None
        """
        bank_code_upper = bank_code.upper()

        for adapter_class in cls.ADAPTERS:
            adapter = adapter_class()
            if adapter.BANK_CODE == bank_code_upper:
                return adapter

        return None

    @classmethod
    def test_detection(cls, ocr_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test detection dan return detailed info (untuk debugging)

        Args:
            ocr_result: OCR result

        Returns:
            Dict dengan detection results
        """
        text = cls._extract_text(ocr_result)

        results = {
            'text_length': len(text),
            'text_preview': text[:500] + '...' if len(text) > 500 else text,
            'detected_bank': None,
            'detection_scores': [],
        }

        # Try semua adapters dan calculate score
        for adapter_class in cls.ADAPTERS:
            adapter = adapter_class()

            # Count keyword matches
            keyword_matches = 0
            matched_keywords = []

            for keyword in adapter.DETECTION_KEYWORDS:
                if keyword.upper() in text.upper():
                    keyword_matches += 1
                    matched_keywords.append(keyword)

            score = {
                'bank_name': adapter.BANK_NAME,
                'bank_code': adapter.BANK_CODE,
                'keyword_matches': keyword_matches,
                'total_keywords': len(adapter.DETECTION_KEYWORDS),
                'match_percentage': (keyword_matches / len(adapter.DETECTION_KEYWORDS)) * 100 if adapter.DETECTION_KEYWORDS else 0,
                'matched_keywords': matched_keywords,
                'is_detected': adapter.detect(text),
            }

            results['detection_scores'].append(score)

            # Set detected bank (first match)
            if score['is_detected'] and results['detected_bank'] is None:
                results['detected_bank'] = {
                    'name': adapter.BANK_NAME,
                    'code': adapter.BANK_CODE,
                }

        # Sort by match percentage
        results['detection_scores'].sort(key=lambda x: x['match_percentage'], reverse=True)

        return results
