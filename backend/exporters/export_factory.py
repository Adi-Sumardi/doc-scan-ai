"""
Export Factory
Registry for all document-specific exporters
Uses Factory Pattern to automatically select the correct exporter based on document type
"""

from typing import Optional
import logging

from .base_exporter import BaseExporter
from .faktur_pajak_exporter import FakturPajakExporter
from .pph21_exporter import PPh21Exporter
from .pph23_exporter import PPh23Exporter
from .rekening_koran_exporter import RekeningKoranExporter
from .invoice_exporter import InvoiceExporter

logger = logging.getLogger(__name__)

from typing import Optional
import logging

from .base_exporter import BaseExporter
from .faktur_pajak_exporter import FakturPajakExporter

logger = logging.getLogger(__name__)


class ExportFactory:
    """Factory for creating document-specific exporters"""
    
    # Registry of document types to exporter classes
    _exporters = {
        # Faktur Pajak
        "faktur_pajak": FakturPajakExporter,
        "faktur pajak": FakturPajakExporter,
        "tax invoice": FakturPajakExporter,
        
        # PPh21
        "pph21": PPh21Exporter,
        "pph 21": PPh21Exporter,
        "employee tax": PPh21Exporter,
        
        # PPh23
        "pph23": PPh23Exporter,
        "pph 23": PPh23Exporter,
        "service tax": PPh23Exporter,
        "tax on services": PPh23Exporter,
        
        # Rekening Koran
        "rekening_koran": RekeningKoranExporter,
        "rekening koran": RekeningKoranExporter,
        "bank statement": RekeningKoranExporter,
        "account statement": RekeningKoranExporter,
        
        # Invoice
        "invoice": InvoiceExporter,
        "tagihan": InvoiceExporter,
        "bill": InvoiceExporter,
    }
    
    @classmethod
    def get_exporter(cls, document_type: str) -> Optional[BaseExporter]:
        """
        Get appropriate exporter instance for document type
        
        Args:
            document_type: Type of document (e.g., "faktur_pajak", "pph21")
            
        Returns:
            BaseExporter instance or None if no exporter found
        """
        # Normalize document type (lowercase, strip whitespace)
        normalized_type = document_type.lower().strip()
        
        # Get exporter class from registry
        exporter_class = cls._exporters.get(normalized_type)
        
        if exporter_class:
            logger.info(f"✅ Found exporter for document type: {document_type}")
            return exporter_class()
        else:
            logger.warning(f"⚠️ No exporter found for document type: {document_type}")
            # Return default Faktur Pajak exporter as fallback
            logger.info("Using Faktur Pajak exporter as fallback")
            return FakturPajakExporter()
    
    @classmethod
    def register_exporter(cls, document_type: str, exporter_class):
        """
        Register a new exporter for a document type
        
        Args:
            document_type: Type of document
            exporter_class: Exporter class (must inherit from BaseExporter)
        """
        if not issubclass(exporter_class, BaseExporter):
            raise ValueError(f"Exporter class must inherit from BaseExporter")
        
        normalized_type = document_type.lower().strip()
        cls._exporters[normalized_type] = exporter_class
        logger.info(f"✅ Registered exporter for document type: {document_type}")
    
    @classmethod
    def list_supported_types(cls) -> list:
        """Get list of supported document types"""
        return list(cls._exporters.keys())
