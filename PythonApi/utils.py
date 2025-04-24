import re
import os
import logging
from typing import Dict, Any
from logging.handlers import RotatingFileHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def validate_request_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and clean request data.
    
    Args:
        data: Dictionary containing request parameters
        
    Returns:
        Dictionary with validated and cleaned parameters
        
    Raises:
        ValueError: If required parameters are missing or invalid
    """
    if not data:
        raise ValueError("Request body is empty")
    
    keyword = data.get("text", "")
    if not keyword or not isinstance(keyword, str):
        raise ValueError("Text parameter is required and must be a string")
    
    keyword = keyword.strip()
    if not keyword:
        raise ValueError("Text parameter cannot be empty after trimming")
    
    max_results = data.get("maxResults", 100)
    if not isinstance(max_results, int) or max_results <= 0:
        max_results = 100  # Default if invalid
    
    # Limit max_results to a reasonable value to prevent abuse
    max_results = min(max_results, 500)
    
    return {
        "text": keyword,
        "maxResults": max_results
    }

def setup_logging(log_level=logging.INFO, log_file="python_api.log"):
    """
    Set up application-wide logging configuration with console and file output.
    
    Args:
        log_level: The logging level to use
        log_file: Path to the log file
    """
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file_path = os.path.join(log_dir, log_file)
    
    # Set up root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatters
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation (10 MB per file, max 5 backup files)
    file_handler = RotatingFileHandler(
        log_file_path, 
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
