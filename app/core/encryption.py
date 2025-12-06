"""
Encryption utilities for secure file and data storage.
Uses AES-256-GCM for authenticated encryption.
"""

import base64
import os
from typing import Tuple, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import hashlib
import logging

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Custom exception for encryption-related errors"""
    pass


class EncryptionUtils:
    """Utility class for encryption/decryption operations"""
    
    @staticmethod
    def generate_key() -> str:
        """
        Generate a new 256-bit encryption key.
        Returns base64-encoded key string.
        
        WARNING: Only use this for initial setup. Store the key securely
        and never regenerate in production without proper key rotation.
        """
        key = AESGCM.generate_key(bit_length=256)
        return base64.b64encode(key).decode('utf-8')
    
    @staticmethod
    def validate_key(key_b64: str) -> bool:
        """
        Validate that a base64-encoded key is valid for AES-256.
        
        Args:
            key_b64: Base64-encoded key string
            
        Returns:
            True if valid, False otherwise
        """
        try:
            key_bytes = base64.b64decode(key_b64)
            return len(key_bytes) == 32  # 256 bits = 32 bytes
        except Exception:
            return False
    
    @staticmethod
    def encrypt_bytes(
        plaintext: bytes,
        key_b64: str,
        associated_data: Optional[bytes] = None
    ) -> Tuple[bytes, bytes, bytes]:
        """
        Encrypt bytes using AES-256-GCM.
        
        Args:
            plaintext: Data to encrypt
            key_b64: Base64-encoded encryption key
            associated_data: Optional additional authenticated data (not encrypted)
            
        Returns:
            Tuple of (ciphertext, iv, tag) - all as bytes
            
        Raises:
            EncryptionError: If encryption fails
        """
        try:
            # Decode key
            key = base64.b64decode(key_b64)
            
            # Generate random IV (12 bytes recommended for GCM)
            iv = os.urandom(12)
            
            # Create cipher and encrypt
            aesgcm = AESGCM(key)
            ciphertext = aesgcm.encrypt(iv, plaintext, associated_data)
            
            # GCM mode appends the tag to ciphertext
            # Split: last 16 bytes are the tag
            tag = ciphertext[-16:]
            ciphertext_only = ciphertext[:-16]
            
            return ciphertext_only, iv, tag
            
        except Exception as e:
            logger.error(f"Encryption failed: {type(e).__name__}")
            raise EncryptionError("Encryption operation failed") from e
    
    @staticmethod
    def decrypt_bytes(
        ciphertext: bytes,
        iv: bytes,
        tag: bytes,
        key_b64: str,
        associated_data: Optional[bytes] = None
    ) -> bytes:
        """
        Decrypt bytes using AES-256-GCM.
        
        Args:
            ciphertext: Encrypted data
            iv: Initialization vector
            tag: Authentication tag
            key_b64: Base64-encoded encryption key
            associated_data: Optional additional authenticated data
            
        Returns:
            Decrypted plaintext bytes
            
        Raises:
            EncryptionError: If decryption or authentication fails
        """
        try:
            # Decode key
            key = base64.b64decode(key_b64)
            
            # Reconstruct full ciphertext with tag
            ciphertext_with_tag = ciphertext + tag
            
            # Create cipher and decrypt
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(iv, ciphertext_with_tag, associated_data)
            
            return plaintext
            
        except Exception as e:
            logger.error(f"Decryption failed: {type(e).__name__}")
            raise EncryptionError("Decryption operation failed") from e
    
    @staticmethod
    def compute_checksum(data: bytes) -> str:
        """
        Compute SHA-256 checksum of data.
        
        Args:
            data: Bytes to checksum
            
        Returns:
            Hex-encoded checksum string
        """
        return hashlib.sha256(data).hexdigest()
    
    @staticmethod
    def encode_for_storage(data: bytes) -> str:
        """
        Encode bytes as base64 string for text storage.
        
        Args:
            data: Bytes to encode
            
        Returns:
            Base64-encoded string
        """
        return base64.b64encode(data).decode('utf-8')
    
    @staticmethod
    def decode_from_storage(data_b64: str) -> bytes:
        """
        Decode base64 string back to bytes.
        
        Args:
            data_b64: Base64-encoded string
            
        Returns:
            Original bytes
        """
        return base64.b64decode(data_b64)


# Convenience functions for common operations

def encrypt_file_data(
    file_bytes: bytes,
    encryption_key: str
) -> Tuple[bytes, str, str, str]:
    """
    Encrypt file data and return all components needed for storage.
    
    Args:
        file_bytes: File content to encrypt
        encryption_key: Base64-encoded encryption key
        
    Returns:
        Tuple of (ciphertext, iv_b64, tag_b64, checksum)
    """
    # Compute checksum of original data
    checksum = EncryptionUtils.compute_checksum(file_bytes)
    
    # Encrypt
    ciphertext, iv, tag = EncryptionUtils.encrypt_bytes(file_bytes, encryption_key)
    
    # Encode for storage
    iv_b64 = EncryptionUtils.encode_for_storage(iv)
    tag_b64 = EncryptionUtils.encode_for_storage(tag)
    
    return ciphertext, iv_b64, tag_b64, checksum


def decrypt_file_data(
    ciphertext: bytes,
    iv_b64: str,
    tag_b64: str,
    encryption_key: str,
    verify_checksum: Optional[str] = None
) -> bytes:
    """
    Decrypt file data and optionally verify checksum.
    
    Args:
        ciphertext: Encrypted data
        iv_b64: Base64-encoded IV
        tag_b64: Base64-encoded authentication tag
        encryption_key: Base64-encoded encryption key
        verify_checksum: Optional checksum to verify against
        
    Returns:
        Decrypted file bytes
        
    Raises:
        EncryptionError: If decryption fails or checksum doesn't match
    """
    # Decode IV and tag
    iv = EncryptionUtils.decode_from_storage(iv_b64)
    tag = EncryptionUtils.decode_from_storage(tag_b64)
    
    # Decrypt
    plaintext = EncryptionUtils.decrypt_bytes(ciphertext, iv, tag, encryption_key)
    
    # Verify checksum if provided
    if verify_checksum:
        actual_checksum = EncryptionUtils.compute_checksum(plaintext)
        if actual_checksum != verify_checksum:
            raise EncryptionError("Checksum verification failed - data may be corrupted")
    
    return plaintext

