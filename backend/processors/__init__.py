"""
Processors Module
Advanced bank statement processing with hybrid approach

Components:
- RuleBasedTransactionParser: Parse 90% without GPT (token savings!)
- ProgressiveValidator: Validate and determine GPT need
- HybridBankProcessor: Orchestrate hybrid pipeline

Strategy: Structured First + Progressive Validation
Expected Savings: 90-96% token reduction
"""

from .rule_based_parser import RuleBasedTransactionParser, ParsedTransaction
from .progressive_validator import (
    ProgressiveValidator,
    ValidationResult,
    ChunkValidation
)
from .hybrid_bank_processor import HybridBankProcessor

__all__ = [
    'RuleBasedTransactionParser',
    'ParsedTransaction',
    'ProgressiveValidator',
    'ValidationResult',
    'ChunkValidation',
    'HybridBankProcessor',
]
