import torch
import logging

logger = logging.getLogger(__name__)

def get_optimal_device():
    """
    Get the optimal computing device for AI/ML processing
    Returns the best available device in order: MPS -> CUDA -> CPU
    """
    try:
        # Check for Apple Silicon MPS
        if torch.backends.mps.is_available() and torch.backends.mps.is_built():
            device = torch.device("mps")
            logger.info("✅ Using Apple Silicon MPS for GPU acceleration")
            return device
    except Exception as e:
        logger.warning(f"MPS check failed: {e}")
    
    try:
        # Check for NVIDIA CUDA
        if torch.cuda.is_available():
            device = torch.device("cuda")
            logger.info(f"✅ Using NVIDIA CUDA GPU: {torch.cuda.get_device_name()}")
            return device
    except Exception as e:
        logger.warning(f"CUDA check failed: {e}")
    
    # Fallback to CPU
    device = torch.device("cpu")
    logger.info("⚠️ Using CPU for processing. Consider GPU for better performance.")
    return device

def configure_ocr_device():
    """
    Configure optimal device settings for OCR processing
    """
    device = get_optimal_device()
    
    # Set environment variables for better performance
    import os
    
    if device.type == "mps":
        # Optimize for Apple Silicon
        os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
        logger.info("🔧 Configured PyTorch MPS fallback for compatibility")
    
    elif device.type == "cuda":
        # Optimize for NVIDIA GPU
        torch.backends.cudnn.benchmark = True
        logger.info("🔧 Enabled cuDNN benchmark for optimal CUDA performance")
    
    return device

# Global device configuration
DEVICE = configure_ocr_device()

def get_device():
    """Get the configured device for processing"""
    return DEVICE

def get_device_info():
    """Get detailed device information"""
    device = get_device()
    
    info = {
        "device_type": device.type,
        "device_name": str(device),
        "torch_version": torch.__version__,
    }
    
    if device.type == "mps":
        info.update({
            "mps_available": torch.backends.mps.is_available(),
            "mps_built": torch.backends.mps.is_built(),
            "acceleration": "Apple Silicon GPU"
        })
    elif device.type == "cuda":
        info.update({
            "cuda_version": torch.version.cuda,
            "cuda_device_count": torch.cuda.device_count(),
            "cuda_device_name": torch.cuda.get_device_name() if torch.cuda.is_available() else None,
            "acceleration": "NVIDIA GPU"
        })
    else:
        info.update({
            "acceleration": "CPU Only"
        })
    
    return info