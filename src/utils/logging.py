#!/usr/bin/env python3

"""Logging configuration"""

import logging
import sys
from pathlib import Path
from typing import Optional

def setup_logging(log_file: Optional[str] = None, level: str = "INFO") -> None:
    """Configure logging
    
    Args:
        log_file: Path to log file (optional)
        level: Logging level
    """
    # Create logs directory if needed
    if log_file:
        log_dir = Path(log_file).parent
        log_dir.mkdir(exist_ok=True)
    
    # Configure logging
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers
    ) 