#!/usr/bin/env python3
"""
Пример тестового запроса от CRM системы к Jamf Pro Bootstrap API
"""

import requests
import json
import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

def create_fernet(key: str) -> Fernet:
    """Создание Fernet объекта для шифрования"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'jamf_bootstrap_salt',
        iterations=100000,
    )
    key_bytes = base64.urlsafe_b64encode(kdf.derive(key.encode()))
    return Fernet(key_bytes)

def encrypt_data(data: str, key: str) -> str:
    """Шифрование данных"""
    fernet = create_fernet(key)
    encrypted_data = fernet.encrypt(data.encode())
    return base64.urlsafe_b64encode(encrypted_data).decode()

def encrypt_key_with_vault_key(key: str, vault_key: str) -> str:
    """Шифрование ключа ключом из Vault"""
    vault_fernet = Fernet(base64.urlsafe_b64encode(vault_key.encode()))
    encrypted_key = vault_fernet.encrypt(key.encode())
    return base64.urlsafe_b64encode(encrypted_key).decode()

def generate_checksum(data: str) -> str:
    """Генерация SHA256 хеша"""
    return hashlib.sha256(data.encode()).hexdigest()

def main():
    # Конфигурация (в реальной системе эти данные берутся из Vault)
    VAULT_URL = "https://vault.your-domain.com"
    JAMF_API_ENDPOINT = "https://your-vm-ip:5000/api/request"
    
    # Секреты (в реальной системе получаются из Vault)
    API_TOKEN = "your-api-token-from-vault"
    ENCRYPTION_KEY = "your-32-character-encryption-key"
    VAULT_ENCRYPTION_KEY = "vault-encryption-key-for-key-encryption"
    
    # Данные сотрудника
    employee_data = {
        "employee_id": "E12345",
        "email": "user@example.com",
        "full_name": "User Name",
        "device": {
            "serial": "C02XXXXX",
            "platform": "macOS",
            "os_version": "15.0"
        },
        "idempotency_key": "b2df428b-1234-5678-9abc-def012345678"
    }
    
    try:
        # 1. Подготавливаем данные
        employee_json = json.dumps(employee_data, sort_keys=True)
        print(f"📋 Данные сотрудника: {employee_json}")
        
        # 2. Шифруем данные сотрудника
        encrypted_payload = encrypt_data(employee_json, ENCRYPTION_KEY)
        print(f"🔒 Зашифрованные данные: {encrypted_payload[:50]}...")
        
        # 3. Шифруем ключ ключом из Vault
        encrypted_key = encrypt_key_with_vault_key(ENCRYPTION_KEY, VAULT_ENCRYPTION_KEY)
        print(f"🔑 Зашифрованный ключ: {encrypted_key[:50]}...")
        
        # 4. Генерируем checksum
        checksum = generate_checksum(employee_json)
        print(f"📊 Checksum: {checksum}")
        
        # 5. Формируем запрос
        request_data = {
            'crm_id': f"crm-{employee_data['employee_id']}",
            'request_type': 'create',
            'payload': encrypted_payload,
            'encrypted_key': encrypted_key,
            'token': API_TOKEN
        }
        
        print(f"📤 Отправляем запрос на: {JAMF_API_ENDPOINT}")
        print(f"📦 Данные запроса: {json.dumps(request_data, indent=2)}")
        
        # 6. Отправляем запрос
        response = requests.post(
            JAMF_API_ENDPOINT,
            json=request_data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"📥 Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Успешный ответ: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ Ошибка: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"💥 Ошибка: {e}")

if __name__ == "__main__":
    main()
