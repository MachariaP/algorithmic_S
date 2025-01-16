#!/usr/bin/env python3

"""SSL Configuration"""

import ssl
from pathlib import Path


def create_ssl_context(cert_dir: str = "ssl") -> ssl.SSLContext:
    """Create SSL context

    Args:
        cert_dir: Directory containing certificates

    Returns:
        Configured SSL context
    """
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    cert_path = Path(cert_dir) / "server.crt"
    key_path = Path(cert_dir) / "server.key"

    context.load_cert_chain(
        certfile=str(cert_path),
        keyfile=str(key_path)
    )

    return context


def create_client_context() -> ssl.SSLContext:
    """Create client SSL context"""
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context
