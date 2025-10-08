"""Backend package bootstrap utilities."""

from pathlib import Path
import sys

# Ensure the backend directory itself is on sys.path so that legacy absolute imports
# like `from database import ...` continue to resolve when the package is imported
_package_dir = Path(__file__).resolve().parent
_package_dir_str = str(_package_dir)
if _package_dir_str not in sys.path:
	sys.path.insert(0, _package_dir_str)
