#!/usr/bin/env python3
"""
Example CRM request to Jamf Pro Bootstrap API

This script demonstrates how a CRM system would construct and send
an encrypted request to the Jamf Pro Bootstrap API.
"""

import os
import json
import base64
import hashlib
import requests
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def get_vault_secrets():
    """
    Get encryption keys and API token from HashiCorp Vault
    
    In a real implementation, this would connect to Vault using
    AppRole authentication and retrieve secrets.
    
    Returns:
        dict: Encryption key and API token
    """
    # This is a placeholder - replace with actual Vault integration
    return {
        'encryption_key': os.getenv('JAMF_ENCRYPTION_KEY', 'your-32-char-encryption-key-here'),
        'api_token': os.getenv('JAMF_API_TOKEN', 'your-api-token-here'),
        'api_url': os.getenv('JAMF_API_URL', 'https://your-api-server.com')
    }


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


def create_employee_data():
    """
    Create example employee data
    
    Returns:
        dict: Employee and device information
    """
    return {
        "employee_id": "E12345",
        "email": "sergei@pharmacyhub.com",
        "full_name": "User Name",
        "department": "IT",  # IT, HR, Finance, Marketing, Sales
        "device": {
            "serial": "C02XXXXX",
            "platform": "macOS",
            "os_version": "15.0"
        },
        "idempotency_key": "b2df428b-..."
    }


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
    # Get secrets from Vault
    secrets = get_vault_secrets()
    encryption_key = secrets['encryption_key']
    api_token = secrets['api_token']
    api_url = secrets['api_url']
    
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
    
    print(f"Sending request to: {api_url}/api/request")
    print(f"Request type: {request_type}")
    print(f"CRM ID: {crm_id}")
    print(f"Department: {employee_data.get('department')}")
    
    # Send request to API
    try:
        response = requests.post(
            f'{api_url}/api/request',
            json=request_payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        response.raise_for_status()
        result = response.json()
        
        print(f"✅ Request successful!")
        print(f"Response: {json.dumps(result, indent=2)}")
        return result
        
    except requests.exceptions.RequestException as e:
        error_msg = f"❌ Request failed: {str(e)}"
        print(error_msg)
        return {
            'success': False,
            'error': error_msg
        }


def check_request_status(request_id):
    """
    Check the status of a previously submitted request
    
    Args:
        request_id (str): Request ID from previous submission
        
    Returns:
        dict: Request status information
    """
    secrets = get_vault_secrets()
    api_url = secrets['api_url']
    api_token = secrets['api_token']
    
    try:
        response = requests.get(
            f'{api_url}/api/request/{request_id}',
            headers={'X-API-Key': api_token},
            timeout=30
        )
        
        response.raise_for_status()
        result = response.json()
        
        print(f"✅ Status check successful!")
        print(f"Status: {json.dumps(result, indent=2)}")
        return result
        
    except requests.exceptions.RequestException as e:
        error_msg = f"❌ Status check failed: {str(e)}"
        print(error_msg)
        return {
            'success': False,
            'error': error_msg
        }


def test_api_health():
    """
    Test API connectivity and health
    
    Returns:
        bool: True if API is healthy, False otherwise
    """
    secrets = get_vault_secrets()
    api_url = secrets['api_url']
    
    try:
        response = requests.get(f'{api_url}/api/health', timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ API health check successful!")
            print(f"Status: {result.get('status')}")
            print(f"Vault connected: {result.get('vault_connected')}")
            return True
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ API health check failed: {str(e)}")
        return False


def get_policies_info():
    """
    Get information about available policies by department
    
    Returns:
        dict: Policy information
    """
    secrets = get_vault_secrets()
    api_url = secrets['api_url']
    
    try:
        response = requests.get(f'{api_url}/api/policies', timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Policy information retrieved!")
            print(f"Supported departments: {result.get('supported_departments')}")
            return result
        else:
            print(f"❌ Policy info request failed: {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Policy info request failed: {str(e)}")
        return None


def main():
    """
    Main function demonstrating the complete workflow
    """
    print("🚀 Jamf Pro Bootstrap API - CRM Integration Example")
    print("=" * 60)
    
    # Test API health first
    print("\n1. Testing API health...")
    if not test_api_health():
        print("❌ API is not available. Exiting.")
        return
    
    # Get policy information
    print("\n2. Getting policy information...")
    policies_info = get_policies_info()
    if policies_info:
        print("Available departments and policies:")
        for dept, info in policies_info.get('departments', {}).items():
            print(f"  {dept}: {info.get('smart_group')}")
    
    # Create employee data
    print("\n3. Creating employee data...")
    employee_data = create_employee_data()
    print(f"Employee: {employee_data['full_name']} ({employee_data['email']})")
    print(f"Department: {employee_data['department']}")
    print(f"Device: {employee_data['device']['serial']}")
    
    # Send request to create computer record
    print("\n4. Sending request to create computer record...")
    result = send_jamf_request(employee_data, 'crm-example-001', 'create')
    
    if result.get('success'):
        request_id = result.get('request_id')
        print(f"✅ Request created with ID: {request_id}")
        
        # Check request status
        print("\n5. Checking request status...")
        status_result = check_request_status(request_id)
        
        if status_result.get('success'):
            print("✅ Request processed successfully!")
            if 'policies_applied' in result:
                policies = result.get('policies_applied', [])
                print(f"Applied {len(policies)} policies for {employee_data['department']} department")
        else:
            print("❌ Request processing failed or still pending")
    else:
        print("❌ Failed to create request")
        print(f"Error: {result.get('error')}")
    
    print("\n" + "=" * 60)
    print("🏁 Example completed!")


if __name__ == "__main__":
    # Set environment variables for testing
    # In production, these would be retrieved from Vault
    os.environ.setdefault('JAMF_ENCRYPTION_KEY', 'your-32-char-encryption-key-here')
    os.environ.setdefault('JAMF_API_TOKEN', 'your-api-token-here')
    os.environ.setdefault('JAMF_API_URL', 'https://your-api-server.com')
    
    main()
