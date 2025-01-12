#!/usr/bin/env python3

"""Verify data file format"""

from pathlib import Path
import logging
import sys

logging.basicConfig(level=logging.INFO)

def verify_format():
    """Verify data file format"""
    data_path = Path("data/200k.txt")
    
    if not data_path.exists():
        logging.error("Data file not found!")
        return False
        
    test_strings = {
        "7;0;6;28;0;23;5;0;",
        "1;0;6;16;0;19;3;0;",
        "18;0;21;26;0;17;3;0;",
        "20;0;1;11;0;12;5;0;"
    }
    
    try:
        with open(data_path, 'rb') as f:  # Open in binary mode to check exact bytes
            content = f.read()
            
        # Check for Windows line endings
        if b'\r\n' in content:
            logging.error("Found Windows line endings (CRLF)")
            return False
            
        # Convert to text and check strings
        text_content = content.decode('utf-8')
        lines = set(line.strip() for line in text_content.split('\n') if line.strip())
        
        # Verify test strings
        for test in test_strings:
            if test not in lines:
                logging.error(f"Missing test string: '{test}'")
                return False
            else:
                logging.info(f"Found test string: '{test}'")
                
        logging.info("All test strings present with correct format")
        return True
        
    except Exception as e:
        logging.error(f"Error verifying format: {e}")
        return False

if __name__ == "__main__":
    if not verify_format():
        sys.exit(1) 