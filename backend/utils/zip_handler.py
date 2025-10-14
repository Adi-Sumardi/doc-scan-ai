"""
ZIP File Handler
Utility for handling ZIP file uploads and extraction for batch document processing.
"""

import os
import zipfile
import shutil
import logging
from pathlib import Path
from typing import List, Tuple, Dict
import tempfile

logger = logging.getLogger(__name__)

# Configuration (will be overridden by config.py if available)
MAX_ZIP_SIZE_MB = 200  # Maximum ZIP file size in MB (increased for large batches)
MAX_FILES_IN_ZIP = 100  # Maximum number of files in ZIP (increased from 50)
ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.tif'}


class ZipHandler:
    """Handle ZIP file extraction and validation for document uploads"""

    def __init__(self, max_size_mb: int = MAX_ZIP_SIZE_MB, max_files: int = MAX_FILES_IN_ZIP):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.max_files = max_files
        self.allowed_extensions = ALLOWED_EXTENSIONS

    def validate_zip_file(self, zip_path: str) -> Tuple[bool, str]:
        """
        Validate ZIP file before extraction.

        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        try:
            # Check file exists
            if not os.path.exists(zip_path):
                return False, "ZIP file not found"

            # Check file size
            file_size = os.path.getsize(zip_path)
            if file_size > self.max_size_bytes:
                size_mb = file_size / (1024 * 1024)
                return False, f"ZIP file too large: {size_mb:.1f}MB (max: {self.max_size_bytes / (1024 * 1024):.0f}MB)"

            # Check if it's a valid ZIP file
            if not zipfile.is_zipfile(zip_path):
                return False, "Invalid ZIP file format"

            # Check ZIP contents
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()

                # Check number of files
                valid_files = [f for f in file_list if not f.endswith('/') and not f.startswith('__MACOSX')]
                if len(valid_files) > self.max_files:
                    return False, f"Too many files in ZIP: {len(valid_files)} (max: {self.max_files})"

                if len(valid_files) == 0:
                    return False, "ZIP file contains no valid files"

                # Check for dangerous files
                for file_name in file_list:
                    # Skip directories and macOS metadata
                    if file_name.endswith('/') or file_name.startswith('__MACOSX'):
                        continue

                    # Check for path traversal attacks
                    if '..' in file_name or file_name.startswith('/'):
                        return False, f"Suspicious file path detected: {file_name}"

                logger.info(f"✅ ZIP validation passed: {len(valid_files)} files, {file_size / (1024 * 1024):.1f}MB")
                return True, f"Valid ZIP with {len(valid_files)} files"

        except zipfile.BadZipFile:
            return False, "Corrupted ZIP file"
        except Exception as e:
            logger.error(f"❌ ZIP validation error: {e}")
            return False, f"Validation error: {str(e)}"

    def extract_zip_file(self, zip_path: str, extract_to: str = None) -> Tuple[bool, List[str], str]:
        """
        Extract ZIP file and return list of extracted file paths.

        Args:
            zip_path: Path to ZIP file
            extract_to: Directory to extract to (if None, creates temp directory)

        Returns:
            Tuple[bool, List[str], str]: (success, list_of_file_paths, error_message)
        """
        try:
            # Validate first
            is_valid, message = self.validate_zip_file(zip_path)
            if not is_valid:
                return False, [], message

            # Create extraction directory
            if extract_to is None:
                extract_to = tempfile.mkdtemp(prefix='zip_extract_')
            else:
                os.makedirs(extract_to, exist_ok=True)

            extracted_files = []

            # Extract ZIP
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                logger.info(f"📦 Extracting ZIP to: {extract_to}")

                for file_info in zip_ref.infolist():
                    file_name = file_info.filename

                    # Skip directories, macOS metadata, and hidden files
                    if (file_info.is_dir() or
                        file_name.startswith('__MACOSX') or
                        file_name.startswith('.') or
                        '/' in file_name and file_name.split('/')[-1].startswith('.')):
                        continue

                    # Get file extension
                    file_ext = Path(file_name).suffix.lower()

                    # Only extract allowed file types
                    if file_ext in self.allowed_extensions:
                        # Extract to flat directory (no subdirectories)
                        # This prevents nested folder issues
                        file_basename = os.path.basename(file_name)
                        extract_path = os.path.join(extract_to, file_basename)

                        # Handle duplicate filenames
                        if os.path.exists(extract_path):
                            name, ext = os.path.splitext(file_basename)
                            counter = 1
                            while os.path.exists(extract_path):
                                file_basename = f"{name}_{counter}{ext}"
                                extract_path = os.path.join(extract_to, file_basename)
                                counter += 1

                        # Extract file
                        with zip_ref.open(file_info) as source, open(extract_path, 'wb') as target:
                            shutil.copyfileobj(source, target)

                        extracted_files.append(extract_path)
                        logger.info(f"  ✅ Extracted: {file_basename}")
                    else:
                        logger.info(f"  ⏭️  Skipped (unsupported): {file_name}")

            if not extracted_files:
                return False, [], "No valid document files found in ZIP"

            logger.info(f"✅ Successfully extracted {len(extracted_files)} files from ZIP")
            return True, extracted_files, f"Extracted {len(extracted_files)} files"

        except Exception as e:
            logger.error(f"❌ ZIP extraction error: {e}", exc_info=True)
            return False, [], f"Extraction error: {str(e)}"

    def get_zip_info(self, zip_path: str) -> Dict:
        """
        Get information about ZIP file contents without extracting.

        Returns:
            Dict with ZIP metadata
        """
        try:
            if not zipfile.is_zipfile(zip_path):
                return {"error": "Not a valid ZIP file"}

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()

                # Filter valid files
                valid_files = []
                for file_name in file_list:
                    if file_name.endswith('/') or file_name.startswith('__MACOSX'):
                        continue
                    file_ext = Path(file_name).suffix.lower()
                    if file_ext in self.allowed_extensions:
                        valid_files.append(file_name)

                total_size = sum(info.file_size for info in zip_ref.infolist())

                return {
                    "total_files": len(file_list),
                    "valid_files": len(valid_files),
                    "valid_file_names": valid_files,
                    "total_size_bytes": total_size,
                    "total_size_mb": round(total_size / (1024 * 1024), 2)
                }

        except Exception as e:
            logger.error(f"❌ Error getting ZIP info: {e}")
            return {"error": str(e)}

    def cleanup_extracted_files(self, directory: str) -> bool:
        """
        Clean up extracted files and directory.

        Args:
            directory: Directory to remove

        Returns:
            bool: Success status
        """
        try:
            if os.path.exists(directory):
                shutil.rmtree(directory)
                logger.info(f"🗑️  Cleaned up extracted files: {directory}")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Cleanup error: {e}")
            return False


# Convenience functions
def extract_zip(zip_path: str, extract_to: str = None) -> Tuple[bool, List[str], str]:
    """
    Quick function to extract ZIP file.

    Returns:
        Tuple[bool, List[str], str]: (success, file_paths, message)
    """
    handler = ZipHandler()
    return handler.extract_zip_file(zip_path, extract_to)


def validate_zip(zip_path: str) -> Tuple[bool, str]:
    """
    Quick function to validate ZIP file.

    Returns:
        Tuple[bool, str]: (is_valid, message)
    """
    handler = ZipHandler()
    return handler.validate_zip_file(zip_path)


def get_zip_info(zip_path: str) -> Dict:
    """
    Quick function to get ZIP info.

    Returns:
        Dict with ZIP metadata
    """
    handler = ZipHandler()
    return handler.get_zip_info(zip_path)


def cleanup_temp_dir(directory: str) -> bool:
    """
    Quick function to cleanup directory.

    Returns:
        bool: Success status
    """
    handler = ZipHandler()
    return handler.cleanup_extracted_files(directory)
