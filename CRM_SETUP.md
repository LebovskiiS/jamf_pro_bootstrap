# CRM Integration Setup Guide

> **Complete guide for configuring CRM system integration with Jamf Pro Bootstrap API**

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Integration Steps](#integration-steps)
- [Request Format](#request-format)
- [Error Handling](#error-handling)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

---

## Overview

This guide explains how to configure your CRM system to integrate with the Jamf Pro Bootstrap API. The integration allows automatic creation of computer records in Jamf Pro with department-based policy application.

### Integration Flow

1. **Employee data** is collected in CRM
2. **Data is encrypted** using Vault-provided keys
3. **Request is sent** to Jamf Pro Bootstrap API
4. **API processes** the request and creates Jamf Pro record
5. **Policies are applied** based on employee department
6. **Status is returned** to CRM

---

## Prerequisites

### Required Components

- **CRM System** with API capabilities
- **HashiCorp Vault** access for encryption keys
- **Network access** to Jamf Pro Bootstrap API
- **Employee data** with department information

### Required Permissions

- **Vault access** for reading encryption keys
- **API access** to Jamf Pro Bootstrap endpoints
- **Network connectivity** to API server

---

## Integration Steps

### Step 1: Configure Vault Access

#### Get Encryption Keys from Vault

```python
import hvac
import base64
import json

# Connect to Vault
vault_client = hvac.Client(
    url='https://your-vault-server.com',
    token='your-vault-token'
)

# Get encryption key for your environment
secret = vault_client.secrets.kv.v2.read_secret_version(
    path='jamf-bootstrap-prod',
    mount_point='secret'
)

encryption_key = secret['data']['data']['encryption_key']
api_token = secret['data']['data']['api_secret']
```

#### Store Keys Securely

```python
# Store keys in secure environment variables
import os

os.environ['JAMF_ENCRYPTION_KEY'] = encryption_key
os.environ['JAMF_API_TOKEN'] = api_token
os.environ['JAMF_API_URL'] = 'https://your-api-server.com'
```

### Step 2: Implement Encryption

#### Install Required Libraries

```bash
pip install cryptography requests
```

#### Create Encryption Function

```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import hashlib
import json

def encrypt_employee_data(employee_data, encryption_key):
    """
    Encrypt employee data using Fernet encryption
    
    Args:
        employee_data (dict): Employee information
        encryption_key (str): Encryption key from Vault
        
    Returns:
        tuple: (encrypted_data, encrypted_key, checksum)
    """
    # Convert data to JSON string
    json_data = json.dumps(employee_data, sort_keys=True)
    
    # Generate key using PBKDF2
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'jamf_bootstrap_salt',
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(encryption_key.encode()))
    
    # Encrypt data
    fernet = Fernet(key)
    encrypted_data = fernet.encrypt(json_data.encode())
    
    # Generate checksum
    checksum = hashlib.sha256(json_data.encode()).hexdigest()
    
    # Encrypt the key with Vault key
    vault_fernet = Fernet(encryption_key.encode())
    encrypted_key = vault_fernet.encrypt(key)
    
    return (
        base64.b64encode(encrypted_data).decode(),
        base64.b64encode(encrypted_key).decode(),
        checksum
    )
```

### Step 3: Create API Request Function

#### Implement Request Sending

```python
import requests
import json

def send_jamf_request(employee_data, crm_id, request_type='create'):
    """
    Send encrypted request to Jamf Pro Bootstrap API
    
    Args:
        employee_data (dict): Employee and device information
        crm_id (str): CRM system identifier
        request_type (str): Request type (create, update, delete)
        
    Returns:
        dict: API response
    """
    # Get encryption key from environment
    encryption_key = os.environ['JAMF_ENCRYPTION_KEY']
    api_token = os.environ['JAMF_API_TOKEN']
    api_url = os.environ['JAMF_API_URL']
    
    # Encrypt employee data
    encrypted_data, encrypted_key_b64, checksum = encrypt_employee_data(
        employee_data, encryption_key
    )
    
    # Prepare request payload
    request_payload = {
        'crm_id': crm_id,
        'request_type': request_type,
        'payload': encrypted_data,
        'encrypted_key': encrypted_key_b64,
        'token': api_token,
        'checksum': checksum
    }
    
    # Send request to API
    try:
        response = requests.post(
            f'{api_url}/api/request',
            json=request_payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'error': f'Request failed: {str(e)}'
        }
```

### Step 4: Implement Employee Data Collection

#### Collect Required Information

```python
def collect_employee_data(employee_id, email, full_name, department, device_info):
    """
    Collect and validate employee data
    
    Args:
        employee_id (str): Employee identifier
        email (str): Employee email address
        full_name (str): Employee full name
        department (str): Employee department
        device_info (dict): Device information
        
    Returns:
        dict: Validated employee data
    """
    # Validate required fields
    if not all([employee_id, email, full_name, department]):
        raise ValueError("Missing required employee information")
    
    # Validate department
    valid_departments = ['IT', 'HR', 'Finance', 'Marketing', 'Sales']
    if department not in valid_departments:
        department = 'Default'  # Fallback to default
    
    # Validate device information
    if not device_info.get('serial'):
        raise ValueError("Device serial number is required")
    
    # Generate idempotency key
    import uuid
    idempotency_key = str(uuid.uuid4())
    
    return {
        'employee_id': employee_id,
        'email': email,
        'full_name': full_name,
        'department': department,
        'device': {
            'serial': device_info['serial'],
            'platform': device_info.get('platform', 'macOS'),
            'os_version': device_info.get('os_version', '15.0')
        },
        'idempotency_key': idempotency_key
    }
```

---

## Request Format

### Employee Data Structure

```json
{
  "employee_id": "E12345",
  "email": "sergei@pharmacyhub.com",
  "full_name": "User Name",
  "department": "IT",
  "device": {
    "serial": "C02XXXXX",
    "platform": "macOS",
    "os_version": "15.0"
  },
  "idempotency_key": "b2df428b-..."
}
```

### API Request Structure

```json
{
  "crm_id": "crm-123",
  "request_type": "create",
  "payload": "encrypted-employee-data-base64",
  "encrypted_key": "encrypted-key-from-vault-base64",
  "token": "valid-token-from-vault",
  "checksum": "sha256-checksum"
}
```

### Supported Departments

| Department | Smart Group | Policies Applied |
|------------|-------------|------------------|
| **IT** | IT_Computers | Admin rights, Dev tools, Server access |
| **HR** | HR_Computers | Basic apps, Limited rights |
| **Finance** | FINANCE_Computers | Additional encryption, Audit |
| **Marketing** | MARKETING_Computers | Creative apps, Design tools |
| **Sales** | SALES_Computers | CRM systems, Mobile policies |
| **Default** | DEFAULT_Computers | Basic security policies |

---

## Error Handling

### Common Error Scenarios

#### Encryption Errors

```python
def handle_encryption_error(error):
    """Handle encryption-related errors"""
    if "Invalid key" in str(error):
        # Refresh encryption key from Vault
        refresh_vault_keys()
        return "Encryption key refreshed, retry request"
    elif "Invalid token" in str(error):
        # Refresh API token
        refresh_api_token()
        return "API token refreshed, retry request"
    else:
        return f"Encryption error: {str(error)}"
```

#### API Errors

```python
def handle_api_error(response):
    """Handle API response errors"""
    if response.status_code == 401:
        return "Authentication failed - check API token"
    elif response.status_code == 400:
        return f"Bad request: {response.json().get('error', 'Unknown error')}"
    elif response.status_code == 500:
        return "Internal server error - contact administrator"
    else:
        return f"API error {response.status_code}: {response.text}"
```

### Retry Logic

```python
import time
from functools import wraps

def retry_on_failure(max_retries=3, delay=1):
    """Retry decorator for failed requests"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    result = func(*args, **kwargs)
                    if result.get('success'):
                        return result
                    
                    # Check if retry is appropriate
                    error = result.get('error', '')
                    if 'authentication' in error.lower() or 'token' in error.lower():
                        # Refresh credentials and retry
                        refresh_credentials()
                        time.sleep(delay)
                        continue
                    
                    return result
                    
                except Exception as e:
                    if attempt == max_retries - 1:
                        return {'success': False, 'error': str(e)}
                    time.sleep(delay)
            
            return {'success': False, 'error': 'Max retries exceeded'}
        return wrapper
    return decorator
```

---

## Testing

### Test Environment Setup

#### Create Test Data

```python
def create_test_employee():
    """Create test employee data"""
    return {
        'employee_id': 'TEST-001',
        'email': 'test@example.com',
        'full_name': 'Test User',
        'department': 'IT',
        'device': {
            'serial': 'TEST-SERIAL-001',
            'platform': 'macOS',
            'os_version': '15.0'
        }
    }
```

#### Test Request Flow

```python
def test_integration():
    """Test complete integration flow"""
    # Create test employee
    employee_data = create_test_employee()
    
    # Send request
    result = send_jamf_request(employee_data, 'test-crm-001')
    
    # Check result
    if result.get('success'):
        print(f"✅ Test successful: {result.get('message')}")
        return True
    else:
        print(f"❌ Test failed: {result.get('error')}")
        return False
```

### Validation Tests

#### Test Encryption

```python
def test_encryption():
    """Test encryption/decryption functionality"""
    test_data = {'test': 'data'}
    encryption_key = os.environ['JAMF_ENCRYPTION_KEY']
    
    # Encrypt
    encrypted_data, encrypted_key_b64, checksum = encrypt_employee_data(
        test_data, encryption_key
    )
    
    # Verify checksum
    json_data = json.dumps(test_data, sort_keys=True)
    expected_checksum = hashlib.sha256(json_data.encode()).hexdigest()
    
    assert checksum == expected_checksum, "Checksum verification failed"
    print("✅ Encryption test passed")
```

#### Test API Connectivity

```python
def test_api_connectivity():
    """Test API connectivity"""
    api_url = os.environ['JAMF_API_URL']
    
    try:
        response = requests.get(f'{api_url}/api/health', timeout=10)
        if response.status_code == 200:
            print("✅ API connectivity test passed")
            return True
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API connectivity test failed: {str(e)}")
        return False
```

---

## Troubleshooting

### Common Issues

#### Vault Connection Issues

```bash
# Check Vault connectivity
curl -H "X-Vault-Token: your-token" https://your-vault-server.com/v1/sys/health

# Verify token permissions
vault token lookup
```

#### API Connection Issues

```bash
# Check API health
curl https://your-api-server.com/api/health

# Check network connectivity
ping your-api-server.com
telnet your-api-server.com 443
```

#### Encryption Issues

```python
# Verify encryption key format
def verify_encryption_key(key):
    """Verify encryption key is valid"""
    try:
        # Key should be 32 bytes when decoded
        decoded_key = base64.b64decode(key)
        assert len(decoded_key) == 32, "Key must be 32 bytes"
        return True
    except Exception as e:
        print(f"Invalid encryption key: {e}")
        return False
```

### Debug Mode

#### Enable Debug Logging

```python
import logging

# Configure debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Log all requests
def debug_request(request_data):
    """Log request data for debugging"""
    logging.debug(f"Request data: {json.dumps(request_data, indent=2)}")
```

#### Debug Response

```python
def debug_response(response):
    """Log response data for debugging"""
    logging.debug(f"Response status: {response.status_code}")
    logging.debug(f"Response headers: {dict(response.headers)}")
    logging.debug(f"Response body: {response.text}")
```

---

## Support

### Contact Information

- **Email**: sergei@pharmacyhub.com
- **Documentation**: [README.md](README.md)
- **Security**: [SECURITY.md](SECURITY.md)

### Additional Resources

- [Jamf Pro Documentation](https://docs.jamf.com/)
- [HashiCorp Vault Documentation](https://www.vaultproject.io/docs)
- [Python Cryptography Documentation](https://cryptography.io/)

---

<div align="center">

**Integration Guide - Last updated: January 2024**

</div>
