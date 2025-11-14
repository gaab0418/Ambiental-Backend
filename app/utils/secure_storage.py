"""
Secure Storage abstraction for encrypted file storage.
Supports local encrypted storage and cloud storage backends.
"""

import os
from pathlib import Path
from typing import Tuple, Optional
import logging
from app.config import settings
from app.core.encryption import encrypt_file_data, decrypt_file_data, EncryptionError

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Custom exception for storage operations"""
    pass


class SecureStorage:
    """
    Abstraction layer for secure file storage.
    Automatically selects backend based on configuration.
    """
    
    @staticmethod
    def _get_backend():
        """Get the appropriate storage backend based on config"""
        backend_type = settings.file_storage_backend
        
        if backend_type == "local_encrypted":
            return LocalEncryptedStorage()
        elif backend_type == "s3_encrypted":
            # Future implementation
            raise NotImplementedError("S3 storage backend not yet implemented")
        else:
            raise ValueError(f"Unknown storage backend: {backend_type}")
    
    @staticmethod
    def store_file(
        org_id: int,
        thread_id: int,
        file_bytes: bytes,
        filename: str,
        mime_type: str
    ) -> Tuple[str, int, str, str, str]:
        """
        Store a file securely with encryption.
        
        Args:
            org_id: Organization ID
            thread_id: Chat thread ID
            file_bytes: File content as bytes
            filename: Original filename
            mime_type: MIME type of the file
            
        Returns:
            Tuple of (storage_path, size_bytes, checksum, iv_b64, tag_b64)
            
        Raises:
            StorageError: If storage operation fails
        """
        backend = SecureStorage._get_backend()
        return backend.store_file(org_id, thread_id, file_bytes, filename, mime_type)
    
    @staticmethod
    def load_file(
        storage_path: str,
        iv_b64: str,
        tag_b64: str,
        checksum: Optional[str] = None
    ) -> bytes:
        """
        Load and decrypt a file.
        
        Args:
            storage_path: Path where file is stored
            iv_b64: Base64-encoded initialization vector
            tag_b64: Base64-encoded authentication tag
            checksum: Optional checksum to verify integrity
            
        Returns:
            Decrypted file bytes
            
        Raises:
            StorageError: If load or decryption fails
        """
        backend = SecureStorage._get_backend()
        return backend.load_file(storage_path, iv_b64, tag_b64, checksum)
    
    @staticmethod
    def delete_file(storage_path: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            storage_path: Path where file is stored
            
        Returns:
            True if deleted, False if not found
        """
        backend = SecureStorage._get_backend()
        return backend.delete_file(storage_path)


class LocalEncryptedStorage:
    """Local filesystem storage with encryption"""
    
    BASE_DIR = Path("uploads/chat_files")
    
    def __init__(self):
        # Ensure base directory exists
        self.BASE_DIR.mkdir(parents=True, exist_ok=True)
    
    def _get_storage_path(self, org_id: int, thread_id: int, filename: str) -> Path:
        """Generate storage path for a file"""
        # Create directory structure: uploads/chat_files/{org_id}/{thread_id}/
        org_dir = self.BASE_DIR / str(org_id)
        thread_dir = org_dir / str(thread_id)
        thread_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename with timestamp to avoid collisions
        import uuid
        import time
        timestamp = int(time.time())
        file_ext = Path(filename).suffix
        unique_filename = f"{timestamp}_{uuid.uuid4().hex}{file_ext}"
        
        return thread_dir / unique_filename
    
    def store_file(
        self,
        org_id: int,
        thread_id: int,
        file_bytes: bytes,
        filename: str,
        mime_type: str
    ) -> Tuple[str, int, str, str, str]:
        """
        Store file with encryption on local filesystem.
        
        Returns:
            Tuple of (storage_path, size_bytes, checksum, iv_b64, tag_b64)
        """
        try:
            # Check if encryption key is configured
            if not settings.file_encryption_key:
                raise StorageError("File encryption key not configured")
            
            # Encrypt file data
            ciphertext, iv_b64, tag_b64, checksum = encrypt_file_data(
                file_bytes,
                settings.file_encryption_key
            )
            
            # Get storage path
            storage_path = self._get_storage_path(org_id, thread_id, filename)
            
            # Write encrypted data to file
            with open(storage_path, 'wb') as f:
                f.write(ciphertext)
            
            # Calculate size
            size_bytes = len(file_bytes)
            
            # Return relative path from uploads directory
            relative_path = str(storage_path.relative_to(Path("uploads")))
            
            logger.info(
                f"Stored encrypted file for org {org_id}, thread {thread_id}: "
                f"{filename} ({size_bytes} bytes)"
            )
            
            return relative_path, size_bytes, checksum, iv_b64, tag_b64
            
        except StorageError:
            # Erros de configuração (ex.: chave ausente) já vêm como StorageError;
            # apenas propaga sem alterar a mensagem.
            raise
        except EncryptionError as e:
            logger.error(f"Encryption failed for file {filename}: {str(e)}")
            raise StorageError("Failed to encrypt file") from e
        except Exception as e:
            logger.error(f"Storage failed for file {filename}: {str(e)}")
            raise StorageError("Failed to store file") from e
    
    def load_file(
        self,
        storage_path: str,
        iv_b64: str,
        tag_b64: str,
        checksum: Optional[str] = None
    ) -> bytes:
        """
        Load and decrypt file from local filesystem.
        
        Returns:
            Decrypted file bytes
        """
        try:
            # Check if encryption key is configured
            if not settings.file_encryption_key:
                raise StorageError("File encryption key not configured")
            
            # Construct full path
            full_path = Path("uploads") / storage_path
            
            # Check if file exists
            if not full_path.exists():
                raise StorageError(f"File not found: {storage_path}")
            
            # Read encrypted data
            with open(full_path, 'rb') as f:
                ciphertext = f.read()
            
            # Decrypt
            plaintext = decrypt_file_data(
                ciphertext,
                iv_b64,
                tag_b64,
                settings.file_encryption_key,
                verify_checksum=checksum
            )
            
            logger.info(f"Loaded and decrypted file: {storage_path}")
            
            return plaintext
            
        except EncryptionError as e:
            logger.error(f"Decryption failed for file {storage_path}: {str(e)}")
            raise StorageError("Failed to decrypt file") from e
        except Exception as e:
            logger.error(f"Load failed for file {storage_path}: {str(e)}")
            raise StorageError("Failed to load file") from e
    
    def delete_file(self, storage_path: str) -> bool:
        """Delete file from local filesystem"""
        try:
            full_path = Path("uploads") / storage_path
            
            if full_path.exists() and full_path.is_file():
                full_path.unlink()
                logger.info(f"Deleted file: {storage_path}")
                return True
            else:
                logger.warning(f"File not found for deletion: {storage_path}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete file {storage_path}: {str(e)}")
            return False


# Singleton instance for easy access
secure_storage = SecureStorage()

