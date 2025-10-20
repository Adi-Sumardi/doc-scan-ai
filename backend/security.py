import os
import hashlib
import mimetypes
import re
import html
import logging
from typing import Dict, List, Optional, Tuple
from fastapi import HTTPException, UploadFile
from pathlib import Path
from config import settings

logger = logging.getLogger(__name__)

try:
    import magic  # type: ignore
    MAGIC_AVAILABLE = True
except ImportError:
    magic = None  # type: ignore
    MAGIC_AVAILABLE = False
    logger.warning("python-magic not available - falling back to mimetypes-based detection")

# Try to import clamd (optional)
try:
    import clamd
    CLAMD_AVAILABLE = True
except ImportError:
    CLAMD_AVAILABLE = False
    logger.warning("clamd not available - virus scanning will be disabled")

class FileSecurityValidator:
    """Comprehensive file security validation system"""
    
    def __init__(self):
        self.magic = None
        self.magic_available = False
        if MAGIC_AVAILABLE:
            try:
                self.magic = magic.Magic(mime=True)  # type: ignore[attr-defined]
                self.magic_available = True
            except (OSError, AttributeError) as exc:
                logger.warning(f"python-magic failed to initialize: {exc}. Falling back to mimetypes detection.")
                self.magic = None
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
            
            # 6. PDF Page Count Validation (for rekening koran)
            if file.filename.lower().endswith('.pdf'):
                page_count_check = self._validate_pdf_page_count(content, file.filename)
                validation_result["security_checks"]["page_count_check"] = page_count_check
                validation_result["file_info"]["page_count"] = page_count_check.get("page_count", 0)
                if not page_count_check["passed"]:
                    validation_result["is_valid"] = False
                    validation_result["errors"].append(page_count_check["message"])

            # 7. Advanced security checks
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

    def _validate_pdf_page_count(self, content: bytes, filename: str) -> Dict[str, any]:
        """Validate PDF page count against Google Document AI limits"""
        try:
            import io
            import PyPDF2

            pdf_file = io.BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            page_count = len(pdf_reader.pages)

            max_pages = settings.max_pdf_pages_per_file  # 30 pages (Google Document AI imageless mode limit)

            if page_count > max_pages:
                return {
                    "passed": False,
                    "message": f"❌ PDF has {page_count} pages. Maximum allowed: {max_pages} pages (Google Document AI limit). Please split your file into multiple parts: Part 1 (pages 1-{max_pages}), Part 2 (pages {max_pages+1}-{max_pages*2}), etc.",
                    "page_count": page_count,
                    "max_pages": max_pages,
                    "suggestion": f"Split into {(page_count + max_pages - 1) // max_pages} files"
                }

            return {
                "passed": True,
                "message": f"PDF page count validation passed ({page_count} pages)",
                "page_count": page_count,
                "max_pages": max_pages
            }

        except Exception as e:
            logger.error(f"Error validating PDF page count: {e}")
            # Don't fail validation if we can't count pages
            return {
                "passed": True,
                "message": f"Unable to validate page count: {str(e)}",
                "page_count": 0,
                "max_pages": settings.max_pdf_pages_per_file
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
            detected_mime = None
            detection_source = "magic"

            if self.magic is not None:
                try:
                    detected_mime = self.magic.from_buffer(content)
                except Exception as exc:
                    logger.warning(f"python-magic MIME detection failed: {exc}. Falling back to mimetypes")

            if not detected_mime:
                detection_source = "fallback"
                detected_mime, _ = mimetypes.guess_type(filename)
                if not detected_mime:
                    detected_mime = "application/octet-stream"
            
            # Expected MIME types for our allowed extensions
            expected_mimes = {
                "pdf": ["application/pdf"],
                "png": ["image/png"],
                "jpg": ["image/jpeg"],
                "jpeg": ["image/jpeg"],
                "tiff": ["image/tiff"],
                "bmp": ["image/bmp", "image/x-ms-bmp"],
                "xlsx": ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
                "xls": ["application/vnd.ms-excel", "application/msexcel"]
            }
            
            # Get file extension
            extension = filename.lower().split('.')[-1] if '.' in filename else ""
            
            if extension in expected_mimes:
                if detected_mime in expected_mimes[extension]:
                    return {
                        "passed": True,
                        "message": f"MIME type validation passed ({detection_source})",
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


class SecurityValidator:
    """Comprehensive security validation for user inputs (XSS, injection prevention)"""
    
    @staticmethod
    def sanitize_input(text: str, max_length: int = 1000) -> str:
        """
        Sanitize user input to prevent XSS attacks
        
        Args:
            text: User input string
            max_length: Maximum allowed length
            
        Returns:
            Sanitized string
            
        Raises:
            HTTPException: If input is too long or contains null bytes
        """
        if not text:
            return ""
        
        # Remove null bytes (can be used for injection)
        if '\x00' in text:
            raise HTTPException(
                status_code=400,
                detail="Input contains invalid characters (null bytes)"
            )
        
        # Limit length
        if len(text) > max_length:
            raise HTTPException(
                status_code=400,
                detail=f"Input too long (max {max_length} characters)"
            )
        
        # Escape HTML to prevent XSS
        text = html.escape(text)
        
        # Remove dangerous patterns
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'<iframe',
            r'<object',
            r'<embed',
        ]
        
        for pattern in dangerous_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
        
        return text.strip()
    
    @staticmethod
    def validate_email(email: str) -> str:
        """
        Validate email format
        
        Args:
            email: Email address
            
        Returns:
            Lowercase email
            
        Raises:
            HTTPException: If email format is invalid
        """
        if not email:
            raise HTTPException(status_code=400, detail="Email is required")
        
        # RFC 5322 simplified pattern
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(pattern, email):
            raise HTTPException(status_code=400, detail="Invalid email format")
        
        if len(email) > 254:  # RFC maximum
            raise HTTPException(status_code=400, detail="Email address too long")
        
        # Check for SQL injection patterns in email
        if SecurityValidator.check_sql_injection(email):
            raise HTTPException(
                status_code=400,
                detail="Invalid email format - contains suspicious patterns"
            )
        
        return email.lower().strip()
    
    @staticmethod
    def validate_username(username: str) -> str:
        """
        Validate username format and length
        
        Args:
            username: Username string
            
        Returns:
            Validated username
            
        Raises:
            HTTPException: If username is invalid
        """
        if not username:
            raise HTTPException(status_code=400, detail="Username is required")
        
        username = username.strip()
        
        if len(username) < 3:
            raise HTTPException(
                status_code=400,
                detail="Username must be at least 3 characters"
            )
        
        if len(username) > 50:
            raise HTTPException(
                status_code=400,
                detail="Username cannot exceed 50 characters"
            )
        
        # Only allow alphanumeric, underscore, and hyphen
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            raise HTTPException(
                status_code=400,
                detail="Username can only contain letters, numbers, underscore, and hyphen"
            )
        
        # Check for reserved usernames
        reserved = ['admin', 'root', 'system', 'administrator', 'moderator', 'support', 'api', 'null', 'undefined']
        if username.lower() in reserved:
            raise HTTPException(
                status_code=400,
                detail="This username is reserved and cannot be used"
            )
        
        # Check for SQL injection patterns
        if SecurityValidator.check_sql_injection(username):
            raise HTTPException(
                status_code=400,
                detail="Username contains invalid characters"
            )
        
        return username
    
    @staticmethod
    def validate_password_strength(password: str) -> bool:
        """
        Validate password meets security requirements
        
        Requirements:
        - At least 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character
        - Not a common weak password
        
        Args:
            password: Password to validate
            
        Returns:
            True if valid
            
        Raises:
            HTTPException: If password doesn't meet requirements
        """
        if not password:
            raise HTTPException(status_code=400, detail="Password is required")
        
        if len(password) < 8:
            raise HTTPException(
                status_code=400,
                detail="Password must be at least 8 characters long"
            )
        
        if len(password) > 128:
            raise HTTPException(
                status_code=400,
                detail="Password too long (maximum 128 characters)"
            )
        
        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', password):
            raise HTTPException(
                status_code=400,
                detail="Password must contain at least one uppercase letter (A-Z)"
            )
        
        # Check for at least one lowercase letter
        if not re.search(r'[a-z]', password):
            raise HTTPException(
                status_code=400,
                detail="Password must contain at least one lowercase letter (a-z)"
            )
        
        # Check for at least one digit
        if not re.search(r'\d', password):
            raise HTTPException(
                status_code=400,
                detail="Password must contain at least one digit (0-9)"
            )
        
        # Check for at least one special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;/~`]', password):
            raise HTTPException(
                status_code=400,
                detail="Password must contain at least one special character (!@#$%^&* etc.)"
            )
        
        # Check for common weak passwords
        weak_passwords = [
            'password', 'password123', 'password1', '12345678', 'qwerty123',
            'admin123', 'letmein123', 'welcome123', 'abc12345', 'Password1',
            'Password123', 'Qwerty123', 'Admin123'
        ]
        if password in weak_passwords:
            raise HTTPException(
                status_code=400,
                detail="This password is too common. Please choose a stronger, unique password"
            )
        
        # Check for sequential characters (e.g., "12345", "abcde")
        if re.search(r'(012|123|234|345|456|567|678|789|abc|bcd|cde|def)', password.lower()):
            logger.warning(f"Password contains sequential characters")
            # This is a warning, not an error - still allow but log
        
        return True
    
    @staticmethod
    def validate_filename(filename: str) -> str:
        """
        Validate and sanitize filename to prevent path traversal attacks
        
        Args:
            filename: Original filename
            
        Returns:
            Safe filename
            
        Raises:
            HTTPException: If filename is invalid
        """
        if not filename:
            raise HTTPException(status_code=400, detail="Filename cannot be empty")
        
        # Remove directory traversal attempts
        filename = filename.replace('../', '').replace('..\\', '')
        filename = filename.replace('/', '').replace('\\', '')
        
        # Remove null bytes
        filename = filename.replace('\x00', '')
        
        # Remove or replace dangerous characters but keep extension
        # Allow: letters, numbers, spaces, dots, underscores, hyphens
        name_parts = filename.rsplit('.', 1)
        clean_name = re.sub(r'[^\w\s.-]', '_', name_parts[0])
        
        if len(name_parts) > 1:
            clean_ext = re.sub(r'[^\w]', '', name_parts[1])
            filename = f"{clean_name}.{clean_ext}"
        else:
            filename = clean_name
        
        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')
        
        # Limit length (filesystem limit is usually 255)
        if len(filename) > 255:
            # Truncate but keep extension
            if '.' in filename:
                name, ext = filename.rsplit('.', 1)
                max_name_len = 250 - len(ext)
                filename = name[:max_name_len] + '.' + ext
            else:
                filename = filename[:255]
        
        # Final validation
        if not filename or filename in ['.', '..']:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        # Check for reserved Windows filenames
        reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 
                         'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 
                         'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']
        name_without_ext = filename.split('.')[0].upper()
        if name_without_ext in reserved_names:
            raise HTTPException(
                status_code=400,
                detail=f"Filename '{filename}' is reserved and cannot be used"
            )
        
        return filename
    
    @staticmethod
    def check_sql_injection(text: str) -> bool:
        """
        Check if text contains potential SQL injection patterns
        
        Args:
            text: Text to check
            
        Returns:
            True if suspicious patterns found, False otherwise
        """
        if not text:
            return False
        
        # Common SQL injection patterns
        sql_patterns = [
            r"(\bOR\b|\bAND\b)\s+\d+\s*=\s*\d+",  # OR 1=1, AND 1=1
            r"'\s*(OR|AND)\s+'1'\s*=\s*'1",  # ' OR '1'='1
            r"\bUNION\s+(ALL\s+)?SELECT\b",  # UNION SELECT
            r"\bDROP\s+TABLE\b",  # DROP TABLE
            r"\bINSERT\s+INTO\b",  # INSERT INTO
            r"\bDELETE\s+FROM\b",  # DELETE FROM
            r"\bUPDATE\s+\w+\s+SET\b",  # UPDATE ... SET
            r"--\s*$",  # SQL comment at end
            r"/\*.*?\*/",  # SQL block comment
            r"\bEXEC\b.*\(",  # EXEC(
            r"\bEXECUTE\b.*\(",  # EXECUTE(
            r";\s*DROP\s+",  # ; DROP
            r";\s*DELETE\s+",  # ; DELETE
            r"'\s*;\s*",  # '; (command separator)
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"SQL injection pattern detected: {pattern}")
                return True
        
        return False
    
    @staticmethod
    def validate_integer(value: any, min_value: int = None, max_value: int = None, field_name: str = "value") -> int:
        """
        Validate and convert to integer with optional range check
        
        Args:
            value: Value to validate
            min_value: Minimum allowed value (optional)
            max_value: Maximum allowed value (optional)
            field_name: Name of field for error messages
            
        Returns:
            Validated integer
            
        Raises:
            HTTPException: If value is invalid
        """
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=400,
                detail=f"{field_name} must be a valid integer"
            )
        
        if min_value is not None and int_value < min_value:
            raise HTTPException(
                status_code=400,
                detail=f"{field_name} must be at least {min_value}"
            )
        
        if max_value is not None and int_value > max_value:
            raise HTTPException(
                status_code=400,
                detail=f"{field_name} cannot exceed {max_value}"
            )
        
        return int_value