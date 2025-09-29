#!/usr/bin/env python3
"""
SUPER ADVANCED IMAGE PREPROCESSOR
State-of-the-art preprocessing untuk hasil OCR maksimal
Menggunakan AI-based correction dan advanced algorithms
"""

import cv2
import numpy as np
import logging
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass
import math
from scipy import ndimage
from skimage import filters, morphology, measure, transform
from skimage.feature import canny
from skimage.transform import hough_line, hough_line_peaks
import albumentations as A

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ImageQualityMetrics:
    """Advanced image quality metrics"""
    sharpness: float
    contrast: float
    brightness: float
    noise_level: float
    skew_angle: float
    document_coverage: float
    text_density: float
    overall_score: float

class SuperAdvancedPreprocessor:
    """State-of-the-art image preprocessing for OCR"""
    
    def __init__(self):
        """Initialize preprocessor with advanced algorithms"""
        self.clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        
        # Advanced augmentation pipeline
        self.quality_enhancer = A.Compose([
            A.CLAHE(clip_limit=2.0, tile_grid_size=(8, 8), p=0.5),
            A.Sharpen(alpha=(0.2, 0.5), lightness=(0.5, 1.0), p=0.5),
            A.UnsharpMask(blur_limit=(3, 7), sigma_limit=0, alpha=(0.2, 0.5), threshold=10, p=0.3),
        ])
        
        logger.info("🚀 Super Advanced Preprocessor initialized")
    
    def analyze_image_quality(self, image: np.ndarray) -> ImageQualityMetrics:
        """Comprehensive image quality analysis"""
        try:
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # Sharpness (Laplacian variance)
            sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # Contrast (RMS contrast)
            contrast = gray.std()
            
            # Brightness (mean)
            brightness = gray.mean()
            
            # Noise level (using high-frequency content)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            noise_level = np.mean(np.abs(gray.astype(float) - blur.astype(float)))
            
            # Skew angle
            skew_angle = self._detect_skew_advanced(gray)
            
            # Document coverage (non-white pixels)
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            document_coverage = 1.0 - (np.sum(binary == 255) / binary.size)
            
            # Text density estimation
            edges = cv2.Canny(gray, 50, 150)
            text_density = np.sum(edges > 0) / edges.size
            
            # Overall quality score
            overall_score = self._calculate_quality_score(
                sharpness, contrast, brightness, noise_level, 
                abs(skew_angle), document_coverage, text_density
            )
            
            return ImageQualityMetrics(
                sharpness=sharpness,
                contrast=contrast,
                brightness=brightness,
                noise_level=noise_level,
                skew_angle=skew_angle,
                document_coverage=document_coverage,
                text_density=text_density,
                overall_score=overall_score
            )
            
        except Exception as e:
            logger.error(f"❌ Quality analysis failed: {e}")
            return ImageQualityMetrics(50, 50, 128, 10, 0, 0.5, 0.1, 50)
    
    def preprocess_super_advanced(self, image: np.ndarray, doc_type: str = "unknown") -> np.ndarray:
        """Super advanced preprocessing pipeline"""
        try:
            logger.info(f"🔄 Starting super advanced preprocessing for {doc_type}")
            
            # Step 1: Quality analysis
            quality = self.analyze_image_quality(image)
            logger.info(f"📊 Quality metrics: Sharpness={quality.sharpness:.1f}, "
                       f"Contrast={quality.contrast:.1f}, Overall={quality.overall_score:.1f}")
            
            # Step 2: Convert to grayscale
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # Step 3: Perspective correction
            gray = self._correct_perspective_ai(gray)
            
            # Step 4: Deskewing
            if abs(quality.skew_angle) > 0.5:
                gray = self._deskew_image_advanced(gray, quality.skew_angle)
                logger.info(f"🔧 Deskewed by {quality.skew_angle:.2f} degrees")
            
            # Step 5: Advanced denoising
            if quality.noise_level > 15:
                gray = self._denoise_adaptive(gray, quality.noise_level)
                logger.info("🧹 Applied adaptive denoising")
            
            # Step 6: Contrast enhancement
            if quality.contrast < 50:
                gray = self._enhance_contrast_adaptive(gray, quality.contrast)
                logger.info("📈 Enhanced contrast")
            
            # Step 7: Sharpening
            if quality.sharpness < 100:
                gray = self._sharpen_adaptive(gray, quality.sharpness)
                logger.info("🔪 Applied adaptive sharpening")
            
            # Step 8: Document-specific optimization
            gray = self._optimize_for_document_type(gray, doc_type, quality)
            
            # Step 9: Final binarization
            binary = self._binarize_advanced(gray, quality)
            
            logger.info("✅ Super advanced preprocessing completed")
            return binary
            
        except Exception as e:
            logger.error(f"❌ Super advanced preprocessing failed: {e}")
            return image
    
    def _detect_skew_advanced(self, image: np.ndarray) -> float:
        """Advanced skew detection using multiple methods"""
        try:
            # Method 1: Hough Line Transform
            edges = canny(image, sigma=2, low_threshold=0.1, high_threshold=0.2)
            lines = hough_line(edges, theta=np.linspace(-np.pi/2, np.pi/2, 360))
            hspace, angles, dists = hough_line_peaks(lines[0], lines[1], lines[2])
            
            if len(hspace) > 0:
                # Find most prominent angle
                angle = angles[np.argmax(hspace)]
                skew_angle = np.degrees(angle)
                
                # Normalize to [-45, 45] range
                if skew_angle > 45:
                    skew_angle -= 90
                elif skew_angle < -45:
                    skew_angle += 90
                
                return skew_angle
            
            # Method 2: Projection profile (fallback)
            h, w = image.shape
            center = h // 2
            
            # Calculate horizontal projection variance for different angles
            best_angle = 0
            max_variance = 0
            
            for angle in range(-45, 46, 1):
                rotated = transform.rotate(image, angle, preserve_range=True).astype(np.uint8)
                projection = np.sum(rotated, axis=1)
                variance = np.var(projection)
                
                if variance > max_variance:
                    max_variance = variance
                    best_angle = angle
            
            return best_angle
            
        except Exception as e:
            logger.error(f"❌ Skew detection failed: {e}")
            return 0.0
    
    def _correct_perspective_ai(self, image: np.ndarray) -> np.ndarray:
        """AI-based perspective correction"""
        try:
            # Find document contours
            blurred = cv2.GaussianBlur(image, (5, 5), 0)
            edged = cv2.Canny(blurred, 75, 200)
            
            # Find contours
            contours, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
            
            # Find the largest rectangular contour
            for contour in contours:
                peri = cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
                
                if len(approx) == 4:
                    # Apply perspective transform
                    return self._four_point_transform(image, approx.reshape(4, 2))
            
            return image
            
        except Exception as e:
            logger.error(f"❌ Perspective correction failed: {e}")
            return image
    
    def _four_point_transform(self, image: np.ndarray, pts: np.ndarray) -> np.ndarray:
        """Apply four-point perspective transform"""
        try:
            # Order points: top-left, top-right, bottom-right, bottom-left
            rect = self._order_points(pts)
            (tl, tr, br, bl) = rect
            
            # Compute width and height
            widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
            widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
            maxWidth = max(int(widthA), int(widthB))
            
            heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
            heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
            maxHeight = max(int(heightA), int(heightB))
            
            # Destination points
            dst = np.array([
                [0, 0],
                [maxWidth - 1, 0],
                [maxWidth - 1, maxHeight - 1],
                [0, maxHeight - 1]
            ], dtype="float32")
            
            # Compute perspective transform matrix
            M = cv2.getPerspectiveTransform(rect, dst)
            warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
            
            return warped
            
        except Exception as e:
            logger.error(f"❌ Four point transform failed: {e}")
            return image
    
    def _order_points(self, pts: np.ndarray) -> np.ndarray:
        """Order points in clockwise order"""
        rect = np.zeros((4, 2), dtype="float32")
        
        # Sum and difference to find corners
        s = pts.sum(axis=1)
        diff = np.diff(pts, axis=1)
        
        rect[0] = pts[np.argmin(s)]      # top-left
        rect[2] = pts[np.argmax(s)]      # bottom-right
        rect[1] = pts[np.argmin(diff)]   # top-right
        rect[3] = pts[np.argmax(diff)]   # bottom-left
        
        return rect
    
    def _deskew_image_advanced(self, image: np.ndarray, angle: float) -> np.ndarray:
        """Advanced deskewing with subpixel accuracy"""
        try:
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            
            # Create rotation matrix
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            
            # Perform rotation
            rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            
            return rotated
            
        except Exception as e:
            logger.error(f"❌ Advanced deskewing failed: {e}")
            return image
    
    def _denoise_adaptive(self, image: np.ndarray, noise_level: float) -> np.ndarray:
        """Adaptive denoising based on noise level"""
        try:
            if noise_level > 25:
                # Heavy denoising
                return cv2.fastNlMeansDenoising(image, None, 10, 7, 21)
            elif noise_level > 15:
                # Medium denoising
                return cv2.fastNlMeansDenoising(image, None, 7, 7, 21)
            else:
                # Light denoising
                return cv2.bilateralFilter(image, 9, 75, 75)
                
        except Exception as e:
            logger.error(f"❌ Adaptive denoising failed: {e}")
            return image
    
    def _enhance_contrast_adaptive(self, image: np.ndarray, contrast: float) -> np.ndarray:
        """Adaptive contrast enhancement"""
        try:
            if contrast < 30:
                # Strong enhancement
                return self.clahe.apply(image)
            else:
                # Gentle enhancement
                alpha = 1.2  # Contrast control
                beta = 10    # Brightness control
                return cv2.convertScaleAbs(image, alpha=alpha, beta=beta)
                
        except Exception as e:
            logger.error(f"❌ Contrast enhancement failed: {e}")
            return image
    
    def _sharpen_adaptive(self, image: np.ndarray, sharpness: float) -> np.ndarray:
        """Adaptive sharpening based on image sharpness"""
        try:
            if sharpness < 50:
                # Strong sharpening
                kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            else:
                # Gentle sharpening
                kernel = np.array([[0,-1,0], [-1,5,-1], [0,-1,0]])
            
            return cv2.filter2D(image, -1, kernel)
            
        except Exception as e:
            logger.error(f"❌ Adaptive sharpening failed: {e}")
            return image
    
    def _optimize_for_document_type(self, image: np.ndarray, doc_type: str, quality: ImageQualityMetrics) -> np.ndarray:
        """Document-specific optimization"""
        try:
            if doc_type in ['faktur_pajak', 'pph21', 'pph23']:
                # Tax documents often have structured layouts
                # Apply morphological operations to clean up table structures
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
                image = cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel)
                
            elif doc_type in ['rekening_koran']:
                # Bank statements have dense text
                # Apply gentle smoothing
                image = cv2.GaussianBlur(image, (3, 3), 0)
                
            elif doc_type in ['invoice']:
                # Invoices vary widely - use conservative processing
                pass
            
            return image
            
        except Exception as e:
            logger.error(f"❌ Document-specific optimization failed: {e}")
            return image
    
    def _binarize_advanced(self, image: np.ndarray, quality: ImageQualityMetrics) -> np.ndarray:
        """Advanced binarization with quality-based selection"""
        try:
            # Try multiple binarization methods
            methods = []
            
            # Method 1: Otsu's thresholding
            _, otsu = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            methods.append(('Otsu', otsu))
            
            # Method 2: Adaptive thresholding
            adaptive = cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            methods.append(('Adaptive', adaptive))
            
            # Method 3: Niblack-style local thresholding (if quality is poor)
            if quality.overall_score < 60:
                # Use smaller block size for poor quality images
                niblack = cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, 5)
                methods.append(('Niblack', niblack))
            
            # Select best method based on image characteristics
            if quality.contrast > 60:
                return otsu  # High contrast - Otsu works well
            elif quality.brightness < 100 or quality.brightness > 180:
                return adaptive  # Poor lighting - adaptive works better
            else:
                return otsu  # Default to Otsu
                
        except Exception as e:
            logger.error(f"❌ Advanced binarization failed: {e}")
            _, binary = cv2.threshold(image, 127, 255, cv2.THRESH_BINARY)
            return binary
    
    def _calculate_quality_score(self, sharpness: float, contrast: float, brightness: float, 
                                noise_level: float, skew_angle: float, document_coverage: float, 
                                text_density: float) -> float:
        """Calculate overall image quality score"""
        try:
            # Normalize metrics to 0-100 scale
            sharpness_score = min(100, sharpness / 2)  # Typical good sharpness > 100
            contrast_score = min(100, contrast / 0.8)  # Typical good contrast > 60
            brightness_score = 100 - abs(brightness - 128) / 1.28  # Optimal brightness around 128
            noise_score = max(0, 100 - noise_level * 2)  # Lower noise is better
            skew_score = max(0, 100 - abs(skew_angle) * 2)  # Less skew is better
            coverage_score = document_coverage * 100  # More document coverage is better
            density_score = min(100, text_density * 500)  # Good text density
            
            # Weighted average
            weights = [0.2, 0.2, 0.1, 0.15, 0.1, 0.15, 0.1]
            scores = [sharpness_score, contrast_score, brightness_score, noise_score, 
                     skew_score, coverage_score, density_score]
            
            overall_score = sum(w * s for w, s in zip(weights, scores))
            return max(0, min(100, overall_score))
            
        except Exception as e:
            logger.error(f"❌ Quality score calculation failed: {e}")
            return 50.0

# Test function
def test_super_preprocessor():
    """Test the super advanced preprocessor"""
    preprocessor = SuperAdvancedPreprocessor()
    
    # Create a test image
    test_image = np.random.randint(0, 255, (800, 600), dtype=np.uint8)
    
    # Analyze quality
    quality = preprocessor.analyze_image_quality(test_image)
    print(f"✅ Quality analysis: Overall score = {quality.overall_score:.1f}")
    
    # Process image
    processed = preprocessor.preprocess_super_advanced(test_image, "faktur_pajak")
    print(f"✅ Processing completed: {processed.shape}")

if __name__ == "__main__":
    test_super_preprocessor()