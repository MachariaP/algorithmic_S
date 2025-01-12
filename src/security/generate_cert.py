#!/usr/bin/env python3

"""
SSL Certificate Generator

Generates self-signed SSL certificates for development/testing.
"""

from pathlib import Path
import subprocess
import sys

def generate_self_signed_cert(cert_dir: Path = Path("ssl")) -> None:
    """Generate self-signed SSL certificate and key"""
    
    cert_dir.mkdir(exist_ok=True)
    cert_path = cert_dir / "server.crt"
    key_path = cert_dir / "server.key"
    
    # Generate private key
    subprocess.run([
        "openssl", "genrsa",
        "-out", str(key_path),
        "2048"
    ], check=True)
    
    # Generate certificate
    subprocess.run([
        "openssl", "req", "-new",
        "-x509",
        "-key", str(key_path),
        "-out", str(cert_path),
        "-days", "365",
        "-subj", "/CN=localhost"
    ], check=True)
    
    print(f"Generated certificate: {cert_path}")
    print(f"Generated private key: {key_path}")

if __name__ == "__main__":
    try:
        generate_self_signed_cert()
    except subprocess.CalledProcessError as e:
        print(f"Error generating certificates: {e}", file=sys.stderr)
        sys.exit(1)
