"""
HashiCorp Vault Client
Module for interacting with HashiCorp Vault to retrieve secrets
"""

import os
import logging
from typing import Dict, Optional, Any
import hvac

logger = logging.getLogger(__name__)

class VaultClient:
    """Client for HashiCorp Vault operations"""
    
    def __init__(self, vault_url: Optional[str] = None, auth_method: str = 'token'):
        """
        Initialize Vault client
        
        Args:
            vault_url: Vault server URL (defaults to VAULT_ADDR)
            auth_method: Authentication method (token, approle, gcp)
        """
        self.vault_url = vault_url or os.getenv('VAULT_ADDR')
        self.auth_method = auth_method
        
        if not self.vault_url:
            raise ValueError("Vault URL not specified. Set VAULT_ADDR or pass vault_url")
        
        self.client = hvac.Client(url=self.vault_url)
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Vault"""
        try:
            if self.auth_method == 'token':
                self._authenticate_with_token()
            elif self.auth_method == 'approle':
                self._authenticate_with_approle()
            elif self.auth_method == 'gcp':
                self._authenticate_with_gcp()
            else:
                raise ValueError(f"Unsupported authentication method: {self.auth_method}")
                
        except Exception as e:
            logger.error(f"Vault authentication failed: {e}")
            raise
    
    def _authenticate_with_token(self):
        """Authenticate using token"""
        token = os.getenv('VAULT_TOKEN')
        if not token:
            raise ValueError("Vault token not specified. Set VAULT_TOKEN")
        
        self.client.token = token
    
    def _authenticate_with_approle(self):
        """Authenticate using AppRole"""
        role_id = os.getenv('VAULT_ROLE_ID')
        secret_id = os.getenv('VAULT_SECRET_ID')
        
        if not role_id or not secret_id:
            raise ValueError("AppRole not configured. Set VAULT_ROLE_ID and VAULT_SECRET_ID")
        
        response = self.client.auth.approle.login(
            role_id=role_id,
            secret_id=secret_id
        )
        
        if response and 'auth' in response:
            self.client.token = response['auth']['client_token']
        else:
            raise ValueError("Failed to get token via AppRole")
    

    
    def _authenticate_with_gcp(self):
        """Authenticate using GCP IAM"""
        role = os.getenv('VAULT_GCP_ROLE')
        jwt = os.getenv('VAULT_GCP_JWT')
        
        if not role or not jwt:
            raise ValueError("GCP authentication not configured")
        
        response = self.client.auth.gcp.login(
            role=role,
            jwt=jwt
        )
        
        if response and 'auth' in response:
            self.client.token = response['auth']['client_token']
        else:
            raise ValueError("Failed to get token via GCP IAM")
    
    def is_authenticated(self) -> bool:
        """Check Vault authentication status"""
        try:
            return self.client.is_authenticated()
        except Exception as e:
            logger.error(f"Vault authentication check failed: {e}")
            return False
    
    def get_secret(self, path: str, key: Optional[str] = None) -> Any:
        """
        Get secret from Vault
        
        Args:
            path: Secret path in Vault (e.g., 'secret/jamf-pro')
            key: Secret key (if None, returns entire secret)
            
        Returns:
            Secret value or None if not found
        """
        try:
            if not self.is_authenticated():
                logger.error("Failed to authenticate with Vault")
                return None
            
            # Read secret
            secret_response = self.client.secrets.kv.v2.read_secret_version(path=path)
            
            if secret_response and 'data' in secret_response:
                secret_data = secret_response['data']['data']
                
                if key:
                    return secret_data.get(key)
                else:
                    return secret_data
            else:
                logger.warning(f"Secret not found at path: {path}")
                return None
                
        except hvac.exceptions.InvalidPath:
            logger.warning(f"Secret path not found: {path}")
            return None
        except Exception as e:
            logger.error(f"Failed to get secret from Vault: {e}")
            return None
    
    def get_jamf_config(self, environment: str = 'dev') -> Dict[str, str]:
        """
        Get Jamf Pro configuration from Vault
        
        Args:
            environment: Environment (dev/prod)
            
        Returns:
            Dictionary with Jamf Pro configuration
        """
        config = {}
        
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
        
        db_secret = self.get_secret(f'secret/database-{environment}')
        if db_secret:
            db_host = os.getenv('POSTGRES_INTERNAL_IP', '10.79.160.3')
            
            config.update({
                'DATABASE_HOST': db_host,
                'DATABASE_PORT': db_secret.get('port', '5432'),
                'DATABASE_NAME': db_secret.get('name', ''),
                'DATABASE_USER': db_secret.get('user', ''),
                'DATABASE_PASSWORD': db_secret.get('password', ''),
                'DATABASE_SSL_MODE': db_secret.get('ssl_mode', 'require'),
                'DATABASE_SSL_CA': db_secret.get('ssl_ca', ''),
                'DATABASE_SSL_CERT': db_secret.get('ssl_cert', ''),
                'DATABASE_SSL_KEY': db_secret.get('ssl_key', '')
            })
            
            if all([db_secret.get('user'), db_secret.get('password'), db_secret.get('name')]):
                ssl_params = ""
                if db_secret.get('ssl_mode'):
                    ssl_params = f"?sslmode={db_secret.get('ssl_mode')}"
                if db_secret.get('ssl_ca'):
                    ssl_params += f"&sslrootcert={db_secret.get('ssl_ca')}"
                if db_secret.get('ssl_cert'):
                    ssl_params += f"&sslcert={db_secret.get('ssl_cert')}"
                if db_secret.get('ssl_key'):
                    ssl_params += f"&sslkey={db_secret.get('ssl_key')}"
                
                database_url = f"postgresql://{db_secret.get('user')}:{db_secret.get('password')}@{db_host}:{db_secret.get('port', '5432')}/{db_secret.get('name')}{ssl_params}"
                config['DATABASE_URL'] = database_url
        
        return config
    
    def get_encryption_key(self, environment: str = 'dev') -> Optional[str]:
        """
        Get encryption key from Vault
        
        Args:
            environment: Environment (dev/prod)
            
        Returns:
            Encryption key or None
        """
        app_secret = self.get_secret(f'secret/jamf-bootstrap-{environment}')
        if app_secret:
            return app_secret.get('encryption_key')
        return None
    
    def validate_api_key(self, api_key: str, environment: str = 'dev') -> bool:
        """
        Validate API key
        
        Args:
            api_key: API key to validate
            environment: Environment (dev/prod)
            
        Returns:
            True if key is valid, False otherwise
        """
        stored_key = self.get_secret(f'secret/jamf-bootstrap-{environment}', 'api_secret')
        return stored_key == api_key
    
    def validate_payload_token(self, payload: dict, environment: str = 'dev') -> bool:
        """
        Validate token in request payload
        
        Args:
            payload: Request data from CRM
            environment: Environment (dev/prod)
            
        Returns:
            True if token is valid, False otherwise
        """
        try:
            if 'token' not in payload:
                logger.warning("Token missing in payload")
                return False
            
            token = payload['token']
            if not token:
                logger.warning("Token is empty in payload")
                return False
            
            stored_token = self.get_secret(f'secret/jamf-bootstrap-{environment}', 'api_secret')
            if not stored_token:
                logger.error("Token not found in Vault")
                return False
            
            is_valid = stored_token == token
            if not is_valid:
                logger.warning(f"Invalid token in payload: {token[:10]}...")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Token validation in payload failed: {e}")
            return False
    
    def get_secret_with_token_validation(self, payload: dict, secret_path: str, environment: str = 'dev') -> Optional[Dict[str, Any]]:
        """
        Get secret only after payload token validation
        
        Args:
            payload: Request data from CRM
            secret_path: Secret path in Vault
            environment: Environment (dev/prod)
            
        Returns:
            Secret from Vault or None if token is invalid
        """
        if not self.validate_payload_token(payload, environment):
            logger.error("Token in payload is invalid, secret not provided")
            return None
        
        logger.info(f"Token is valid, getting secret: {secret_path}")
        return self.get_secret(secret_path)
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test Vault connection
        
        Returns:
            Dictionary with test results
        """
        result = {
            'connected': False,
            'authenticated': False,
            'auth_method': self.auth_method,
            'error': None
        }
        
        try:
            self.client.sys.read_health_status()
            result['connected'] = True
            
            result['authenticated'] = self.is_authenticated()
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Failed to connect to Vault: {e}")
        
        return result
