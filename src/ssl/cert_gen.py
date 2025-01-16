#!/usr/bin/env python3

"""
SSL Certificate Generator

This script generates self-signed SSL certificates for the string search server.
It creates both the certificate and private key files needed for SSL/TLS.
"""

import os
from pathlib import Path
from OpenSSL import crypto
from typing import Optional


def generate_self_signed_cert(
    cert_path: str,
    key_path: str,
    country: str = "US",
    state: str = "State",
    locality: str = "City",
    organization: str = "Organization",
    organizational_unit: str = "Unit",
    common_name: str = "localhost",
    days_valid: int = 365
) -> None:
    """Generate self-signed SSL certificate"""
    # Generate key
    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA, 2048)

    # Generate certificate
    cert = crypto.X509()
    cert.get_subject().C = country
    cert.get_subject().ST = state
    cert.get_subject().L = locality
    cert.get_subject().O = organization
    cert.get_subject().OU = organizational_unit
    cert.get_subject().CN = common_name
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(days_valid * 24 * 60 * 60)
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(k)
    cert.sign(k, 'sha256')

    # Save certificate and private key
    with open(cert_path, "wb") as f:
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    with open(key_path, "wb") as f:
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))


if __name__ == "__main__":
    cert_file, key_file = generate_self_signed_cert()
    print(f"Generated SSL certificate: {cert_file}")
    print(f"Generated private key: {key_file}")
