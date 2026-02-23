"""
OCR Processor Module - Hybrid Version
Primary: Surya OCR (free, local)
Fallback: Google Document AI (paid, cloud)
Smart Mapper GPT handles field extraction from raw OCR text
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# OCR Engine configuration
# Options: surya_primary, google_primary, surya_only, google_only
OCR_ENGINE_MODE = os.environ.get('OCR_ENGINE_MODE', 'surya_primary')

# Surya OCR availability — defer heavy import to first use
HAS_SURYA = False
try:
    import importlib
    _surya_spec = importlib.util.find_spec("surya_processor")
    if _surya_spec is not None:
        HAS_SURYA = True
        logger.info("Surya OCR available (deferred loading)")
except Exception:
    pass
if not HAS_SURYA:
    logger.warning("Surya OCR not available (pip install surya-ocr)")

# Try to import Google Document AI (paid, cloud)
try:
    from cloud_ai_processor import CloudAIProcessor
    HAS_CLOUD_AI = True
    logger.info("Google Document AI available")
except ImportError:
    HAS_CLOUD_AI = False
    logger.warning("Google Document AI not available")


class RealOCRProcessor:
    """Hybrid OCR processor: Surya OCR (free, primary) + Google DocAI (paid, fallback)

    Engine modes:
    - surya_primary: Try Surya first, fallback to Google (default)
    - google_primary: Try Google first, fallback to Surya
    - surya_only: Only use Surya (100% free)
    - google_only: Only use Google (current behavior)
    """

    def __init__(self):
        self.initialized = False
        self._last_ocr_result = None
        self.surya_processor = None
        self.cloud_processor = None

        self._surya_needed = OCR_ENGINE_MODE in ('surya_primary', 'surya_only', 'google_primary') and HAS_SURYA

        logger.info(f"OCR Engine Mode: {OCR_ENGINE_MODE}")

        if self._surya_needed:
            logger.info("Surya OCR initialized (deferred — models load on first OCR request)")

        # Initialize Google Document AI if needed
        if OCR_ENGINE_MODE in ('surya_primary', 'google_primary', 'google_only') and HAS_CLOUD_AI:
            try:
                self.cloud_processor = CloudAIProcessor()
                logger.info("Google Document AI initialized (FALLBACK)" if OCR_ENGINE_MODE == 'surya_primary'
                            else "Google Document AI initialized")
            except Exception as e:
                logger.error(f"Google Document AI init failed: {e}", exc_info=True)

        self.initialized = (
            self._surya_needed or
            self.cloud_processor is not None
        )

        if not self.initialized:
            logger.critical("No OCR engine available! System cannot function.")
            logger.critical("Install surya-ocr (pip install surya-ocr) or configure Google Document AI")

    def _get_surya(self):
        """Lazy-load SuryaProcessor on first OCR request"""
        if self.surya_processor is None and self._surya_needed:
            try:
                from surya_processor import SuryaProcessor
                self.surya_processor = SuryaProcessor()
                logger.info("Surya OCR processor created on first use")
            except Exception as e:
                logger.error(f"Surya OCR init failed: {e}", exc_info=True)
                self._surya_needed = False
        return self.surya_processor

    async def extract_text(self, file_path: str) -> str:
        """Extract text with hybrid engine (try primary, fallback to secondary)"""
        if not self.initialized:
            logger.error("No OCR engine initialized")
            return ""

        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return ""

        file_ext = Path(file_path).suffix.lower()

        # Determine engine order based on mode (Surya loaded lazily on first use)
        if OCR_ENGINE_MODE == 'surya_primary':
            engines = [
                ('surya', self._get_surya),
                ('google', lambda: self.cloud_processor),
            ]
        elif OCR_ENGINE_MODE == 'google_primary':
            engines = [
                ('google', lambda: self.cloud_processor),
                ('surya', self._get_surya),
            ]
        elif OCR_ENGINE_MODE == 'surya_only':
            engines = [('surya', self._get_surya)]
        else:  # google_only
            engines = [('google', lambda: self.cloud_processor)]

        # Try engines in order
        for engine_name, engine_getter in engines:
            engine = engine_getter()
            if engine is None:
                continue

            try:
                logger.info(f"Processing {file_ext} file with {engine_name}: {file_path}")

                if engine_name == 'surya':
                    result = await engine.process_document(file_path)
                else:
                    result = await engine.process_with_google(file_path)

                if result and result.raw_text:
                    logger.info(
                        f"{engine_name} OCR success: "
                        f"{len(result.raw_text)} chars, "
                        f"{result.confidence:.1f}% confidence"
                    )

                    self._last_ocr_result = {
                        'text': result.raw_text,
                        'extracted_fields': result.extracted_fields,
                        'confidence': result.confidence,
                        'engine_used': result.service_used,
                        'quality_score': result.confidence,
                        'processing_time': result.processing_time,
                        'raw_response': result.raw_response,
                    }
                    return result.raw_text
                else:
                    logger.warning(f"{engine_name} returned no text, trying next engine...")

            except Exception as e:
                logger.error(f"{engine_name} OCR failed: {e}", exc_info=True)
                continue

        logger.error("All OCR engines failed - no text extracted")
        return ""

    def get_last_ocr_metadata(self) -> Optional[Dict[str, Any]]:
        """Get metadata from the last OCR operation"""
        return self._last_ocr_result

    def get_ocr_system_info(self) -> Dict[str, Any]:
        """Get information about OCR system"""
        return {
            'engine_mode': OCR_ENGINE_MODE,
            'surya_available': self._surya_needed or self.surya_processor is not None,
            'google_available': self.cloud_processor is not None,
            'initialized': self.initialized,
            'smart_mapper_enabled': True,
        }
