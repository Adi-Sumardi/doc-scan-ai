"""
AI-based Bank Detector using Claude
Uses Claude AI to detect bank name from OCR result
More accurate and robust than keyword matching
"""

from typing import Dict, Any, Optional
import logging
import json
import os
from anthropic import Anthropic

logger = logging.getLogger(__name__)


class AIBankDetector:
    """
    AI-based bank detector using Claude API
    Analyzes first page of bank statement to identify the bank
    """

    # Map AI response to adapter codes
    BANK_CODE_MAPPING = {
        "MANDIRI": "MANDIRI_V2",  # Default to V2, will fallback to V1 if needed
        "BANK MANDIRI": "MANDIRI_V2",
        "PT BANK MANDIRI": "MANDIRI_V2",

        "BNI": "BNI_V2",  # Default to V2, will fallback to V1 if needed
        "BANK BNI": "BNI_V2",
        "PT BANK BNI": "BNI_V2",

        "BCA": "BCA",
        "BANK CENTRAL ASIA": "BCA",
        "PT BANK CENTRAL ASIA": "BCA",

        "BCA SYARIAH": "BCA_SYARIAH",
        "PT BANK BCA SYARIAH": "BCA_SYARIAH",

        "CIMB NIAGA": "CIMB_NIAGA",
        "CIMB": "CIMB_NIAGA",
        "PT BANK CIMB NIAGA": "CIMB_NIAGA",

        "BRI": "BRI",
        "BANK RAKYAT INDONESIA": "BRI",
        "PT BANK RAKYAT INDONESIA": "BRI",

        "PERMATA": "PERMATA",
        "BANK PERMATA": "PERMATA",
        "PT BANK PERMATA": "PERMATA",

        "OCBC": "OCBC",
        "OCBC NISP": "OCBC",
        "PT BANK OCBC NISP": "OCBC",

        "BSI": "BSI_SYARIAH",
        "BANK SYARIAH INDONESIA": "BSI_SYARIAH",
        "PT BANK SYARIAH INDONESIA": "BSI_SYARIAH",

        "MUFG": "MUFG",
        "BANK OF TOKYO MITSUBISHI UFJ": "MUFG",
        "PT BANK OF TOKYO MITSUBISHI UFJ": "MUFG",
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize AI detector with Claude API

        Args:
            api_key: Anthropic API key (if None, will use env var)
        """
        # Load API key from env var if not provided (same pattern as smart_mapper)
        if not api_key:
            api_key = os.getenv("CLAUDE_API_KEY")

        self.client = Anthropic(api_key=api_key) if api_key else Anthropic()
        self.model = "claude-sonnet-4-20250514"  # Use same model as Smart Mapper

    def detect(self, ocr_result: Dict[str, Any], verbose: bool = True) -> Optional[str]:
        """
        Detect bank from OCR result using AI

        Args:
            ocr_result: OCR result from Google Document AI
            verbose: Print detection messages

        Returns:
            Bank code (e.g., "CIMB_NIAGA", "BCA") or None if not detected
        """
        try:
            # Extract first page text for detection
            text = self._extract_first_page_text(ocr_result)

            if not text:
                logger.warning("No text found in OCR result for AI detection")
                return None

            # ✅ FIX: Use ONLY first 500 characters (header area) to avoid confusion from transaction details
            # CIMB files have "BCA (BANK CENTRAL A" appearing many times in transactions,
            # which confuses Claude if we send 2000 chars
            text_sample = text[:500]  # Reduced from 2000 to 500

            if verbose:
                logger.info(f"🤖 AI Bank Detection: Analyzing {len(text_sample)} characters...")
                # DEBUG: Show first 300 chars to understand what's being sent
                logger.info(f"📝 Text sample (first 300 chars):")
                logger.info(f"{text_sample[:300]}")

            # Call Claude API for detection
            bank_name = self._call_claude_detection(text_sample)

            if not bank_name:
                if verbose:
                    logger.warning("❌ AI Detection: No bank detected")
                return None

            # Map bank name to code
            bank_code = self._map_bank_name_to_code(bank_name)

            if verbose:
                logger.info(f"✅ AI Detection: {bank_name} → {bank_code}")

            return bank_code

        except Exception as e:
            logger.error(f"AI bank detection failed: {e}")
            return None

    def _extract_first_page_text(self, ocr_result: Dict[str, Any]) -> str:
        """
        Extract text from first page only (for fast detection)

        Args:
            ocr_result: OCR result dict

        Returns:
            First page text
        """
        # Try direct text field
        if 'text' in ocr_result:
            return ocr_result['text']

        # Try to extract from pages
        if 'pages' in ocr_result and len(ocr_result['pages']) > 0:
            first_page = ocr_result['pages'][0]

            # Try blocks
            if 'blocks' in first_page:
                blocks = [block.get('text', '') for block in first_page.get('blocks', [])]
                if blocks:
                    return '\n'.join(blocks)

            # Try paragraphs
            if 'paragraphs' in first_page:
                paragraphs = [para.get('text', '') for para in first_page.get('paragraphs', [])]
                if paragraphs:
                    return '\n'.join(paragraphs)

            # Try lines
            if 'lines' in first_page:
                lines = [line.get('text', '') for line in first_page.get('lines', [])]
                if lines:
                    return '\n'.join(lines)

        # Fallback: extract from document
        if 'document' in ocr_result and 'text' in ocr_result['document']:
            return ocr_result['document']['text']

        return ""

    def _call_claude_detection(self, text: str) -> Optional[str]:
        """
        Call Claude API to detect bank name

        Args:
            text: OCR text sample

        Returns:
            Bank name or None
        """
        # ✅ STRICT PROMPT: Force single-word output with explicit instructions to ignore transaction details
        prompt = f"""Analyze this Indonesian bank statement and return ONLY the bank name from the HEADER/TITLE.

Text sample:
{text}

CRITICAL RULES:
1. Look ONLY at the TOP/HEADER of the document for the bank name (usually in first 5-10 lines)
2. IGNORE bank names that appear in transaction descriptions (e.g., "Transfer to BCA", "From MANDIRI", "BCA (BANK CENTRAL A" in transactions)
3. The bank name is usually displayed prominently at the very top of the statement
4. Return ONLY the bank name (one or two words maximum)
5. Valid banks: BCA, MANDIRI, BNI, BRI, CIMB NIAGA, PERMATA, OCBC, BSI, MUFG
6. DO NOT write explanations, reasoning, or full sentences
7. If unsure, return: UNKNOWN

Examples:
- Header shows "CIMB NIAGA" → respond: CIMB NIAGA (ignore "BCA" in transaction details)
- Header shows "BANK CENTRAL ASIA" → respond: BCA (ignore "MANDIRI" in transaction details)
- Header shows "Bank Mandiri" → respond: MANDIRI (ignore "BCA" in transaction details)

Your response (bank name only):"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=20,  # ✅ REDUCED: Only need 1-2 words
                temperature=0,  # Deterministic
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Extract bank name from response
            bank_name = response.content[0].text.strip().upper()

            # ✅ SANITIZE: Remove common explanation prefixes
            prefixes_to_remove = [
                "BANK NAME:", "BANK:", "THE BANK IS", "THIS IS",
                "LOOKING AT", "BASED ON", "I CAN SEE", "THE STATEMENT"
            ]
            for prefix in prefixes_to_remove:
                if bank_name.startswith(prefix):
                    bank_name = bank_name.replace(prefix, "").strip()

            # ✅ EXTRACT: Take only first 1-3 words
            words = bank_name.split()
            if len(words) > 3:
                # Likely an explanation, try to extract bank name
                for known_bank in ["CIMB NIAGA", "BCA", "MANDIRI", "BNI", "BRI", "PERMATA", "OCBC", "BSI", "MUFG"]:
                    if known_bank in bank_name:
                        bank_name = known_bank
                        break
                else:
                    # Take first 2 words as fallback
                    bank_name = " ".join(words[:2])

            # Validate response
            if bank_name == "UNKNOWN" or not bank_name or len(bank_name) > 50:
                logger.warning(f"⚠️ AI returned invalid bank name: {bank_name}")
                return None

            logger.info(f"🤖 Claude detected bank: {bank_name}")
            return bank_name

        except Exception as e:
            logger.error(f"Claude API call failed: {e}")
            return None

    def _map_bank_name_to_code(self, bank_name: str) -> Optional[str]:
        """
        Map AI-detected bank name to adapter code

        Args:
            bank_name: Bank name from AI (e.g., "CIMB NIAGA", "BCA")

        Returns:
            Bank code (e.g., "CIMB_NIAGA", "BCA") or None
        """
        bank_name_upper = bank_name.upper().strip()

        # Direct match
        if bank_name_upper in self.BANK_CODE_MAPPING:
            return self.BANK_CODE_MAPPING[bank_name_upper]

        # Partial match (fuzzy)
        for key, code in self.BANK_CODE_MAPPING.items():
            if key in bank_name_upper or bank_name_upper in key:
                return code

        # No match found
        logger.warning(f"❌ Unknown bank name from AI: {bank_name}")
        return None