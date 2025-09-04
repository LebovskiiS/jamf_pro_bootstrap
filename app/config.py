"""
Application Configuration
Module for loading configuration from Vault and environment variables
"""

import os
import logging
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class Config:
    """Base configuration class"""
    
    def __init__(self):
        self.config = {}
        self._load_config()
    
    def _load_config(self):
        """Load configuration from various sources"""
        
        vault_config = self._load_from_vault()
        if vault_config:
            self.config.update(vault_config)
            logger.info("Configuration loaded from Vault")
        
        env_config = self._load_from_env()
        self.config.update(env_config)
        
        default_config = self._get_default_config()
        for key, value in default_config.items():
            if key not in self.config or not self.config[key]:
                self.config[key] = value
    
    def _load_from_vault(self) -> Dict[str, str]:
        """Load configuration from Vault"""
        try:
            if not (os.getenv('VAULT_ADDR') and os.getenv('VAULT_TOKEN')):
                logger.info("Vault not configured, skipping Vault loading")
                return {}
            
            from .vault_client import VaultClient
            vault_client = VaultClient()
            
            test_result = vault_client.test_connection()
            if not test_result['connected'] or not test_result['authenticated']:
                logger.warning(f"Failed to connect to Vault: {test_result.get('error')}")
                return {}
            
            environment = os.getenv('FLASK_ENV', 'dev')
            if environment not in ['dev', 'prod']:
                environment = 'dev'
            
            return vault_client.get_jamf_config(environment)
            
        except Exception as e:
            logger.error(f"Failed to load config from Vault: {e}")
            return {}
    
    def _load_from_env(self) -> Dict[str, str]:
        """Load configuration from environment variables"""
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
        """Get default configuration"""
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
        """Get configuration value"""
        return self.config.get(key, default)
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean configuration value"""
        value = self.config.get(key, default)
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)
    
    def get_int(self, key: str, default: int = 0) -> int:
        """Get integer configuration value"""
        value = self.config.get(key, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def to_dict(self) -> Dict[str, Any]:
        """Get all configuration as dictionary"""
        return self.config.copy()
    
    def is_vault_enabled(self) -> bool:
        """Check if Vault integration is enabled"""
        return bool(os.getenv('VAULT_ADDR') and os.getenv('VAULT_TOKEN'))
    
    def get_vault_status(self) -> Dict[str, Any]:
        """Get Vault connection status"""
        if not self.is_vault_enabled():
            return {
                'enabled': False,
                'reason': 'Vault not configured (missing VAULT_ADDR or VAULT_TOKEN)'
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

# Global configuration instance
config = Config()
