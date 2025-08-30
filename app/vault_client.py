"""
HashiCorp Vault Client
Модуль для работы с HashiCorp Vault для получения секретов
"""

import os
import logging
from typing import Dict, Optional, Any
import hvac

logger = logging.getLogger(__name__)

class VaultClient:
    """Клиент для работы с HashiCorp Vault"""
    
    def __init__(self, vault_url: Optional[str] = None, auth_method: str = 'token'):
        """
        Инициализация клиента Vault
        
        Args:
            vault_url: URL сервера Vault (по умолчанию из VAULT_ADDR)
            auth_method: Метод аутентификации (token, approle, kubernetes, gcp)
        """
        self.vault_url = vault_url or os.getenv('VAULT_ADDR')
        self.auth_method = auth_method
        
        if not self.vault_url:
            raise ValueError("Vault URL не указан. Установите VAULT_ADDR или передайте vault_url")
        
        self.client = hvac.Client(url=self.vault_url)
        self._authenticate()
    
    def _authenticate(self):
        """Аутентификация в Vault"""
        try:
            if self.auth_method == 'token':
                self._authenticate_with_token()
            elif self.auth_method == 'approle':
                self._authenticate_with_approle()
            elif self.auth_method == 'kubernetes':
                self._authenticate_with_kubernetes()
            elif self.auth_method == 'gcp':
                self._authenticate_with_gcp()
            else:
                raise ValueError(f"Неподдерживаемый метод аутентификации: {self.auth_method}")
                
        except Exception as e:
            logger.error(f"Ошибка аутентификации в Vault: {e}")
            raise
    
    def _authenticate_with_token(self):
        """Аутентификация с помощью токена"""
        token = os.getenv('VAULT_TOKEN')
        if not token:
            raise ValueError("Vault токен не указан. Установите VAULT_TOKEN")
        
        self.client.token = token
    
    def _authenticate_with_approle(self):
        """Аутентификация с помощью AppRole"""
        role_id = os.getenv('VAULT_ROLE_ID')
        secret_id = os.getenv('VAULT_SECRET_ID')
        
        if not role_id or not secret_id:
            raise ValueError("AppRole не настроен. Установите VAULT_ROLE_ID и VAULT_SECRET_ID")
        
        response = self.client.auth.approle.login(
            role_id=role_id,
            secret_id=secret_id
        )
        
        if response and 'auth' in response:
            self.client.token = response['auth']['client_token']
        else:
            raise ValueError("Не удалось получить токен через AppRole")
    
    def _authenticate_with_kubernetes(self):
        """Аутентификация с помощью Kubernetes"""
        role = os.getenv('VAULT_K8S_ROLE')
        jwt = os.getenv('VAULT_K8S_JWT')
        
        if not role or not jwt:
            raise ValueError("Kubernetes аутентификация не настроена")
        
        response = self.client.auth.kubernetes.login(
            role=role,
            jwt=jwt
        )
        
        if response and 'auth' in response:
            self.client.token = response['auth']['client_token']
        else:
            raise ValueError("Не удалось получить токен через Kubernetes")
    
    def _authenticate_with_gcp(self):
        """Аутентификация с помощью GCP IAM"""
        role = os.getenv('VAULT_GCP_ROLE')
        jwt = os.getenv('VAULT_GCP_JWT')
        
        if not role or not jwt:
            raise ValueError("GCP аутентификация не настроена")
        
        response = self.client.auth.gcp.login(
            role=role,
            jwt=jwt
        )
        
        if response and 'auth' in response:
            self.client.token = response['auth']['client_token']
        else:
            raise ValueError("Не удалось получить токен через GCP IAM")
    
    def is_authenticated(self) -> bool:
        """Проверка аутентификации в Vault"""
        try:
            return self.client.is_authenticated()
        except Exception as e:
            logger.error(f"Ошибка проверки аутентификации Vault: {e}")
            return False
    
    def get_secret(self, path: str, key: Optional[str] = None) -> Any:
        """
        Получение секрета из Vault
        
        Args:
            path: Путь к секрету в Vault (например, 'secret/jamf-pro')
            key: Ключ секрета (если None, возвращает весь секрет)
            
        Returns:
            Значение секрета или None если не найден
        """
        try:
            if not self.is_authenticated():
                logger.error("Не удалось аутентифицироваться в Vault")
                return None
            
            # Читаем секрет
            secret_response = self.client.secrets.kv.v2.read_secret_version(path=path)
            
            if secret_response and 'data' in secret_response:
                secret_data = secret_response['data']['data']
                
                if key:
                    return secret_data.get(key)
                else:
                    return secret_data
            else:
                logger.warning(f"Секрет не найден по пути: {path}")
                return None
                
        except hvac.exceptions.InvalidPath:
            logger.warning(f"Путь к секрету не найден: {path}")
            return None
        except Exception as e:
            logger.error(f"Ошибка получения секрета из Vault: {e}")
            return None
    
    def get_jamf_config(self, environment: str = 'dev') -> Dict[str, str]:
        """
        Получение конфигурации Jamf Pro из Vault
        
        Args:
            environment: Окружение (dev/prod)
            
        Returns:
            Словарь с конфигурацией Jamf Pro
        """
        config = {}
        
        # Получаем конфигурацию Jamf Pro для конкретного окружения
        jamf_secret = self.get_secret(f'secret/jamf-pro-{environment}')
        if jamf_secret:
            config.update({
                'JAMF_PRO_URL': jamf_secret.get('url', ''),
                'JAMF_PRO_USERNAME': jamf_secret.get('username', ''),
                'JAMF_PRO_PASSWORD': jamf_secret.get('password', ''),
                'JAMF_PRO_CLIENT_ID': jamf_secret.get('client_id', ''),
                'JAMF_PRO_CLIENT_SECRET': jamf_secret.get('client_secret', ''),
                'JAMF_PRO_API_KEY': jamf_secret.get('api_key', '')
            })
        
        # Получаем общие настройки приложения для окружения
        app_secret = self.get_secret(f'secret/jamf-bootstrap-{environment}')
        if app_secret:
            config.update({
                'SECRET_KEY': app_secret.get('secret_key', 'dev-secret-key'),
                'FLASK_ENV': environment,
                'FLASK_DEBUG': app_secret.get('flask_debug', 'True'),
                'DATABASE_URL': app_secret.get('database_url', ''),
                'ENCRYPTION_KEY': app_secret.get('encryption_key', ''),
                'API_SECRET': app_secret.get('api_secret', '')
            })
        
        return config
    
    def get_encryption_key(self, environment: str = 'dev') -> Optional[str]:
        """
        Получение ключа шифрования из Vault
        
        Args:
            environment: Окружение (dev/prod)
            
        Returns:
            Ключ шифрования или None
        """
        app_secret = self.get_secret(f'secret/jamf-bootstrap-{environment}')
        if app_secret:
            return app_secret.get('encryption_key')
        return None
    
    def validate_api_key(self, api_key: str, environment: str = 'dev') -> bool:
        """
        Проверка валидности API ключа
        
        Args:
            api_key: API ключ для проверки
            environment: Окружение (dev/prod)
            
        Returns:
            True если ключ валиден, False иначе
        """
        stored_key = self.get_secret(f'secret/jamf-bootstrap-{environment}', 'api_secret')
        return stored_key == api_key
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Тестирование подключения к Vault
        
        Returns:
            Словарь с результатами тестирования
        """
        result = {
            'connected': False,
            'authenticated': False,
            'auth_method': self.auth_method,
            'error': None
        }
        
        try:
            # Проверяем подключение
            self.client.sys.read_health_status()
            result['connected'] = True
            
            # Проверяем аутентификацию
            result['authenticated'] = self.is_authenticated()
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Ошибка подключения к Vault: {e}")
        
        return result
