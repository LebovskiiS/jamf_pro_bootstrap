"""
Конфигурация приложения
Модуль для загрузки конфигурации из Vault и переменных окружения
"""

import os
import logging
from typing import Dict, Any
from dotenv import load_dotenv

# Загружаем .env файл для локальной разработки
load_dotenv()

logger = logging.getLogger(__name__)

class Config:
    """Базовый класс конфигурации"""
    
    def __init__(self):
        self.config = {}
        self._load_config()
    
    def _load_config(self):
        """Загрузка конфигурации из различных источников"""
        # Приоритет: Vault > Переменные окружения > Значения по умолчанию
        
        # 1. Пытаемся загрузить из Vault
        vault_config = self._load_from_vault()
        if vault_config:
            self.config.update(vault_config)
            logger.info("Конфигурация загружена из Vault")
        
        # 2. Загружаем из переменных окружения
        env_config = self._load_from_env()
        self.config.update(env_config)
        
        # 3. Устанавливаем значения по умолчанию
        default_config = self._get_default_config()
        for key, value in default_config.items():
            if key not in self.config or not self.config[key]:
                self.config[key] = value
    
    def _load_from_vault(self) -> Dict[str, str]:
        """Загрузка конфигурации из Vault"""
        try:
            # Проверяем, доступен ли Vault
            if not (os.getenv('VAULT_ADDR') and os.getenv('VAULT_TOKEN')):
                logger.info("Vault не настроен, пропускаем загрузку из Vault")
                return {}
            
            from .vault_client import VaultClient
            vault_client = VaultClient()
            
            # Тестируем подключение
            test_result = vault_client.test_connection()
            if not test_result['connected'] or not test_result['authenticated']:
                logger.warning(f"Не удалось подключиться к Vault: {test_result.get('error')}")
                return {}
            
            # Определяем окружение
            environment = os.getenv('FLASK_ENV', 'dev')
            if environment not in ['dev', 'prod']:
                environment = 'dev'
            
            # Получаем конфигурацию для конкретного окружения
            return vault_client.get_jamf_config(environment)
            
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации из Vault: {e}")
            return {}
    
    def _load_from_env(self) -> Dict[str, str]:
        """Загрузка конфигурации из переменных окружения"""
        env_vars = [
            'JAMF_PRO_URL',
            'JAMF_PRO_USERNAME', 
            'JAMF_PRO_PASSWORD',
            'JAMF_PRO_CLIENT_ID',
            'JAMF_PRO_CLIENT_SECRET',
            'SECRET_KEY',
            'FLASK_ENV',
            'FLASK_DEBUG',
            'DATABASE_URL'
        ]
        
        config = {}
        for var in env_vars:
            value = os.getenv(var)
            if value is not None:
                config[var] = value
        
        return config
    
    def _get_default_config(self) -> Dict[str, str]:
        """Получение конфигурации по умолчанию"""
        return {
            'SECRET_KEY': 'dev-secret-key-change-in-production',
            'FLASK_ENV': 'dev',
            'FLASK_DEBUG': 'True',
            'DATABASE_URL': '',
            'JAMF_PRO_URL': '',
            'JAMF_PRO_USERNAME': '',
            'JAMF_PRO_PASSWORD': '',
            'JAMF_PRO_CLIENT_ID': '',
            'JAMF_PRO_CLIENT_SECRET': '',
            'JAMF_PRO_API_KEY': '',
            'ENCRYPTION_KEY': '',
            'API_SECRET': ''
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Получение значения конфигурации"""
        return self.config.get(key, default)
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Получение булевого значения конфигурации"""
        value = self.config.get(key, default)
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)
    
    def get_int(self, key: str, default: int = 0) -> int:
        """Получение целочисленного значения конфигурации"""
        value = self.config.get(key, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def to_dict(self) -> Dict[str, Any]:
        """Получение всей конфигурации в виде словаря"""
        return self.config.copy()
    
    def is_vault_enabled(self) -> bool:
        """Проверка, включена ли интеграция с Vault"""
        return bool(os.getenv('VAULT_ADDR') and os.getenv('VAULT_TOKEN'))
    
    def get_vault_status(self) -> Dict[str, Any]:
        """Получение статуса подключения к Vault"""
        if not self.is_vault_enabled():
            return {
                'enabled': False,
                'reason': 'Vault не настроен (отсутствуют VAULT_ADDR или VAULT_TOKEN)'
            }
        
        try:
            from .vault_client import VaultClient
            vault_client = VaultClient()
            return vault_client.test_connection()
        except Exception as e:
            return {
                'enabled': True,
                'connected': False,
                'authenticated': False,
                'error': str(e)
            }

# Глобальный экземпляр конфигурации
config = Config()
