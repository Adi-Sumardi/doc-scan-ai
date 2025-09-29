import os
import magic
import hashlib
import mimetypes
from typing import Dict, List, Optional, Tuple
from fastapi import HTTPException, UploadFile
import clamd
import logging
from config import settings

logger = logging.getLogger(__name__)

class FileSecurityValidator:
    """Comprehensive file security validation system"""
    
    def __init__(self):
        self.magic = magic.Magic(mime=True)
        self.allowed_extensions = settings.allowed_extensions_list
        self.max_file_size = settings.max_file_size_mb * 1024 * 1024  # Convert to bytes
        self.enable_virus_scan = settings.enable_virus_scan
        
        # Initialize ClamAV connection if enabled
        self.clamd_client = None
        if self.enable_virus_scan:
            try:
                self.clamd_client = clamd.ClamdUnixSocket()
                # Test connection
                self.clamd_client.ping()
                logger.info("ClamAV connection established successfully")
            except Exception as e:
                logger.warning(f"ClamAV not available: {e}. Virus scanning disabled.")
                self.enable_virus_scan = False
    
    async def validate_file(self, file: UploadFile) -> Dict[str, any]:
        """
        Comprehensive file validation including:
        - File size validation
        - Extension validation
        - MIME type validation
        - Virus scanning
        - File integrity checks
        """
        try:
            # Read file content
            content = await file.read()
            await file.seek(0)  # Reset file pointer
            
            validation_result = {
                "filename": file.filename,
                "size_bytes": len(content),
                "is_valid": True,
                "errors": [],
                "warnings": [],
                "security_checks": {},
                "file_info": {}
            }
            
            # 1. File size validation
            size_check = self._validate_file_size(len(content))
            validation_result["security_checks"]["size_check"] = size_check
            if not size_check["passed"]:
                validation_result["is_valid"] = False
                validation_result["errors"].append(size_check["message"])
            
            # 2. Extension validation
            ext_check = self._validate_file_extension(file.filename)
            validation_result["security_checks"]["extension_check"] = ext_check
            if not ext_check["passed"]:
                validation_result["is_valid"] = False
                validation_result["errors"].append(ext_check["message"])
            
            # 3. MIME type validation
            mime_check = self._validate_mime_type(content, file.filename)
            validation_result["security_checks"]["mime_check"] = mime_check
            validation_result["file_info"]["mime_type"] = mime_check.get("detected_mime", "unknown")
            if not mime_check["passed"]:
                validation_result["is_valid"] = False
                validation_result["errors"].append(mime_check["message"])
            
            # 4. File integrity checks
            integrity_check = self._check_file_integrity(content)
            validation_result["security_checks"]["integrity_check"] = integrity_check
            validation_result["file_info"].update(integrity_check["file_info"])
            
            # 5. Virus scanning
            if self.enable_virus_scan and self.clamd_client:
                virus_check = await self._scan_for_viruses(content)
                validation_result["security_checks"]["virus_scan"] = virus_check
                if not virus_check["passed"]:
                    validation_result["is_valid"] = False
                    validation_result["errors"].append(virus_check["message"])
            else:
                validation_result["security_checks"]["virus_scan"] = {
                    "passed": True,
                    "message": "Virus scanning disabled or unavailable",
                    "status": "skipped"
                }
            
            # 6. Advanced security checks
            advanced_checks = self._advanced_security_checks(content, file.filename)
            validation_result["security_checks"]["advanced_checks"] = advanced_checks
            if advanced_checks["warnings"]:
                validation_result["warnings"].extend(advanced_checks["warnings"])
            
            logger.info(f"File validation completed for {file.filename}: {'PASSED' if validation_result['is_valid'] else 'FAILED'}")
            return validation_result
            
        except Exception as e:
            logger.error(f"Error during file validation: {e}")
            return {
                "filename": file.filename,
                "size_bytes": 0,
                "is_valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": [],
                "security_checks": {},
                "file_info": {}
            }
    
    def _validate_file_size(self, size_bytes: int) -> Dict[str, any]:
        """Validate file size against limits"""
        if size_bytes > self.max_file_size:
            return {
                "passed": False,
                "message": f"File size ({size_bytes / (1024*1024):.2f} MB) exceeds maximum allowed size ({settings.max_file_size_mb} MB)",
                "size_bytes": size_bytes,
                "max_size_bytes": self.max_file_size
            }
        
        return {
            "passed": True,
            "message": "File size validation passed",
            "size_bytes": size_bytes,
            "max_size_bytes": self.max_file_size
        }
    
    def _validate_file_extension(self, filename: str) -> Dict[str, any]:
        """Validate file extension against allowed extensions"""
        if not filename:
            return {
                "passed": False,
                "message": "Filename is required",
                "extension": None
            }
        
        # Extract extension
        extension = filename.lower().split('.')[-1] if '.' in filename else ""
        
        if extension not in self.allowed_extensions:
            return {
                "passed": False,
                "message": f"File extension '{extension}' not allowed. Allowed extensions: {', '.join(self.allowed_extensions)}",
                "extension": extension,
                "allowed_extensions": self.allowed_extensions
            }
        
        return {
            "passed": True,
            "message": "File extension validation passed",
            "extension": extension,
            "allowed_extensions": self.allowed_extensions
        }
    
    def _validate_mime_type(self, content: bytes, filename: str) -> Dict[str, any]:
        """Validate MIME type matches file extension and is allowed"""
        try:
            # Detect MIME type from content
            detected_mime = self.magic.from_buffer(content)
            
            # Expected MIME types for our allowed extensions
            expected_mimes = {
                "pdf": ["application/pdf"],
                "png": ["image/png"],
                "jpg": ["image/jpeg"],
                "jpeg": ["image/jpeg"],
                "tiff": ["image/tiff"],
                "bmp": ["image/bmp", "image/x-ms-bmp"]
            }
            
            # Get file extension
            extension = filename.lower().split('.')[-1] if '.' in filename else ""
            
            if extension in expected_mimes:
                if detected_mime in expected_mimes[extension]:
                    return {
                        "passed": True,
                        "message": "MIME type validation passed",
                        "detected_mime": detected_mime,
                        "expected_mimes": expected_mimes[extension],
                        "extension": extension
                    }
                else:
                    return {
                        "passed": False,
                        "message": f"MIME type mismatch. Detected: {detected_mime}, Expected: {expected_mimes[extension]}",
                        "detected_mime": detected_mime,
                        "expected_mimes": expected_mimes[extension],
                        "extension": extension
                    }
            else:
                return {
                    "passed": False,
                    "message": f"Unknown or unsupported file extension: {extension}",
                    "detected_mime": detected_mime,
                    "extension": extension
                }
                
        except Exception as e:
            return {
                "passed": False,
                "message": f"MIME type detection failed: {str(e)}",
                "detected_mime": None,
                "error": str(e)
            }
    
    def _check_file_integrity(self, content: bytes) -> Dict[str, any]:
        """Check file integrity and generate checksums"""
        try:
            # Generate checksums
            md5_hash = hashlib.md5(content).hexdigest()
            sha256_hash = hashlib.sha256(content).hexdigest()
            
            # Basic integrity checks
            is_empty = len(content) == 0
            has_null_bytes = b'\x00' in content[:100]  # Check first 100 bytes for null bytes
            
            file_info = {
                "md5": md5_hash,
                "sha256": sha256_hash,
                "size_bytes": len(content),
                "is_empty": is_empty,
                "has_suspicious_content": has_null_bytes and len(content) < 1000  # Small files with null bytes are suspicious
            }
            
            return {
                "passed": not is_empty,
                "message": "File integrity check completed",
                "file_info": file_info
            }
            
        except Exception as e:
            return {
                "passed": False,
                "message": f"File integrity check failed: {str(e)}",
                "file_info": {},
                "error": str(e)
            }
    
    async def _scan_for_viruses(self, content: bytes) -> Dict[str, any]:
        """Scan file content for viruses using ClamAV"""
        try:
            if not self.clamd_client:
                return {
                    "passed": True,
                    "message": "Virus scanning not available",
                    "status": "skipped"
                }
            
            # Scan content
            scan_result = self.clamd_client.instream(content)
            
            if scan_result['stream'][0] == 'OK':
                return {
                    "passed": True,
                    "message": "No viruses detected",
                    "status": "clean",
                    "scan_result": scan_result
                }
            else:
                return {
                    "passed": False,
                    "message": f"Virus detected: {scan_result['stream'][1]}",
                    "status": "infected",
                    "scan_result": scan_result
                }
                
        except Exception as e:
            logger.error(f"Virus scanning failed: {e}")
            return {
                "passed": False,
                "message": f"Virus scanning failed: {str(e)}",
                "status": "error",
                "error": str(e)
            }
    
    def _advanced_security_checks(self, content: bytes, filename: str) -> Dict[str, any]:
        """Perform advanced security checks"""
        warnings = []
        checks = {}
        
        try:
            # Check for embedded executables (PE headers)
            if b'MZ' in content[:1024]:  # PE executable signature
                warnings.append("File contains executable content signatures")
                checks["has_executable_signatures"] = True
            else:
                checks["has_executable_signatures"] = False
            
            # Check for script content in non-script files
            script_patterns = [b'<script', b'javascript:', b'vbscript:', b'<?php']
            has_scripts = any(pattern in content[:10000] for pattern in script_patterns)
            if has_scripts:
                warnings.append("File contains script-like content")
                checks["has_script_content"] = True
            else:
                checks["has_script_content"] = False
            
            # Check for suspicious file size patterns
            if len(content) == 0:
                warnings.append("File is empty")
                checks["is_empty"] = True
            elif len(content) < 100:
                warnings.append("File is unusually small")
                checks["is_very_small"] = True
            else:
                checks["is_empty"] = False
                checks["is_very_small"] = False
            
            # Check filename for suspicious patterns
            suspicious_chars = ['..', '/', '\\', '|', '<', '>', ':', '"', '?', '*']
            has_suspicious_filename = any(char in filename for char in suspicious_chars)
            if has_suspicious_filename:
                warnings.append("Filename contains suspicious characters")
                checks["has_suspicious_filename"] = True
            else:
                checks["has_suspicious_filename"] = False
            
            return {
                "warnings": warnings,
                "checks": checks,
                "passed": len(warnings) == 0
            }
            
        except Exception as e:
            return {
                "warnings": [f"Advanced security check failed: {str(e)}"],
                "checks": {},
                "passed": False,
                "error": str(e)
            }

# Global file security validator instance
file_security = FileSecurityValidator()

def validate_uploaded_file(file: UploadFile):
    """Decorator/function to validate uploaded files"""
    async def _validate():
        validation_result = await file_security.validate_file(file)
        if not validation_result["is_valid"]:
            error_details = "; ".join(validation_result["errors"])
            raise HTTPException(
                status_code=400,
                detail=f"File validation failed: {error_details}"
            )
        return validation_result
    
    return _validate()