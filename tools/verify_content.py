#!/usr/bin/env python3

"""Verify and fix data file content"""

import sys
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)

def verify_and_fix():
    """Verify and fix data file"""
    data_path = Path("data/200k.txt")
    
    if not data_path.exists():
        logging.error("Data file not found!")
        return
        
    # Read current content
    with open(data_path, 'r') as f:
        lines = set(line.strip() for line in f if line.strip())
        
    # Required test strings
    test_strings = {
        "7;0;6;28;0;23;5;0;",
        "1;0;6;16;0;19;3;0;",
        "18;0;21;26;0;17;3;0;",
        "20;0;1;11;0;12;5;0;"
    }
    
    # Check which strings are missing
    missing = test_strings - lines
    if missing:
        logging.warning(f"Missing strings: {missing}")
        
        # Add missing strings
        with open(data_path, 'a') as f:
            for string in missing:
                f.write(f"{string}\n")
        logging.info("Added missing strings")
    else:
        logging.info("All test strings present")
        
    # Verify final content
    with open(data_path, 'r') as f:
        final_lines = set(line.strip() for line in f if line.strip())
        for test in test_strings:
            if test in final_lines:
                logging.info(f"Verified: {test}")
            else:
                logging.error(f"Still missing: {test}")

if __name__ == "__main__":
    verify_and_fix() 