"""
End-to-end encryption utilities using X25519 key exchange and XChaCha20-Poly1305 AEAD.

This module provides session-level encryption on top of TLS for zero-knowledge processing.
"""
import base64
import secrets
from typing import Optional, Tuple

from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305


class SessionCrypto:
    """Manages ephemeral X25519 session key exchange and AEAD encryption."""
    
    def __init__(self):
        """Initialize with a new ephemeral X25519 private key."""
        self.private_key = x25519.X25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        
    def get_public_key_b64(self) -> str:
        """Return the server's public key as base64."""
        raw_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        return base64.b64encode(raw_bytes).decode('utf-8')
    
    def derive_shared_secret(self, client_pubkey_b64: str) -> bytes:
        """
        Derive shared secret from client's public key using X25519 ECDH.
        
        Args:
            client_pubkey_b64: Client's X25519 public key as base64
            
        Returns:
            32-byte shared secret
        """
        client_pubkey_raw = base64.b64decode(client_pubkey_b64)
        client_public_key = x25519.X25519PublicKey.from_public_bytes(client_pubkey_raw)
        shared_secret = self.private_key.exchange(client_public_key)
        return shared_secret
    
    @staticmethod
    def decrypt_payload(
        ciphertext: bytes,
        shared_secret: bytes,
        nonce: Optional[bytes] = None
    ) -> bytes:
        """
        Decrypt payload using XChaCha20-Poly1305 AEAD.
        
        Args:
            ciphertext: Encrypted data (includes 16-byte auth tag at the end)
            shared_secret: 32-byte shared secret from key exchange
            nonce: 24-byte nonce (extracted from first 24 bytes of ciphertext if None)
            
        Returns:
            Decrypted plaintext
            
        Raises:
            cryptography.exceptions.InvalidTag: If authentication fails
        """
        if nonce is None:
            # Extract nonce from first 24 bytes
            nonce = ciphertext[:24]
            ciphertext = ciphertext[24:]
        
        # Use XChaCha20Poly1305 (supports 24-byte nonce)
        cipher = ChaCha20Poly1305(shared_secret)
        plaintext = cipher.decrypt(nonce, ciphertext, associated_data=None)
        return plaintext
    
    @staticmethod
    def encrypt_payload(
        plaintext: bytes,
        shared_secret: bytes,
        nonce: Optional[bytes] = None
    ) -> Tuple[bytes, bytes]:
        """
        Encrypt payload using XChaCha20-Poly1305 AEAD.
        
        Args:
            plaintext: Data to encrypt
            shared_secret: 32-byte shared secret from key exchange
            nonce: 24-byte nonce (randomly generated if None)
            
        Returns:
            Tuple of (ciphertext with prepended nonce, nonce)
        """
        if nonce is None:
            nonce = secrets.token_bytes(24)  # XChaCha20Poly1305 uses 24-byte nonce
        
        cipher = ChaCha20Poly1305(shared_secret)
        ciphertext = cipher.encrypt(nonce, plaintext, associated_data=None)
        
        # Prepend nonce to ciphertext for convenience
        return nonce + ciphertext, nonce
    
    @staticmethod
    def secure_wipe(data: bytearray) -> None:
        """
        Securely wipe sensitive data from memory.
        
        Args:
            data: Bytearray to wipe
        """
        if isinstance(data, bytearray):
            for i in range(len(data)):
                data[i] = 0


def parse_session_crypto_header(client_pubkey: str) -> Optional[str]:
    """
    Validate and parse client session crypto header.
    
    Args:
        client_pubkey: Base64-encoded client public key
        
    Returns:
        Validated base64 string or None if invalid
    """
    try:
        # Validate it's valid base64 and correct length (32 bytes for X25519)
        raw = base64.b64decode(client_pubkey)
        if len(raw) != 32:
            return None
        return client_pubkey
    except Exception:
        return None


# Global session crypto instance (ephemeral per server instance)
# For production, consider rotating this periodically or per-connection
_server_session = SessionCrypto()


def get_server_session() -> SessionCrypto:
    """Get the global server session crypto instance."""
    return _server_session
