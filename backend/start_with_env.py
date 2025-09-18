#!/usr/bin/env python3
"""
Enhanced startup script that ensures virtual environment is used
"""
import subprocess
import sys
import os
from pathlib import Path

def main():
    # Get the backend directory
    backend_dir = Path(__file__).parent
    venv_path = backend_dir / "doc_scan_env"
    
    # Check if virtual environment exists
    if not venv_path.exists():
        print("❌ Virtual environment not found!")
        print("Please run: python3 -m venv doc_scan_env")
        sys.exit(1)
    
    # Get the python executable from venv
    if sys.platform == "win32":
        python_exec = venv_path / "Scripts" / "python.exe"
    else:
        python_exec = venv_path / "bin" / "python"
    
    if not python_exec.exists():
        print(f"❌ Python executable not found at {python_exec}")
        sys.exit(1)
    
    print("🚀 Starting FastAPI server with virtual environment...")
    print(f"Using Python: {python_exec}")
    
    # Start the server using the virtual environment python
    try:
        subprocess.run([
            str(python_exec), 
            "-m", "uvicorn", 
            "main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload"
        ], cwd=backend_dir, check=True)
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    except subprocess.CalledProcessError as e:
        print(f"❌ Server failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
