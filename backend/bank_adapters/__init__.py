"""
Bank Adapters untuk Multi-Bank Support
Setiap bank punya format rekening koran yang berbeda
Adapter ini standardize semua format ke output yang sama

Supported Banks:
1. Bank Mandiri V1 & V2
2. MUFG Bank
3. Permata Bank
4. BNI V1 & V2
5. BRI
6. BCA (Bank Central Asia)
7. BCA Syariah
8. OCBC Bank
9. BSI (Bank Syariah Indonesia)

Total: 11 bank adapters (9 unique banks)

Usage:
    from bank_adapters import BankDetector

    # Auto-detect bank
    adapter = BankDetector.detect(ocr_result)
    if adapter:
        transactions = adapter.parse(ocr_result)
        excel_data = adapter.to_excel_format()
"""

from .base import BaseBankAdapter, StandardizedTransaction
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
from .detector import BankDetector

__all__ = [
    # Base classes
    'BaseBankAdapter',
    'StandardizedTransaction',

    # Bank adapters
    'MandiriV1Adapter',
    'MandiriV2Adapter',
    'MufgBankAdapter',
    'PermataBankAdapter',
    'BniV1Adapter',
    'BniV2Adapter',
    'BriAdapter',
    'BcaAdapter',
    'BcaSyariahAdapter',
    'OcbcBankAdapter',
    'BsiSyariahAdapter',

    # Detector
    'BankDetector',
]

# Quick access functions
def detect_bank(ocr_result):
    """Quick function to detect bank"""
    return BankDetector.detect(ocr_result)

def get_supported_banks():
    """Quick function to get supported banks list"""
    return BankDetector.get_supported_banks()

def process_bank_statement(ocr_result, bank_code=None):
    """
    Quick function to process bank statement

    Args:
        ocr_result: OCR result dict
        bank_code: Optional bank code untuk manual selection

    Returns:
        Dict dengan transactions dan summary
    """
    # Get adapter
    if bank_code:
        adapter = BankDetector.get_adapter_by_code(bank_code)
        if not adapter:
            return {
                'success': False,
                'error': f'Invalid bank code: {bank_code}',
                'supported_banks': get_supported_banks(),
            }
    else:
        adapter = BankDetector.detect(ocr_result)
        if not adapter:
            return {
                'success': False,
                'error': 'Bank tidak terdeteksi',
                'supported_banks': get_supported_banks(),
            }

    # Parse transactions
    try:
        transactions = adapter.parse(ocr_result)
        summary = adapter.get_summary()
        excel_data = adapter.to_excel_format()

        return {
            'success': True,
            'bank_name': adapter.BANK_NAME,
            'bank_code': adapter.BANK_CODE,
            'summary': summary,
            'transactions': excel_data,
            'transaction_objects': transactions,
        }

    except Exception as e:
        return {
            'success': False,
            'error': f'Error parsing {adapter.BANK_NAME}: {str(e)}',
        }
