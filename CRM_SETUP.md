# 🏢 Настройка CRM системы для интеграции с Jamf Pro Bootstrap API

## 📋 Обзор интеграции

CRM система должна:
1. **Получать токен** из Vault для аутентификации
2. **Шифровать данные** сотрудника
3. **Шифровать ключ** ключом из Vault
4. **Отправлять запрос** с токеном в payload
5. **Обрабатывать ответ** от API

## 🔧 Настройка Vault для CRM

### 1. Создание секретов в Vault

#### Секрет для CRM аутентификации:
```bash
# Путь: secret/crm-auth-prod
{
  "api_token": "crm-api-token-here",
  "vault_url": "https://vault.your-domain.com",
  "jamf_api_endpoint": "https://your-vm-ip:5000/api/request"
}
```

#### Секрет для шифрования:
```bash
# Путь: secret/crm-encryption-prod
{
  "encryption_key": "your-32-character-encryption-key",
  "vault_encryption_key": "vault-encryption-key-for-key-encryption"
}
```

### 2. Настройка политик Vault

```bash
# Создание политики для CRM
vault policy write crm-policy -<<EOF
path "secret/crm-auth-*" {
  capabilities = ["read"]
}
path "secret/crm-encryption-*" {
  capabilities = ["read"]
}
path "secret/jamf-bootstrap-*" {
  capabilities = ["read"]
}
EOF

# Создание AppRole для CRM
vault auth enable approle
vault write auth/approle/role/crm-role \
  policies="crm-policy" \
  token_ttl=1h \
  token_max_ttl=4h
```

## 🚀 Настройка CRM системы

### 1. Установка зависимостей

#### Python зависимости:
```bash
pip install requests hvac cryptography
```

#### Node.js зависимости:
```bash
npm install axios node-vault crypto-js
```

### 2. Конфигурация CRM

#### Python конфигурация:
```python
# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class CRMConfig:
    # Vault настройки
    VAULT_URL = os.getenv('VAULT_URL', 'https://vault.your-domain.com')
    VAULT_ROLE_ID = os.getenv('VAULT_ROLE_ID')
    VAULT_SECRET_ID = os.getenv('VAULT_SECRET_ID')
    
    # API настройки
    JAMF_API_ENDPOINT = os.getenv('JAMF_API_ENDPOINT', 'https://your-vm-ip:5000/api/request')
    
    # Окружение
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'prod')
```

#### Node.js конфигурация:
```javascript
// config.js
require('dotenv').config();

const config = {
    // Vault настройки
    vaultUrl: process.env.VAULT_URL || 'https://vault.your-domain.com',
    vaultRoleId: process.env.VAULT_ROLE_ID,
    vaultSecretId: process.env.VAULT_SECRET_ID,
    
    // API настройки
    jamfApiEndpoint: process.env.JAMF_API_ENDPOINT || 'https://your-vm-ip:5000/api/request',
    
    // Окружение
    environment: process.env.ENVIRONMENT || 'prod'
};

module.exports = config;
```

### 3. Vault клиент для CRM

#### Python Vault клиент:
```python
# vault_client.py
import hvac
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class CRMVaultClient:
    def __init__(self, vault_url: str, role_id: str, secret_id: str):
        self.vault_url = vault_url
        self.role_id = role_id
        self.secret_id = secret_id
        self.client = hvac.Client(url=vault_url)
        self._authenticate()
    
    def _authenticate(self):
        """Аутентификация в Vault через AppRole"""
        try:
            response = self.client.auth.approle.login(
                role_id=self.role_id,
                secret_id=self.secret_id
            )
            
            if response and 'auth' in response:
                self.client.token = response['auth']['client_token']
                logger.info("Успешная аутентификация в Vault")
            else:
                raise ValueError("Не удалось получить токен через AppRole")
                
        except Exception as e:
            logger.error(f"Ошибка аутентификации в Vault: {e}")
            raise
    
    def get_secret(self, path: str) -> Optional[Dict]:
        """Получение секрета из Vault"""
        try:
            response = self.client.secrets.kv.v2.read_secret_version(path=path)
            if response and 'data' in response and 'data' in response['data']:
                return response['data']['data']
            return None
        except Exception as e:
            logger.error(f"Ошибка получения секрета {path}: {e}")
            return None
    
    def get_api_token(self, environment: str = 'prod') -> Optional[str]:
        """Получение API токена для Jamf API"""
        secret = self.get_secret(f'crm-auth-{environment}')
        return secret.get('api_token') if secret else None
    
    def get_encryption_keys(self, environment: str = 'prod') -> Optional[Dict]:
        """Получение ключей шифрования"""
        return self.get_secret(f'crm-encryption-{environment}')
```

#### Node.js Vault клиент:
```javascript
// vaultClient.js
const vault = require('node-vault');
const logger = require('./logger');

class CRMVaultClient {
    constructor(vaultUrl, roleId, secretId) {
        this.vaultUrl = vaultUrl;
        this.roleId = roleId;
        this.secretId = secretId;
        this.client = vault({ apiVersion: 'v1', endpoint: vaultUrl });
        this.authenticate();
    }
    
    async authenticate() {
        try {
            const result = await this.client.approleLogin({
                role_id: this.roleId,
                secret_id: this.secretId
            });
            
            this.client.token = result.auth.client_token;
            logger.info('Успешная аутентификация в Vault');
        } catch (error) {
            logger.error(`Ошибка аутентификации в Vault: ${error.message}`);
            throw error;
        }
    }
    
    async getSecret(path) {
        try {
            const result = await this.client.read(`secret/data/${path}`);
            return result.data.data;
        } catch (error) {
            logger.error(`Ошибка получения секрета ${path}: ${error.message}`);
            return null;
        }
    }
    
    async getApiToken(environment = 'prod') {
        const secret = await this.getSecret(`crm-auth-${environment}`);
        return secret ? secret.api_token : null;
    }
    
    async getEncryptionKeys(environment = 'prod') {
        return await this.getSecret(`crm-encryption-${environment}`);
    }
}

module.exports = CRMVaultClient;
```

### 4. Менеджер шифрования

#### Python менеджер шифрования:
```python
# encryption_manager.py
import base64
import hashlib
import json
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class CRMEncryptionManager:
    def __init__(self, encryption_key: str):
        self.encryption_key = encryption_key.encode()
        self.fernet = self._create_fernet()
    
    def _create_fernet(self) -> Fernet:
        """Создание Fernet объекта для шифрования"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'jamf_bootstrap_salt',
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.encryption_key))
        return Fernet(key)
    
    def encrypt_data(self, data: str) -> str:
        """Шифрование данных"""
        encrypted_data = self.fernet.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted_data).decode()
    
    def encrypt_key_with_vault_key(self, key: str, vault_key: str) -> str:
        """Шифрование ключа ключом из Vault"""
        vault_fernet = Fernet(base64.urlsafe_b64encode(vault_key.encode()))
        encrypted_key = vault_fernet.encrypt(key.encode())
        return base64.urlsafe_b64encode(encrypted_key).decode()
    
    def generate_checksum(self, data: str) -> str:
        """Генерация SHA256 хеша"""
        return hashlib.sha256(data.encode()).hexdigest()
```

#### Node.js менеджер шифрования:
```javascript
// encryptionManager.js
const crypto = require('crypto');
const CryptoJS = require('crypto-js');

class CRMEncryptionManager {
    constructor(encryptionKey) {
        this.encryptionKey = encryptionKey;
    }
    
    encryptData(data) {
        const cipher = crypto.createCipher('aes-256-cbc', this.encryptionKey);
        let encrypted = cipher.update(data, 'utf8', 'base64');
        encrypted += cipher.final('base64');
        return encrypted;
    }
    
    encryptKeyWithVaultKey(key, vaultKey) {
        const cipher = crypto.createCipher('aes-256-cbc', vaultKey);
        let encrypted = cipher.update(key, 'utf8', 'base64');
        encrypted += cipher.final('base64');
        return encrypted;
    }
    
    generateChecksum(data) {
        return crypto.createHash('sha256').update(data).digest('hex');
    }
}

module.exports = CRMEncryptionManager;
```

### 5. Jamf API клиент

#### Python Jamf API клиент:
```python
# jamf_api_client.py
import requests
import json
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class JamfAPIClient:
    def __init__(self, api_endpoint: str, vault_client, encryption_manager):
        self.api_endpoint = api_endpoint
        self.vault_client = vault_client
        self.encryption_manager = encryption_manager
    
    def create_employee_request(self, employee_data: Dict, environment: str = 'prod') -> Optional[Dict]:
        """Создание запроса для сотрудника"""
        try:
            # Получаем токен из Vault
            api_token = self.vault_client.get_api_token(environment)
            if not api_token:
                raise ValueError("Не удалось получить API токен из Vault")
            
            # Получаем ключи шифрования
            encryption_keys = self.vault_client.get_encryption_keys(environment)
            if not encryption_keys:
                raise ValueError("Не удалось получить ключи шифрования из Vault")
            
            # Подготавливаем данные
            employee_json = json.dumps(employee_data)
            
            # Шифруем данные сотрудника
            encrypted_payload = self.encryption_manager.encrypt_data(employee_json)
            
            # Шифруем ключ ключом из Vault
            encrypted_key = self.encryption_manager.encrypt_key_with_vault_key(
                encryption_keys['encryption_key'],
                encryption_keys['vault_encryption_key']
            )
            
            # Генерируем checksum
            checksum = self.encryption_manager.generate_checksum(employee_json)
            
            # Формируем запрос
            request_data = {
                'crm_id': f"crm-{employee_data.get('employee_id', 'unknown')}",
                'request_type': 'create',
                'payload': encrypted_payload,
                'encrypted_key': encrypted_key,
                'token': api_token
            }
            
            # Отправляем запрос
            response = requests.post(
                self.api_endpoint,
                json=request_data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Запрос создан для сотрудника {employee_data.get('employee_id')}")
                return response.json()
            else:
                logger.error(f"Ошибка создания запроса: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка создания запроса для сотрудника: {e}")
            return None
    
    def get_request_status(self, request_id: str, environment: str = 'prod') -> Optional[Dict]:
        """Получение статуса запроса"""
        try:
            api_token = self.vault_client.get_api_token(environment)
            if not api_token:
                raise ValueError("Не удалось получить API токен из Vault")
            
            response = requests.get(
                f"{self.api_endpoint}/{request_id}",
                headers={'Authorization': f'Bearer {api_token}'},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Ошибка получения статуса: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка получения статуса запроса: {e}")
            return None
```

#### Node.js Jamf API клиент:
```javascript
// jamfApiClient.js
const axios = require('axios');
const logger = require('./logger');

class JamfAPIClient {
    constructor(apiEndpoint, vaultClient, encryptionManager) {
        this.apiEndpoint = apiEndpoint;
        this.vaultClient = vaultClient;
        this.encryptionManager = encryptionManager;
    }
    
    async createEmployeeRequest(employeeData, environment = 'prod') {
        try {
            // Получаем токен из Vault
            const apiToken = await this.vaultClient.getApiToken(environment);
            if (!apiToken) {
                throw new Error('Не удалось получить API токен из Vault');
            }
            
            // Получаем ключи шифрования
            const encryptionKeys = await this.vaultClient.getEncryptionKeys(environment);
            if (!encryptionKeys) {
                throw new Error('Не удалось получить ключи шифрования из Vault');
            }
            
            // Подготавливаем данные
            const employeeJson = JSON.stringify(employeeData);
            
            // Шифруем данные сотрудника
            const encryptedPayload = this.encryptionManager.encryptData(employeeJson);
            
            // Шифруем ключ ключом из Vault
            const encryptedKey = this.encryptionManager.encryptKeyWithVaultKey(
                encryptionKeys.encryption_key,
                encryptionKeys.vault_encryption_key
            );
            
            // Генерируем checksum
            const checksum = this.encryptionManager.generateChecksum(employeeJson);
            
            // Формируем запрос
            const requestData = {
                crm_id: `crm-${employeeData.employee_id || 'unknown'}`,
                request_type: 'create',
                payload: encryptedPayload,
                encrypted_key: encryptedKey,
                token: apiToken
            };
            
            // Отправляем запрос
            const response = await axios.post(this.apiEndpoint, requestData, {
                headers: { 'Content-Type': 'application/json' },
                timeout: 30000
            });
            
            logger.info(`Запрос создан для сотрудника ${employeeData.employee_id}`);
            return response.data;
            
        } catch (error) {
            logger.error(`Ошибка создания запроса для сотрудника: ${error.message}`);
            return null;
        }
    }
    
    async getRequestStatus(requestId, environment = 'prod') {
        try {
            const apiToken = await this.vaultClient.getApiToken(environment);
            if (!apiToken) {
                throw new Error('Не удалось получить API токен из Vault');
            }
            
            const response = await axios.get(`${this.apiEndpoint}/${requestId}`, {
                headers: { 'Authorization': `Bearer ${apiToken}` },
                timeout: 30000
            });
            
            return response.data;
            
        } catch (error) {
            logger.error(`Ошибка получения статуса запроса: ${error.message}`);
            return null;
        }
    }
}

module.exports = JamfAPIClient;
```

### 6. Пример использования

#### Python пример:
```python
# main.py
from config import CRMConfig
from vault_client import CRMVaultClient
from encryption_manager import CRMEncryptionManager
from jamf_api_client import JamfAPIClient

def main():
    # Инициализация компонентов
    config = CRMConfig()
    
    vault_client = CRMVaultClient(
        config.VAULT_URL,
        config.VAULT_ROLE_ID,
        config.VAULT_SECRET_ID
    )
    
    encryption_keys = vault_client.get_encryption_keys(config.ENVIRONMENT)
    encryption_manager = CRMEncryptionManager(encryption_keys['encryption_key'])
    
    jamf_client = JamfAPIClient(
        config.JAMF_API_ENDPOINT,
        vault_client,
        encryption_manager
    )
    
    # Данные сотрудника
    employee_data = {
        "employee_id": "E12345",
        "email": "user@example.com",
        "full_name": "User Name",
        "department": "IT",  # IT, HR, Finance, Marketing, Sales
        "device": {
            "serial": "C02XXXXX",
            "platform": "macOS",
            "os_version": "15.0"
        },
        "idempotency_key": "b2df428b-..."
    }
    
    # Создание запроса
    result = jamf_client.create_employee_request(employee_data, config.ENVIRONMENT)
    
    if result:
        print(f"Запрос создан: {result}")
    else:
        print("Ошибка создания запроса")

if __name__ == "__main__":
    main()
```

#### Node.js пример:
```javascript
// main.js
const config = require('./config');
const CRMVaultClient = require('./vaultClient');
const CRMEncryptionManager = require('./encryptionManager');
const JamfAPIClient = require('./jamfApiClient');

async function main() {
    try {
        // Инициализация компонентов
        const vaultClient = new CRMVaultClient(
            config.vaultUrl,
            config.vaultRoleId,
            config.vaultSecretId
        );
        
        const encryptionKeys = await vaultClient.getEncryptionKeys(config.environment);
        const encryptionManager = new CRMEncryptionManager(encryptionKeys.encryption_key);
        
        const jamfClient = new JamfAPIClient(
            config.jamfApiEndpoint,
            vaultClient,
            encryptionManager
        );
        
        // Данные сотрудника
        const employeeData = {
            employee_id: "E12345",
            email: "user@example.com",
            full_name: "User Name",
            department: "IT", // IT, HR, Finance, Marketing, Sales
            device: {
                serial: "C02XXXXX",
                platform: "macOS",
                os_version: "15.0"
            },
            idempotency_key: "b2df428b-..."
        };
        
        // Создание запроса
        const result = await jamfClient.createEmployeeRequest(employeeData, config.environment);
        
        if (result) {
            console.log(`Запрос создан: ${JSON.stringify(result)}`);
        } else {
            console.log("Ошибка создания запроса");
        }
        
    } catch (error) {
        console.error(`Ошибка: ${error.message}`);
    }
}

main();
```

### 7. Переменные окружения

#### .env файл для CRM:
```bash
# Vault настройки
VAULT_URL=https://vault.your-domain.com
VAULT_ROLE_ID=your-role-id
VAULT_SECRET_ID=your-secret-id

# API настройки
JAMF_API_ENDPOINT=https://your-vm-ip:5000/api/request

# Окружение
ENVIRONMENT=prod
```

## 🔒 Безопасность

### Рекомендации:
- ✅ **Ротация токенов** каждые 24 часа
- ✅ **Логирование** всех операций
- ✅ **Валидация данных** перед отправкой
- ✅ **Обработка ошибок** и retry логика
- ✅ **SSL/TLS** для всех соединений
- ✅ **Ограничение доступа** к Vault

### Мониторинг:
- 📊 **Метрики запросов** к API
- 📊 **Время ответа** Vault
- 📊 **Количество ошибок** шифрования
- 📊 **Статус запросов** в Jamf Pro

## 🚀 Развертывание

### 1. Установка зависимостей
### 2. Настройка переменных окружения
### 3. Тестирование подключения к Vault
### 4. Тестирование шифрования данных
### 5. Тестирование отправки запросов
### 6. Мониторинг и логирование

**CRM система готова к интеграции с Jamf Pro Bootstrap API!** 🎯
