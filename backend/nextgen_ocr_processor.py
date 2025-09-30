#!/usr/bin/env python3
"""
Next-Generation OCR Processor
Clean implementation with RapidOCR and EasyOCR
"""

import os
import cv2
import numpy as np
import logging
from typing import Dict
from dataclasses import dataclass
from datetime import datetime
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class NextGenOCRResult:
    text: str
    confidence: float
    engine_used: str
    processing_time: float
    quality_score: float

class NextGenerationOCRProcessor:
    def __init__(self):
        self.engines = {}
        self.preprocessor = None
        self._init_engines()
        logger.info("🚀 Next-Generation OCR Processor initialized")
    
    def _init_engines(self):
        # RapidOCR
        try:
            from rapidocr_onnxruntime import RapidOCR
            self.engines['rapid'] = RapidOCR()
            logger.info("✅ RapidOCR loaded")
        except ImportError as e:
            logger.warning(f"⚠️ RapidOCR not available: {e}")
        
        # EasyOCR
        try:
            import easyocr
            self.engines['easy'] = easyocr.Reader(['en', 'id'], gpu=False)
            logger.info("✅ EasyOCR loaded")
        except ImportError as e:
            logger.warning(f"⚠️ EasyOCR not available: {e}")
        
        # Advanced preprocessor
        try:
            from super_advanced_preprocessor import SuperAdvancedPreprocessor
            self.preprocessor = SuperAdvancedPreprocessor()
            logger.info("✅ Advanced Preprocessor loaded")
        except Exception as e:
            logger.warning(f"⚠️ Advanced Preprocessor not available: {e}")
    
    def process_document_nextgen(self, file_path: str, doc_type: str = "unknown"):
        start_time = datetime.now()
        
        try:
            # Validate file exists
            if not os.path.exists(file_path):
                logger.error(f"❌ File not found: {file_path}")
                raise FileNotFoundError(f"File not found: {file_path}")

            # Check file permissions
            if not os.access(file_path, os.R_OK):
                logger.error(f"❌ No read permission for file: {file_path}")
                raise PermissionError(f"Cannot read file: {file_path}")

            # Check file type
            import magic
            file_type = magic.from_file(file_path)
            logger.info(f"📄 File type detected: {file_type}")

            # Log processing start with detailed info
            logger.info(f"🔄 Processing document: {file_path}")
            logger.info(f"📋 Document type: {doc_type}")
            logger.info(f"📊 File size: {os.path.getsize(file_path)} bytes")
            
            # Detailed preprocessing logging
            logger.info("🔍 Starting image preprocessing...")
            processed_image = self._preprocess_image(file_path, doc_type)
            if processed_image is None:
                raise ValueError("Image preprocessing returned None")
            if not hasattr(processed_image, 'size') or processed_image.size == 0:
                raise ValueError(f"Invalid processed image: {type(processed_image)}")
            logger.info("✅ Preprocessing completed successfully")

            # Detailed OCR logging
            logger.info("🔍 Starting OCR processing...")
            results = self._run_ensemble_ocr(processed_image)
            if not results:
                raise ValueError("OCR returned no results dictionary")
            if 'text' not in results:
                raise ValueError(f"OCR results missing 'text' key. Keys found: {list(results.keys())}")
            if not results['text'].strip():
                raise ValueError("OCR returned empty text")
            logger.info(f"📝 OCR extracted {len(results['text'].split())} words")

            quality_score = self._calculate_quality(results)
            logger.info(f"📊 Quality score: {quality_score}")
            
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"⏱️ Processing time: {processing_time:.2f}s")
            
            # Log successful processing with details
            logger.info(f"✅ Successfully processed {file_path}")
            logger.info(f"📊 Confidence: {results.get('confidence', 0.0)}")
            logger.info(f"🔧 Engine used: {results.get('engine', 'unknown')}")
            
            result = NextGenOCRResult(
                text=results['text'],
                confidence=results.get('confidence', 0.0),
                engine_used=results.get('engine', 'unknown'),
                processing_time=processing_time,
                quality_score=quality_score
            )

            # Validate result
            if not result.text.strip():
                logger.warning(f"⚠️ No text extracted from {file_path}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Processing failed for {file_path}: {str(e)}", exc_info=True)
            return NextGenOCRResult("", 0.0, f"Error: {str(e)}", 0.0, 0.0)
    
    def _preprocess_image(self, file_path: str, doc_type: str):
        try:
            if file_path.lower().endswith('.pdf'):
                try:
                    from pdf2image import convert_from_path
                    images = convert_from_path(file_path, dpi=300, first_page=1, last_page=1)
                    image = np.array(images[0])
                    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                except Exception as e:
                    logger.error(f"PDF conversion failed: {e}")
                    return np.ones((800, 600), dtype=np.uint8) * 255
            else:
                image = cv2.imread(file_path)
                if image is None:
                    return np.ones((800, 600), dtype=np.uint8) * 255
            
            if self.preprocessor:
                return self.preprocessor.preprocess_super_advanced(image, doc_type)
            else:
                if len(image.shape) == 3:
                    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                return image
                
        except Exception as e:
            logger.error(f"❌ Preprocessing failed: {e}")
            return np.ones((800, 600), dtype=np.uint8) * 255
    
    def _run_ensemble_ocr(self, image):
        results = []
        
        for engine_name in self.engines.keys():
            try:
                result = self._run_single_engine(engine_name, image)
                if result['text']:
                    results.append(result)
                    logger.info(f"✅ {engine_name}: {result['confidence']:.1f}%")
            except Exception as e:
                logger.error(f"❌ Engine {engine_name} failed: {e}")
        
        if results:
            return self._select_best_result(results)
        else:
            return {'text': '', 'confidence': 0.0, 'engine': 'None'}
    
    def _run_single_engine(self, engine_name: str, image):
        if engine_name == 'rapid':
            result = self.engines['rapid'](image)
            if result and result[0]:
                text = ' '.join([item[1] for item in result[0] if item[1]])
                avg_conf = np.mean([item[2] for item in result[0] if item[2]])
                return {'text': text, 'confidence': avg_conf * 100, 'engine': 'rapid'}
        
        elif engine_name == 'easy':
            result = self.engines['easy'].readtext(image)
            if result:
                text = ' '.join([item[1] for item in result if item[1]])
                avg_conf = np.mean([item[2] for item in result if item[2]])
                return {'text': text, 'confidence': avg_conf * 100, 'engine': 'easy'}
        
        return {'text': '', 'confidence': 0.0, 'engine': engine_name}
    
    def _select_best_result(self, results):
        if not results:
            return {'text': '', 'confidence': 0.0, 'engine': 'None'}
        
        # Simple selection: highest confidence
        best_result = max(results, key=lambda x: x['confidence'])
        return best_result
    
    def _calculate_quality(self, results):
        try:
            confidence = results.get('confidence', 0.0)
            text_length = len(results.get('text', ''))
            
            length_factor = min(1.0, text_length / 100)
            confidence_factor = confidence / 100
            
            quality_score = (confidence_factor * 0.8 + length_factor * 0.2) * 100
            return max(0, min(100, quality_score))
            
        except Exception:
            return 50.0
    
    def extract_text(self, file_path: str) -> str:
        """Extract text from document - compatible with existing code"""
        try:
            logger.info(f"📄 NextGen OCR processing: {file_path}")
            result = self.process_document_nextgen(file_path)
            if result and result.text:
                logger.info(f"✅ NextGen OCR extracted {len(result.text)} chars with {result.confidence:.1f}% confidence")
                return result.text
            else:
                logger.warning("⚠️ NextGen OCR returned empty text")
                return ""
        except Exception as e:
            logger.error(f"❌ NextGen OCR failed: {e}")
            return ""

async def test_processor():
    processor = NextGenerationOCRProcessor()
    
    # Create test image
    test_image = np.random.randint(0, 255, (800, 600, 3), dtype=np.uint8)
    cv2.putText(test_image, "Test Document OCR", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
    
    test_path = "test_image.png"
    cv2.imwrite(test_path, test_image)
    
    try:
        result = processor.process_document_nextgen(test_path, "test")
        print(f"✅ Processing completed!")
        print(f"Quality Score: {result.quality_score:.1f}%")
        print(f"Engine Used: {result.engine_used}")
        print(f"Confidence: {result.confidence:.1f}%")
        print(f"Text Length: {len(result.text)} characters")
        print(f"Processing Time: {result.processing_time:.2f}s")
        
        if os.path.exists(test_path):
            os.remove(test_path)
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_processor())
