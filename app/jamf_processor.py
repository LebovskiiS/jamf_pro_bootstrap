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
    """Процессор для работы с Jamf Pro API"""
    
    def __init__(self, jamf_url: str, username: str, password: str, api_key: str = None):
        """
        Инициализация процессора Jamf Pro
        
        Args:
            jamf_url: URL Jamf Pro сервера
            username: Имя пользователя
            password: Пароль
            api_key: API ключ (опционально)
        """
        self.jamf_url = jamf_url.rstrip('/')
        self.username = username
        self.password = password
        self.api_key = api_key
        self.session = requests.Session()
        
        # Настройка сессии
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        if self.api_key:
            self.session.headers['Authorization'] = f'Bearer {self.api_key}'
    
    def _get_auth_token(self) -> Optional[str]:
        """Получение токена аутентификации"""
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
                logger.error(f"Ошибка получения токена: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка аутентификации в Jamf Pro: {e}")
            return None
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Optional[Dict]:
        """Выполнение запроса к Jamf Pro API"""
        try:
            url = f"{self.jamf_url}/api/v1{endpoint}"
            
            # Если нет API ключа, получаем токен
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
                logger.error(f"Ошибка запроса к Jamf Pro: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка выполнения запроса к Jamf Pro: {e}")
            return None
    
    def create_computer_record(self, employee_data: Dict[str, Any]) -> Optional[Dict]:
        """
        Создание записи компьютера в Jamf Pro
        
        Args:
            employee_data: Данные сотрудника и устройства
            
        Returns:
            Результат создания записи
        """
        try:
            # Извлекаем данные
            employee_id = employee_data.get('employee_id')
            email = employee_data.get('email')
            full_name = employee_data.get('full_name')
            device = employee_data.get('device', {})
            
            if not all([employee_id, email, full_name, device]):
                raise ValueError("Неполные данные сотрудника")
            
            # Формируем данные для Jamf Pro
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
            
            # Создаем запись
            result = self._make_request('POST', '/computers', computer_data)
            
            if result:
                logger.info(f"Создана запись компьютера для сотрудника {employee_id}")
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
            logger.error(f"Ошибка создания записи компьютера: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_computer_record(self, jamf_pro_id: str, employee_data: Dict[str, Any]) -> Optional[Dict]:
        """
        Обновление записи компьютера в Jamf Pro
        
        Args:
            jamf_pro_id: ID записи в Jamf Pro
            employee_data: Обновленные данные сотрудника
            
        Returns:
            Результат обновления записи
        """
        try:
            # Получаем текущую запись
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
            logger.error(f"Ошибка обновления записи компьютера: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def delete_computer_record(self, jamf_pro_id: str) -> Optional[Dict]:
        """
        Удаление записи компьютера из Jamf Pro
        
        Args:
            jamf_pro_id: ID записи в Jamf Pro
            
        Returns:
            Результат удаления записи
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
            logger.error(f"Ошибка удаления записи компьютера: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def find_computer_by_serial(self, serial_number: str) -> Optional[Dict]:
        """
        Поиск компьютера по серийному номеру
        
        Args:
            serial_number: Серийный номер устройства
            
        Returns:
            Данные компьютера или None
        """
        try:
            result = self._make_request('GET', f'/computers/serialnumber/{serial_number}')
            return result
        except Exception as e:
            logger.error(f"Ошибка поиска компьютера по серийному номеру: {e}")
            return None
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Тестирование подключения к Jamf Pro
        
        Returns:
            Результат тестирования
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
