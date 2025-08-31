#!/usr/bin/env python3
"""
Example test request from CRM system to Jamf Pro Bootstrap API
"""

import requests
import json
import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

def create_fernet(key: str) -> Fernet:
    """Create Fernet object for encryption"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'jamf_bootstrap_salt',
        iterations=100000,
    )
    key_bytes = base64.urlsafe_b64encode(kdf.derive(key.encode()))
    return Fernet(key_bytes)

def encrypt_data(data: str, key: str) -> str:
    """Encrypt data"""
    fernet = create_fernet(key)
    encrypted_data = fernet.encrypt(data.encode())
    return base64.urlsafe_b64encode(encrypted_data).decode()

def encrypt_key_with_vault_key(key: str, vault_key: str) -> str:
    """Encrypt key with Vault key"""
    vault_fernet = Fernet(base64.urlsafe_b64encode(vault_key.encode()))
    encrypted_key = vault_fernet.encrypt(key.encode())
    return base64.urlsafe_b64encode(encrypted_key).decode()

def generate_checksum(data: str) -> str:
    """Generate SHA256 hash"""
    return hashlib.sha256(data.encode()).hexdigest()

def main():
    # Configuration (in real system these come from Vault)
    VAULT_URL = "https://vault.your-domain.com"
    JAMF_API_ENDPOINT = "https://your-vm-ip:5000/api/request"
    
    # Secrets (in real system obtained from Vault)
    API_TOKEN = "your-api-token-from-vault"
    ENCRYPTION_KEY = "your-32-character-encryption-key"
    VAULT_ENCRYPTION_KEY = "vault-encryption-key-for-key-encryption"
    
    # Employee data
    employee_data = {
        "employee_id": "E12345",
        "email": "sergei@pharmacyhub.com",
        "full_name": "User Name",
        "department": "IT",  # IT, HR, Finance, Marketing, Sales
        "device": {
            "serial": "C02XXXXX",
            "platform": "macOS",
            "os_version": "15.0"
        },
        "idempotency_key": "b2df428b-1234-5678-9abc-def012345678"
    }
    
    try:
        # 1. Prepare data
        employee_json = json.dumps(employee_data, sort_keys=True)
        print(f"📋 Employee data: {employee_json}")
        
        # 2. Encrypt employee data
        encrypted_payload = encrypt_data(employee_json, ENCRYPTION_KEY)
        print(f"🔒 Encrypted data: {encrypted_payload[:50]}...")
        
        # 3. Encrypt key with Vault key
        encrypted_key = encrypt_key_with_vault_key(ENCRYPTION_KEY, VAULT_ENCRYPTION_KEY)
        print(f"🔑 Encrypted key: {encrypted_key[:50]}...")
        
        # 4. Generate checksum
        checksum = generate_checksum(employee_json)
        print(f"📊 Checksum: {checksum}")
        
        # 5. Build request
        request_data = {
            'crm_id': f"crm-{employee_data['employee_id']}",
            'request_type': 'create',
            'payload': encrypted_payload,
            'encrypted_key': encrypted_key,
            'token': API_TOKEN
        }
        
        print(f"📤 Sending request to: {JAMF_API_ENDPOINT}")
        print(f"📦 Request data: {json.dumps(request_data, indent=2)}")
        
        # 6. Send request
        response = requests.post(
            JAMF_API_ENDPOINT,
            json=request_data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"📥 Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success response: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"💥 Exception: {e}")

if __name__ == "__main__":
    main()
