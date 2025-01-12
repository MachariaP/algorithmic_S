#!/usr/bin/env python3

"""
SSL Certificate Generator for String Search Server

Generates self-signed SSL certificates for development and testing.
For production, use certificates from a trusted CA.

Author: Phinehas Macharia
Date: 2025
"""

import os
import sys
import argparse
from pathlib import Path
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import datetime

def generate_ssl_cert(output_dir: Path, common_name: str = "localhost") -> tuple:
    """Generate SSL certificate and private key"""
    # Generate key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    
    # Generate certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "String Search Server"),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Development"),
    ])
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([x509.DNSName(common_name)]),
        critical=False,
    ).sign(private_key, hashes.SHA256())
    
    # Save files
    cert_path = output_dir / "server.crt"
    key_path = output_dir / "server.key"
    
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ))
    
    return cert_path, key_path

def main():
    parser = argparse.ArgumentParser(description="Generate SSL certificates")
    parser.add_argument(
        "-o", "--output",
        default="ssl",
        help="Output directory for certificates"
    )
    parser.add_argument(
        "-n", "--name",
        default="localhost",
        help="Common name for certificate"
    )
    
    args = parser.parse_args()
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)
    
    try:
        cert_path, key_path = generate_ssl_cert(output_dir, args.name)
        print(f"Generated SSL certificate: {cert_path}")
        print(f"Generated private key: {key_path}")
        print("\nUpdate config.ini with these paths:")
        print("[SSL]")
        print(f"SSL_CERT = {cert_path}")
        print(f"SSL_KEY = {key_path}")
    except Exception as e:
        print(f"Error generating certificates: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 
