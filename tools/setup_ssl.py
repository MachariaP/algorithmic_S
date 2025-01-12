#!/usr/bin/env python3

"""SSL Certificate Setup"""

import os
from pathlib import Path
from src.ssl.cert_gen import generate_self_signed_cert

def main():
    """Generate SSL certificates"""
    ssl_dir = Path("ssl")
    ssl_dir.mkdir(exist_ok=True)
    
    key_path, cert_path = generate_self_signed_cert(ssl_dir)
    print(f"\nSSL certificates generated:")
    print(f"Certificate: {cert_path}")
    print(f"Private key: {key_path}")
    print("\nUpdate config.ini to enable SSL:")
    print("ssl_enabled = true")
    print(f"ssl_cert_path = {cert_path}")
    print(f"ssl_key_path = {key_path}")

if __name__ == "__main__":
    main() 