"""
Base Exporter Class
Abstract base class for all document exporters
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class BaseExporter(ABC):
    """Base class for document exporters"""
    
    def __init__(self, document_type: str):
        self.document_type = document_type
    
    @abstractmethod
    def export_to_excel(self, result: Dict[str, Any], output_path: str) -> bool:
        """
        Export document data to Excel format
        
        Args:
            result: Dictionary containing document data
            output_path: Path where Excel file will be saved
            
        Returns:
            bool: True if export successful, False otherwise
        """
        pass
    
    @abstractmethod
    def export_to_pdf(self, result: Dict[str, Any], output_path: str) -> bool:
        """
        Export document data to PDF format
        
        Args:
            result: Dictionary containing document data
            output_path: Path where PDF file will be saved
            
        Returns:
            bool: True if export successful, False otherwise
        """
        pass
    
    @abstractmethod
    def batch_export_to_excel(self, batch_id: str, results: list, output_path: str) -> bool:
        """
        Export multiple documents to single Excel file
        
        Args:
            batch_id: Unique identifier for the batch
            results: List of document result dictionaries
            output_path: Path where Excel file will be saved
            
        Returns:
            bool: True if export successful, False otherwise
        """
        pass
    
    @abstractmethod
    def batch_export_to_pdf(self, batch_id: str, results: list, output_path: str) -> bool:
        """
        Export multiple documents to single PDF file
        
        Args:
            batch_id: Unique identifier for the batch
            results: List of document result dictionaries
            output_path: Path where PDF file will be saved
            
        Returns:
            bool: True if export successful, False otherwise
        """
        pass
