"""
Jamf Pro Processor
Модуль для обработки запросов к Jamf Pro
"""

import json
import logging
import requests
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class JamfProcessor:
    """Processor for Jamf Pro API operations"""
    
    def __init__(self, jamf_url: str, username: str, password: str, api_key: str = None):
        """
        Initialize Jamf Pro processor
        
        Args:
            jamf_url: Jamf Pro server URL
            username: Username
            password: Password
            api_key: API key (optional)
        """
        self.jamf_url = jamf_url.rstrip('/')
        self.username = username
        self.password = password
        self.api_key = api_key
        self.session = requests.Session()
        
        # Configure session
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        if self.api_key:
            self.session.headers['Authorization'] = f'Bearer {self.api_key}'
    
    def _get_auth_token(self) -> Optional[str]:
        """Get authentication token"""
        try:
            auth_url = f"{self.jamf_url}/api/v1/auth/token"
            response = self.session.post(
                auth_url,
                auth=(self.username, self.password),
                timeout=30
            )
            
            if response.status_code == 200:
                token_data = response.json()
                return token_data.get('token')
            else:
                logger.error(f"Failed to get token: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Jamf Pro authentication failed: {e}")
            return None
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Optional[Dict]:
        """Execute request to Jamf Pro API"""
        try:
            url = f"{self.jamf_url}/api/v1{endpoint}"
            
            # If no API key, get token
            if not self.api_key:
                token = self._get_auth_token()
                if token:
                    self.session.headers['Authorization'] = f'Bearer {token}'
                else:
                    return None
            
            response = self.session.request(
                method=method,
                url=url,
                json=data if data else None,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                logger.error(f"Jamf Pro request failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to execute Jamf Pro request: {e}")
            return None
    
    def create_computer_record(self, employee_data: Dict[str, Any]) -> Optional[Dict]:
        """
        Create computer record in Jamf Pro
        
        Args:
            employee_data: Employee and device data
            
        Returns:
            Record creation result
        """
        try:
            # Extract data
            employee_id = employee_data.get('employee_id')
            email = employee_data.get('email')
            full_name = employee_data.get('full_name')
            device = employee_data.get('device', {})
            
            if not all([employee_id, email, full_name, device]):
                raise ValueError("Incomplete employee data")
            
            # Build data for Jamf Pro
            computer_data = {
                "general": {
                    "name": f"{full_name} - {employee_id}",
                    "serial_number": device.get('serial'),
                    "platform": device.get('platform', 'Mac'),
                    "os_version": device.get('os_version'),
                    "last_contact_time": datetime.utcnow().isoformat()
                },
                "location": {
                    "username": email,
                    "real_name": full_name,
                    "email": email,
                    "department": "IT",
                    "building": "Main Office"
                },
                "purchasing": {
                    "purchased_by": full_name,
                    "warranty_expires": None,
                    "lease_expires": None
                },
                "extension_attributes": [
                    {
                        "id": 1,
                        "name": "Employee ID",
                        "type": "String",
                        "value": employee_id
                    },
                    {
                        "id": 2,
                        "name": "CRM ID",
                        "type": "String", 
                        "value": employee_id
                    }
                ]
            }
            
            # Create record
            result = self._make_request('POST', '/computers', computer_data)
            
            if result:
                logger.info(f"Created computer record for employee {employee_id}")
                return {
                    'success': True,
                    'jamf_pro_id': result.get('id'),
                    'message': 'Computer record created successfully'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to create computer record'
                }
                
        except Exception as e:
            logger.error(f"Failed to create computer record: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_computer_record(self, jamf_pro_id: str, employee_data: Dict[str, Any]) -> Optional[Dict]:
        """
        Update computer record in Jamf Pro
        
        Args:
            jamf_pro_id: Record ID in Jamf Pro
            employee_data: Updated employee data
            
        Returns:
            Record update result
        """
        try:
            # Get current record
            current_record = self._make_request('GET', f'/computers/id/{jamf_pro_id}')
            if not current_record:
                return {
                    'success': False,
                    'error': 'Computer record not found'
                }
            
            # Обновляем данные
            employee_id = employee_data.get('employee_id')
            email = employee_data.get('email')
            full_name = employee_data.get('full_name')
            device = employee_data.get('device', {})
            
            update_data = {
                "general": {
                    "name": f"{full_name} - {employee_id}",
                    "os_version": device.get('os_version')
                },
                "location": {
                    "username": email,
                    "real_name": full_name,
                    "email": email
                }
            }
            
            # Обновляем запись
            result = self._make_request('PUT', f'/computers/id/{jamf_pro_id}', update_data)
            
            if result:
                logger.info(f"Обновлена запись компьютера {jamf_pro_id} для сотрудника {employee_id}")
                return {
                    'success': True,
                    'jamf_pro_id': jamf_pro_id,
                    'message': 'Computer record updated successfully'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to update computer record'
                }
                
        except Exception as e:
            logger.error(f"Failed to update computer record: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def delete_computer_record(self, jamf_pro_id: str) -> Optional[Dict]:
        """
        Delete computer record from Jamf Pro
        
        Args:
            jamf_pro_id: Record ID in Jamf Pro
            
        Returns:
            Record deletion result
        """
        try:
            result = self._make_request('DELETE', f'/computers/id/{jamf_pro_id}')
            
            if result is not None:  # DELETE может возвращать None при успехе
                logger.info(f"Удалена запись компьютера {jamf_pro_id}")
                return {
                    'success': True,
                    'message': 'Computer record deleted successfully'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to delete computer record'
                }
                
        except Exception as e:
            logger.error(f"Failed to delete computer record: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def find_computer_by_serial(self, serial_number: str) -> Optional[Dict]:
        """
        Find computer by serial number
        
        Args:
            serial_number: Device serial number
            
        Returns:
            Computer data or None
        """
        try:
            result = self._make_request('GET', f'/computers/serialnumber/{serial_number}')
            return result
        except Exception as e:
            logger.error(f"Failed to find computer by serial number: {e}")
            return None
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to Jamf Pro
        
        Returns:
            Connection test result
        """
        try:
            result = self._make_request('GET', '/computers')
            return {
                'connected': result is not None,
                'error': None if result is not None else 'Failed to connect'
            }
        except Exception as e:
            return {
                'connected': False,
                'error': str(e)
            }
    
    # === POLICY MANAGEMENT METHODS ===
    
    def get_policies(self) -> Optional[Dict]:
        """
        Get all policies from Jamf Pro
        
        Returns:
            List of policies or None
        """
        try:
            result = self._make_request('GET', '/policies')
            return result
        except Exception as e:
            logger.error(f"Failed to get policies: {e}")
            return None
    
    def get_policy_by_name(self, policy_name: str) -> Optional[Dict]:
        """
        Get policy by name
        
        Args:
            policy_name: Name of the policy
            
        Returns:
            Policy data or None
        """
        try:
            policies = self.get_policies()
            if policies and 'policies' in policies:
                for policy in policies['policies']:
                    if policy.get('name') == policy_name:
                        return policy
            return None
        except Exception as e:
            logger.error(f"Failed to get policy by name: {e}")
            return None
    
    def get_smart_groups(self) -> Optional[Dict]:
        """
        Get all smart computer groups from Jamf Pro
        
        Returns:
            List of smart groups or None
        """
        try:
            result = self._make_request('GET', '/computergroups')
            return result
        except Exception as e:
            logger.error(f"Failed to get smart groups: {e}")
            return None
    
    def add_computer_to_group(self, computer_id: int, group_name: str) -> Optional[Dict]:
        """
        Add computer to a smart group
        
        Args:
            computer_id: Computer ID in Jamf Pro
            group_name: Name of the group
            
        Returns:
            Group assignment result
        """
        try:
            # Find group by name
            groups = self.get_smart_groups()
            if not groups or 'computer_groups' not in groups:
                return {
                    'success': False,
                    'error': 'No groups found'
                }
            
            group_id = None
            for group in groups['computer_groups']:
                if group.get('name') == group_name:
                    group_id = group.get('id')
                    break
            
            if not group_id:
                return {
                    'success': False,
                    'error': f'Group "{group_name}" not found'
                }
            
            # Add computer to group
            group_data = {
                "computer_additions": [
                    {"id": computer_id}
                ]
            }
            
            result = self._make_request('PUT', f'/computergroups/id/{group_id}', group_data)
            
            if result:
                logger.info(f"Added computer {computer_id} to group {group_name}")
                return {
                    'success': True,
                    'group_id': group_id,
                    'message': f'Computer added to group {group_name}'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to add computer to group'
                }
                
        except Exception as e:
            logger.error(f"Failed to add computer to group: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def apply_policies_by_department(self, computer_id: int, department: str) -> Optional[Dict]:
        """
        Apply department-specific policies to computer
        
        Args:
            computer_id: Computer ID in Jamf Pro
            department: Department name (IT, HR, Finance, Marketing, etc.)
            
        Returns:
            Policy application results
        """
        try:
            # Get all policies from Jamf Pro
            policies = self.get_policies()
            if not policies or 'policies' not in policies:
                return {
                    'success': False,
                    'error': 'No policies found in Jamf Pro'
                }
            
            applied_policies = []
            failed_policies = []
            
            # Define department-specific policy patterns
            department_policies = {
                'it': ['admin', 'management', 'it', 'developer', 'sudo'],
                'hr': ['hr', 'employee', 'basic', 'standard'],
                'finance': ['finance', 'accounting', 'secure', 'audit'],
                'marketing': ['marketing', 'creative', 'design', 'social'],
                'sales': ['sales', 'crm', 'customer', 'mobile'],
                'default': ['basic', 'standard', 'default', 'baseline']
            }
            
            # Get policy patterns for department
            dept_lower = department.lower()
            patterns = department_policies.get(dept_lower, department_policies['default'])
            
            # Apply policies based on department
            for policy in policies['policies']:
                policy_name = policy.get('name', '').lower()
                policy_id = policy.get('id')
                
                # Check if policy matches department patterns
                if any(pattern in policy_name for pattern in patterns):
                    # Add computer to policy scope (via smart groups)
                    group_result = self.add_computer_to_group(computer_id, f"{department.upper()}_Computers")
                    
                    if group_result and group_result.get('success'):
                        applied_policies.append(policy_name)
                        logger.info(f"Applied policy '{policy_name}' to computer {computer_id}")
                    else:
                        failed_policies.append(policy_name)
                        logger.warning(f"Failed to apply policy '{policy_name}' to computer {computer_id}")
            
            return {
                'success': True,
                'applied_policies': applied_policies,
                'failed_policies': failed_policies,
                'department': department,
                'message': f'Applied {len(applied_policies)} policies for {department} department'
            }
                
        except Exception as e:
            logger.error(f"Failed to apply department policies: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_computer_with_policies(self, employee_data: Dict[str, Any]) -> Optional[Dict]:
        """
        Create computer record and apply appropriate policies
        
        Args:
            employee_data: Employee and device data including department
            
        Returns:
            Creation and policy application result
        """
        try:
            # Create computer record first
            computer_result = self.create_computer_record(employee_data)
            if not computer_result or not computer_result.get('success'):
                return computer_result
            
            jamf_pro_id = computer_result.get('jamf_pro_id')
            department = employee_data.get('department', 'IT')
            
            # Apply department-specific policies
            policy_result = self.apply_policies_by_department(jamf_pro_id, department)
            
            return {
                'success': True,
                'jamf_pro_id': jamf_pro_id,
                'computer_created': True,
                'department': department,
                'policies_applied': policy_result.get('applied_policies', []),
                'policies_failed': policy_result.get('failed_policies', []),
                'message': f'Computer created and {len(policy_result.get("applied_policies", []))} policies applied for {department}'
            }
                
        except Exception as e:
            logger.error(f"Failed to create computer with policies: {e}")
            return {
                'success': False,
                'error': str(e)
            }
