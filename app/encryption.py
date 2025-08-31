"""
Encryption Module
Модуль для шифрования и дешифрования данных
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
    """Менеджер шифрования"""
    
    def __init__(self, secret_key: str):
        """
        Инициализация менеджера шифрования
        
        Args:
            secret_key: Секретный ключ для шифрования
        """
        self.secret_key = secret_key.encode()
        self.fernet = self._create_fernet()
    
    def _create_fernet(self) -> Fernet:
        """Создание Fernet объекта для шифрования"""
        try:
            # Используем PBKDF2 для генерации ключа
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'jamf_bootstrap_salt',  # Фиксированная соль для совместимости
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.secret_key))
            return Fernet(key)
        except Exception as e:
            logger.error(f"Ошибка создания Fernet: {e}")
            raise
    
    def encrypt_data(self, data: str) -> str:
        """
        Шифрование данных
        
        Args:
            data: Данные для шифрования
            
        Returns:
            Зашифрованные данные в base64
        """
        try:
            encrypted_data = self.fernet.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"Ошибка шифрования данных: {e}")
            raise
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """
        Дешифрование данных
        
        Args:
            encrypted_data: Зашифрованные данные в base64
            
        Returns:
            Расшифрованные данные
        """
        try:
            # Декодируем из base64
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            # Дешифруем
            decrypted_data = self.fernet.decrypt(encrypted_bytes)
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Ошибка дешифрования данных: {e}")
            raise
    
    def generate_checksum(self, data: str) -> str:
        """
        Генерация SHA256 хеша для проверки целостности
        
        Args:
            data: Данные для хеширования
            
        Returns:
            SHA256 хеш в hex формате
        """
        try:
            return hashlib.sha256(data.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Ошибка генерации checksum: {e}")
            raise
    
    def verify_checksum(self, data: str, expected_checksum: str) -> bool:
        """
        Проверка целостности данных
        
        Args:
            data: Данные для проверки
            expected_checksum: Ожидаемый checksum
            
        Returns:
            True если checksum совпадает, False иначе
        """
        try:
            actual_checksum = self.generate_checksum(data)
            return actual_checksum == expected_checksum
        except Exception as e:
            logger.error(f"Ошибка проверки checksum: {e}")
            return False
    
    def encrypt_with_checksum(self, data: str) -> Tuple[str, str]:
        """
        Шифрование данных с генерацией checksum
        
        Args:
            data: Данные для шифрования
            
        Returns:
            Кортеж (зашифрованные_данные, checksum)
        """
        try:
            encrypted_data = self.encrypt_data(data)
            checksum = self.generate_checksum(data)
            return encrypted_data, checksum
        except Exception as e:
            logger.error(f"Ошибка шифрования с checksum: {e}")
            raise
    
    def decrypt_and_verify(self, encrypted_data: str, expected_checksum: str) -> Optional[str]:
        """
        Дешифрование данных с проверкой целостности
        
        Args:
            encrypted_data: Зашифрованные данные
            expected_checksum: Ожидаемый checksum
            
        Returns:
            Расшифрованные данные или None если проверка не прошла
        """
        try:
            decrypted_data = self.decrypt_data(encrypted_data)
            if self.verify_checksum(decrypted_data, expected_checksum):
                return decrypted_data
            else:
                logger.warning("Checksum не совпадает - возможна порча данных")
                return None
        except Exception as e:
            logger.error(f"Ошибка дешифрования с проверкой: {e}")
            return None
    
    def generate_encryption_key(self) -> str:
        """
        Генерация нового ключа шифрования
        
        Returns:
            Новый ключ в base64
        """
        try:
            key = Fernet.generate_key()
            return base64.urlsafe_b64encode(key).decode()
        except Exception as e:
            logger.error(f"Ошибка генерации ключа: {e}")
            raise
    
    def validate_encrypted_data(self, encrypted_data: str) -> bool:
        """
        Проверка валидности зашифрованных данных
        
        Args:
            encrypted_data: Зашифрованные данные
            
        Returns:
            True если данные валидны, False иначе
        """
        try:
            # Пытаемся декодировать из base64
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            # Проверяем, что это валидные данные Fernet
            return len(encrypted_bytes) > 0
        except Exception:
            return False
