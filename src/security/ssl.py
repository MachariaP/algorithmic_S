"""SSL/TLS wrapper"""

import socket
import ssl
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Union

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from ..config.models import SecurityConfig
from ..utils.errors import ConfigError, SecurityError


class SSLWrapper:
    """SSL/TLS wrapper for socket connections"""
    
    def __init__(self, config: SecurityConfig):
        """Initialize SSL wrapper
        
        Args:
            config: Security configuration
        """
        self.config = config
        self.context = self._create_context()
        
    def _create_context(self) -> ssl.SSLContext:
        """Create SSL context
        
        Returns:
            SSL context
            
        Raises:
            ConfigError: If SSL configuration is invalid
        """
        try:
            # Create context with TLS 1.3
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.minimum_version = ssl.TLSVersion.TLSv1_3
            
            # Load certificate and private key
            if self.config.ssl_enabled:
                if not self.config.cert_file or not self.config.key_file:
                    raise ConfigError("SSL certificate and key files are required")
                    
                context.load_cert_chain(
                    certfile=str(self.config.cert_file),
                    keyfile=str(self.config.key_file)
                )
                
            # Configure client authentication
            if self.config.client_auth:
                context.verify_mode = ssl.CERT_REQUIRED
                context.load_verify_locations(
                    cafile=str(self.config.cert_file)
                )
            else:
                context.verify_mode = ssl.CERT_NONE
                
            # Configure secure cipher suites
            context.set_ciphers("ECDHE+AESGCM:ECDHE+CHACHA20")
            
            # Enable OCSP stapling
            context.ocsp_stapling = True
            context.ocsp_stapling_callback = self._ocsp_callback
            
            # Additional security options
            context.options |= (
                ssl.OP_NO_SSLv2 |
                ssl.OP_NO_SSLv3 |
                ssl.OP_NO_TLSv1 |
                ssl.OP_NO_TLSv1_1 |
                ssl.OP_NO_COMPRESSION
            )
            
            return context
            
        except (ssl.SSLError, OSError) as e:
            raise ConfigError(f"Failed to create SSL context: {e}")
            
    def wrap_socket(
        self,
        sock: socket.socket,
        server_side: bool = True
    ) -> ssl.SSLSocket:
        """Wrap socket with SSL/TLS
        
        Args:
            sock: Socket to wrap
            server_side: Whether this is the server side
            
        Returns:
            SSL socket
            
        Raises:
            SecurityError: If SSL handshake fails
        """
        try:
            return self.context.wrap_socket(
                sock,
                server_side=server_side,
                do_handshake_on_connect=True
            )
        except ssl.SSLError as e:
            raise SecurityError(f"SSL handshake failed: {e}")
            
    def get_peer_certificate(
        self,
        ssl_socket: ssl.SSLSocket
    ) -> Optional[Dict[str, str]]:
        """Get peer certificate information
        
        Args:
            ssl_socket: SSL socket
            
        Returns:
            Certificate information or None if no certificate
            
        Raises:
            SecurityError: If certificate validation fails
        """
        try:
            cert = ssl_socket.getpeercert()
            if not cert:
                return None
                
            return {
                "subject": dict(x[0] for x in cert["subject"]),
                "issuer": dict(x[0] for x in cert["issuer"]),
                "version": cert["version"],
                "serialNumber": cert["serialNumber"],
                "notBefore": cert["notBefore"],
                "notAfter": cert["notAfter"]
            }
            
        except ssl.SSLError as e:
            raise SecurityError(f"Certificate validation failed: {e}")
            
    def _ocsp_callback(
        self,
        conn: Union[ssl.SSLSocket, ssl.SSLObject],
        ocsp_bytes: Optional[bytes],
        *args: Any
    ) -> bool:
        """OCSP stapling callback
        
        Args:
            conn: SSL connection
            ocsp_bytes: OCSP response bytes
            
        Returns:
            Whether OCSP response is valid
        """
        # TODO: Implement OCSP response validation
        return True
        
    @staticmethod
    def generate_self_signed_cert(
        cert_file: Path,
        key_file: Path,
        common_name: str = "localhost",
        country: str = "US",
        state: str = "CA",
        locality: str = "San Francisco",
        org: str = "Test Organization",
        org_unit: str = "Test Unit",
        validity_days: int = 365
    ) -> None:
        """Generate self-signed certificate
        
        Args:
            cert_file: Certificate file path
            key_file: Private key file path
            common_name: Certificate common name
            country: Certificate country
            state: Certificate state
            locality: Certificate locality
            org: Certificate organization
            org_unit: Certificate organizational unit
            validity_days: Certificate validity period in days
        """
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        
        # Create certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
            x509.NameAttribute(NameOID.COUNTRY_NAME, country),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, state),
            x509.NameAttribute(NameOID.LOCALITY_NAME, locality),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, org),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, org_unit)
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
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=validity_days)
        ).add_extension(
            x509.SubjectAlternativeName([x509.DNSName(common_name)]),
            critical=False
        ).sign(private_key, hashes.SHA256())
        
        # Save certificate
        with open(cert_file, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
            
        # Save private key
        with open(key_file, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))