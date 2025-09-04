"""
Encryption Module
Module for data encryption and decryption
"""

import os
import base64
import hashlib
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class EncryptionManager:
    """Encryption manager"""
    
    def __init__(self, secret_key: str):
        """
        Initialize encryption manager
        
        Args:
            secret_key: Secret key for encryption
        """
        self.secret_key = secret_key.encode()
        self.fernet = self._create_fernet()
    
    def _create_fernet(self) -> Fernet:
        """Create Fernet object for encryption"""
        try:
            # Use PBKDF2 for key generation
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'jamf_bootstrap_salt',  # Fixed salt for compatibility
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.secret_key))
            return Fernet(key)
        except Exception as e:
            logger.error(f"Failed to create Fernet: {e}")
            raise
    
    def encrypt_data(self, data: str) -> str:
        """
        Encrypt data
        
        Args:
            data: Data to encrypt
            
        Returns:
            Encrypted data in base64
        """
        try:
            encrypted_data = self.fernet.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"Data encryption failed: {e}")
            raise
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """
        Decrypt data
        
        Args:
            encrypted_data: Encrypted data in base64
            
        Returns:
            Decrypted data
        """
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self.fernet.decrypt(encrypted_bytes)
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Data decryption failed: {e}")
            raise
    
    def generate_checksum(self, data: str) -> str:
        """
        Generate SHA256 hash for integrity verification
        
        Args:
            data: Data to hash
            
        Returns:
            SHA256 hash in hex format
        """
        try:
            return hashlib.sha256(data.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Checksum generation failed: {e}")
            raise
    
    def verify_checksum(self, data: str, expected_checksum: str) -> bool:
        """
        Verify data integrity
        
        Args:
            data: Data to verify
            expected_checksum: Expected checksum
            
        Returns:
            True if checksum matches, False otherwise
        """
        try:
            actual_checksum = self.generate_checksum(data)
            return actual_checksum == expected_checksum
        except Exception as e:
            logger.error(f"Checksum verification failed: {e}")
            return False
    
    def encrypt_with_checksum(self, data: str) -> Tuple[str, str]:
        """
        Encrypt data with checksum generation
        
        Args:
            data: Data to encrypt
            
        Returns:
            Tuple (encrypted_data, checksum)
        """
        try:
            encrypted_data = self.encrypt_data(data)
            checksum = self.generate_checksum(data)
            return encrypted_data, checksum
        except Exception as e:
            logger.error(f"Encryption with checksum failed: {e}")
            raise
    
    def decrypt_and_verify(self, encrypted_data: str, expected_checksum: str) -> Optional[str]:
        """
        Decrypt data with integrity verification
        
        Args:
            encrypted_data: Encrypted data
            expected_checksum: Expected checksum
            
        Returns:
            Decrypted data or None if verification failed
        """
        try:
            decrypted_data = self.decrypt_data(encrypted_data)
            if self.verify_checksum(decrypted_data, expected_checksum):
                return decrypted_data
            else:
                logger.warning("Checksum mismatch - possible data corruption")
                return None
        except Exception as e:
            logger.error(f"Decryption with verification failed: {e}")
            return None
    
    def generate_encryption_key(self) -> str:
        """
        Generate new encryption key
        
        Returns:
            New key in base64
        """
        try:
            key = Fernet.generate_key()
            return base64.urlsafe_b64encode(key).decode()
        except Exception as e:
            logger.error(f"Key generation failed: {e}")
            raise
    
    def validate_encrypted_data(self, encrypted_data: str) -> bool:
        """
        Validate encrypted data
        
        Args:
            encrypted_data: Encrypted data
            
        Returns:
            True if data is valid, False otherwise
        """
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            return len(encrypted_bytes) > 0
        except Exception:
            return False
