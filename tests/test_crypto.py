"""Unit tests for crypto E2EE module."""
import pytest
from crypto.e2ee import SessionCrypto, parse_session_crypto_header, get_server_session


def test_session_crypto_key_generation():
    """Test X25519 key pair generation."""
    session = SessionCrypto()
    
    # Should have keys
    assert session.private_key is not None
    assert session.public_key is not None
    
    # Public key should be base64 encodable
    pubkey_b64 = session.get_public_key_b64()
    assert isinstance(pubkey_b64, str)
    assert len(pubkey_b64) > 0


def test_shared_secret_derivation():
    """Test ECDH shared secret derivation."""
    # Create two sessions (client and server)
    client_session = SessionCrypto()
    server_session = SessionCrypto()
    
    # Exchange public keys and derive secrets
    client_shared = client_session.derive_shared_secret(
        server_session.get_public_key_b64()
    )
    server_shared = server_session.derive_shared_secret(
        client_session.get_public_key_b64()
    )
    
    # Shared secrets should match
    assert client_shared == server_shared
    assert len(client_shared) == 32  # X25519 output is 32 bytes


def test_encrypt_decrypt_payload():
    """Test XChaCha20-Poly1305 encryption/decryption."""
    session = SessionCrypto()
    shared_secret = b"0" * 32  # Mock 32-byte secret
    
    plaintext = b"This is sensitive data"
    
    # Encrypt
    ciphertext, nonce = SessionCrypto.encrypt_payload(plaintext, shared_secret)
    
    # Should include nonce
    assert len(ciphertext) > len(plaintext)
    assert len(nonce) == 24  # XChaCha20 nonce
    
    # Decrypt
    decrypted = SessionCrypto.decrypt_payload(ciphertext, shared_secret)
    
    assert decrypted == plaintext


def test_encrypt_decrypt_roundtrip():
    """Test full encryption/decryption roundtrip."""
    client_session = SessionCrypto()
    server_session = SessionCrypto()
    
    # Derive shared secret
    shared_secret = client_session.derive_shared_secret(
        server_session.get_public_key_b64()
    )
    
    # Encrypt on client
    plaintext = b"Secret document content" * 100
    encrypted, _ = SessionCrypto.encrypt_payload(plaintext, shared_secret)
    
    # Decrypt on server (using same shared secret)
    decrypted = SessionCrypto.decrypt_payload(encrypted, shared_secret)
    
    assert decrypted == plaintext


def test_invalid_pubkey_parsing():
    """Test invalid public key handling."""
    # Invalid base64
    assert parse_session_crypto_header("invalid!!!") is None
    
    # Wrong length
    import base64
    assert parse_session_crypto_header(base64.b64encode(b"short").decode()) is None
    
    # Valid format
    valid_key = base64.b64encode(b"0" * 32).decode()
    assert parse_session_crypto_header(valid_key) == valid_key


def test_decryption_with_wrong_key_fails():
    """Test that decryption fails with wrong key."""
    shared_secret = b"0" * 32
    wrong_secret = b"1" * 32
    
    plaintext = b"Test data"
    ciphertext, _ = SessionCrypto.encrypt_payload(plaintext, shared_secret)
    
    # Should raise exception
    with pytest.raises(Exception):
        SessionCrypto.decrypt_payload(ciphertext, wrong_secret)


def test_server_session_singleton():
    """Test global server session."""
    session1 = get_server_session()
    session2 = get_server_session()
    
    # Should be same instance
    assert session1 is session2
    assert session1.get_public_key_b64() == session2.get_public_key_b64()


def test_secure_wipe():
    """Test secure memory wiping."""
    data = bytearray(b"sensitive" * 10)
    original_len = len(data)
    
    SessionCrypto.secure_wipe(data)
    
    # Should be all zeros
    assert len(data) == original_len
    assert all(b == 0 for b in data)
