#!/usr/bin/env python3
"""
Jamf Pro Bootstrap API
API для обработки зашифрованных запросов от CRM к Jamf Pro
"""

import os
import logging
import uuid
import json
from flask import Flask, request, jsonify
from app.config import config
from app.database import DatabaseManager
from app.encryption import EncryptionManager
from app.vault_client import VaultClient

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    """Создание и настройка Flask приложения"""
    app = Flask(__name__)
    
    # Конфигурация из Vault или переменных окружения
    app.config['SECRET_KEY'] = config.get('SECRET_KEY')
    app.config['JAMF_PRO_URL'] = config.get('JAMF_PRO_URL')
    app.config['JAMF_PRO_USERNAME'] = config.get('JAMF_PRO_USERNAME')
    app.config['JAMF_PRO_PASSWORD'] = config.get('JAMF_PRO_PASSWORD')
    app.config['JAMF_PRO_CLIENT_ID'] = config.get('JAMF_PRO_CLIENT_ID')
    app.config['JAMF_PRO_CLIENT_SECRET'] = config.get('JAMF_PRO_CLIENT_SECRET')
    app.config['JAMF_PRO_API_KEY'] = config.get('JAMF_PRO_API_KEY')
    app.config['DATABASE_URL'] = config.get('DATABASE_URL')
    app.config['ENCRYPTION_KEY'] = config.get('ENCRYPTION_KEY')
    app.config['API_SECRET'] = config.get('API_SECRET')
    
    # Инициализация компонентов
    vault_client = VaultClient()
    encryption_manager = EncryptionManager(config.get('ENCRYPTION_KEY', 'default-key'))
    db_manager = DatabaseManager(config.get('DATABASE_URL'))
    
    # Создание таблиц при запуске
    try:
        db_manager.create_tables()
        logger.info("База данных инициализирована")
    except Exception as e:
        logger.error(f"Ошибка инициализации базы данных: {e}")
    
    # API маршруты
    @app.route('/api/health')
    def health_check():
        """Проверка состояния API"""
        return jsonify({
            'status': 'healthy',
            'environment': config.get('FLASK_ENV'),
            'vault_connected': vault_client.is_authenticated()
        })
    
    @app.route('/api/request', methods=['POST'])
    def create_request():
        """Создание нового зашифрованного запроса от CRM"""
        try:
            # Проверяем API ключ
            api_key = request.headers.get('X-API-Key')
            if not api_key or not vault_client.validate_api_key(api_key, config.get('FLASK_ENV')):
                return jsonify({'error': 'Invalid API key'}), 401
            
            # Получаем данные запроса
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            # Обязательные поля
            required_fields = ['crm_id', 'request_type', 'payload', 'encrypted_key']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400
            
            # Генерируем уникальный ID запроса
            request_id = str(uuid.uuid4())
            
            # Проверяем валидность зашифрованного ключа
            if not encryption_manager.validate_encrypted_data(data['encrypted_key']):
                return jsonify({'error': 'Invalid encrypted key format'}), 400
            
            # Сохраняем запрос в базу данных
            request_record = db_manager.create_request(
                request_id=request_id,
                crm_id=data['crm_id'],
                request_type=data['request_type'],
                payload=data['payload'],
                encrypted_key=data['encrypted_key']
            )
            
            if not request_record:
                return jsonify({'error': 'Failed to create request'}), 500
            
            logger.info(f"Создан запрос {request_id} от CRM {data['crm_id']}")
            
            return jsonify({
                'request_id': request_id,
                'status': 'created',
                'message': 'Request created successfully'
            }), 201
            
        except Exception as e:
            logger.error(f"Ошибка создания запроса: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/request/<request_id>', methods=['GET'])
    def get_request_status(request_id):
        """Получение статуса запроса"""
        try:
            # Проверяем API ключ
            api_key = request.headers.get('X-API-Key')
            if not api_key or not vault_client.validate_api_key(api_key, config.get('FLASK_ENV')):
                return jsonify({'error': 'Invalid API key'}), 401
            
            # Получаем запрос из базы данных
            request_record = db_manager.get_request(request_id)
            if not request_record:
                return jsonify({'error': 'Request not found'}), 404
            
            return jsonify({
                'request_id': request_record.request_id,
                'crm_id': request_record.crm_id,
                'status': request_record.status,
                'request_type': request_record.request_type,
                'created_at': request_record.created_at.isoformat(),
                'updated_at': request_record.updated_at.isoformat(),
                'jamf_pro_id': request_record.jamf_pro_id,
                'error_message': request_record.error_message,
                'processed_at': request_record.processed_at.isoformat() if request_record.processed_at else None
            })
            
        except Exception as e:
            logger.error(f"Ошибка получения статуса запроса: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/requests/crm/<crm_id>', methods=['GET'])
    def get_crm_requests(crm_id):
        """Получение всех запросов для конкретного CRM"""
        try:
            # Проверяем API ключ
            api_key = request.headers.get('X-API-Key')
            if not api_key or not vault_client.validate_api_key(api_key, config.get('FLASK_ENV')):
                return jsonify({'error': 'Invalid API key'}), 401
            
            # Получаем запросы из базы данных
            requests = db_manager.get_requests_by_crm(crm_id)
            
            return jsonify({
                'crm_id': crm_id,
                'requests': [
                    {
                        'request_id': req.request_id,
                        'status': req.status,
                        'request_type': req.request_type,
                        'created_at': req.created_at.isoformat(),
                        'jamf_pro_id': req.jamf_pro_id
                    }
                    for req in requests
                ]
            })
            
        except Exception as e:
            logger.error(f"Ошибка получения запросов CRM: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/process', methods=['POST'])
    def process_pending_requests():
        """Обработка ожидающих запросов (внутренний endpoint)"""
        try:
            # Проверяем API ключ
            api_key = request.headers.get('X-API-Key')
            if not api_key or not vault_client.validate_api_key(api_key, config.get('FLASK_ENV')):
                return jsonify({'error': 'Invalid API key'}), 401
            
            # Инициализируем Jamf процессор
            from app.jamf_processor import JamfProcessor
            jamf_processor = JamfProcessor(
                jamf_url=app.config['JAMF_PRO_URL'],
                username=app.config['JAMF_PRO_USERNAME'],
                password=app.config['JAMF_PRO_PASSWORD'],
                api_key=app.config['JAMF_PRO_API_KEY']
            )
            
            # Получаем ожидающие запросы
            pending_requests = db_manager.get_pending_requests()
            
            processed_count = 0
            for request_record in pending_requests:
                try:
                    # Обновляем статус на "обрабатывается"
                    db_manager.update_request_status(request_record.request_id, 'processing')
                    
                    # Расшифровываем данные
                    decrypted_payload = encryption_manager.decrypt_data(request_record.payload)
                    employee_data = json.loads(decrypted_payload)
                    
                    # Обрабатываем запрос в зависимости от типа
                    if request_record.request_type == 'create':
                        result = jamf_processor.create_computer_record(employee_data)
                    elif request_record.request_type == 'update':
                        # Для обновления нужен jamf_pro_id
                        jamf_pro_id = request_record.jamf_pro_id or employee_data.get('jamf_pro_id')
                        if not jamf_pro_id:
                            raise ValueError("jamf_pro_id required for update")
                        result = jamf_processor.update_computer_record(jamf_pro_id, employee_data)
                    elif request_record.request_type == 'delete':
                        jamf_pro_id = request_record.jamf_pro_id or employee_data.get('jamf_pro_id')
                        if not jamf_pro_id:
                            raise ValueError("jamf_pro_id required for delete")
                        result = jamf_processor.delete_computer_record(jamf_pro_id)
                    else:
                        raise ValueError(f"Unsupported request type: {request_record.request_type}")
                    
                    # Обновляем статус на основе результата
                    if result and result.get('success'):
                        db_manager.update_request_status(
                            request_record.request_id, 
                            'completed',
                            jamf_pro_id=result.get('jamf_pro_id')
                        )
                        processed_count += 1
                        logger.info(f"Обработан запрос {request_record.request_id}")
                    else:
                        error_msg = result.get('error', 'Unknown error') if result else 'No result'
                        db_manager.update_request_status(
                            request_record.request_id, 
                            'failed',
                            error_message=error_msg
                        )
                        logger.error(f"Ошибка обработки запроса {request_record.request_id}: {error_msg}")
                    
                except Exception as e:
                    logger.error(f"Ошибка обработки запроса {request_record.request_id}: {e}")
                    db_manager.update_request_status(
                        request_record.request_id, 
                        'failed',
                        error_message=str(e)
                    )
            
            return jsonify({
                'processed_count': processed_count,
                'message': f'Processed {processed_count} requests'
            })
            
        except Exception as e:
            logger.error(f"Ошибка обработки запросов: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    debug = config.get_bool('FLASK_DEBUG', False)
    app.run(debug=debug, host='0.0.0.0', port=5000)
