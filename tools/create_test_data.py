#!/usr/bin/env python3

"""Create test data file"""

from pathlib import Path
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def create_test_data():
    """Create test data file with guaranteed content"""
    data_path = Path("data/200k.txt")
    data_path.parent.mkdir(exist_ok=True)
    
    # Test strings that must be present
    test_strings = {  # Using set for uniqueness
        "7;0;6;28;0;23;5;0;",
        "1;0;6;16;0;19;3;0;",
        "18;0;21;26;0;17;3;0;",
        "20;0;1;11;0;12;5;0;"
    }
    
    logging.info(f"Creating test data at {data_path}")
    
    try:
        # Create file with test strings
        with open(data_path, 'w', encoding='utf-8', newline='\n') as f:
            # Write test strings first
            for string in sorted(test_strings):  # Sort for consistency
                f.write(f"{string}\n")
            
            # Generate additional data
            for i in range(1000):
                pattern = f"{i};0;{i+1};{i+2};0;{i+3};{i%5};0;"
                f.write(f"{pattern}\n")
        
        # Verify content
        with open(data_path, 'r', encoding='utf-8') as f:
            content = set(line.strip() for line in f if line.strip())
            
        # Check each test string
        missing = test_strings - content
        if missing:
            logging.error(f"Missing test strings: {missing}")
            sys.exit(1)
        else:
            for test in test_strings:
                logging.info(f"✓ Verified: {test}")
            
        # Print statistics
        file_size = data_path.stat().st_size
        logging.info(f"Created file with {len(content):,} lines ({file_size:,} bytes)")
        
    except Exception as e:
        logging.error(f"Error creating test data: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_test_data() 