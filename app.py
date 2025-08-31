#!/usr/bin/env python3
"""
Jamf Pro Bootstrap API
Handles encrypted requests from CRM to Jamf Pro with Vault integration
"""

import os
import logging
import uuid
import json
import psutil
from flask import Flask, request, jsonify, Response
from prometheus_client import generate_latest, Counter, Histogram, Gauge
from app.config import config
from app.database import DatabaseManager
from app.encryption import EncryptionManager
from app.vault_client import VaultClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    """Initialize and configure Flask application"""
    app = Flask(__name__)
    
    # Prometheus metrics setup
    request_counter = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
    request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration')
    active_requests = Gauge('http_requests_active', 'Active HTTP requests')
    cpu_usage = Gauge('container_cpu_usage_percent', 'Container CPU usage percentage')
    memory_usage = Gauge('container_memory_usage_percent', 'Container memory usage percentage')
    disk_usage = Gauge('container_disk_usage_percent', 'Container disk usage percentage')
    
    # Load config from Vault or environment variables
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
    
    # Initialize components
    vault_client = VaultClient()
    encryption_manager = EncryptionManager(config.get('ENCRYPTION_KEY', 'default-key'))
    db_manager = DatabaseManager(config.get('DATABASE_URL'))
    
    # Create tables on startup
    try:
        db_manager.create_tables()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    
    # Metrics collection middleware
    @app.before_request
    def before_request():
        active_requests.inc()
    
    @app.after_request
    def after_request(response):
        active_requests.dec()
        request_counter.labels(
            method=request.method,
            endpoint=request.endpoint,
            status=response.status_code
        ).inc()
        return response
    
    # API routes
    @app.route('/api/health')
    def health_check():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'environment': config.get('FLASK_ENV'),
            'vault_connected': vault_client.is_authenticated()
        })
    
    @app.route('/metrics')
    def metrics():
        """Prometheus metrics endpoint"""
        try:
            # Update system metrics
            cpu_usage.set(psutil.cpu_percent(interval=1))
            memory_usage.set(psutil.virtual_memory().percent)
            disk_usage.set(psutil.disk_usage('/app').percent)
            
            # Generate Prometheus metrics
            return Response(generate_latest(), mimetype='text/plain')
        except Exception as e:
            logger.error(f"Metrics generation failed: {e}")
            return jsonify({'error': 'Metrics generation failed'}), 500
    
    @app.route('/api/request', methods=['POST'])
    def create_request():
        """Create new encrypted request from CRM"""
        try:
            # Get request data
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            # Required fields including token
            required_fields = ['crm_id', 'request_type', 'payload', 'encrypted_key', 'token']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400
            
            # Validate token in payload
            if not vault_client.validate_payload_token(data, config.get('FLASK_ENV')):
                return jsonify({'error': 'Invalid token in payload'}), 401
            
            # Generate unique request ID
            request_id = str(uuid.uuid4())
            
            # Validate encrypted key format
            if not encryption_manager.validate_encrypted_data(data['encrypted_key']):
                return jsonify({'error': 'Invalid encrypted key format'}), 400
            
            # Generate checksum for integrity verification
            checksum = encryption_manager.generate_checksum(data['payload'])
            
            # Save request to database
            request_record = db_manager.create_request(
                request_id=request_id,
                crm_id=data['crm_id'],
                request_type=data['request_type'],
                payload=data['payload'],
                encrypted_key=data['encrypted_key'],
                checksum=checksum
            )
            
            if not request_record:
                return jsonify({'error': 'Failed to create request'}), 500
            
            logger.info(f"Request {request_id} created for CRM {data['crm_id']}")
            
            return jsonify({
                'request_id': request_id,
                'status': 'created',
                'message': 'Request created successfully'
            }), 201
            
        except Exception as e:
            logger.error(f"Request creation failed: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/request/<request_id>', methods=['GET'])
    def get_request_status(request_id):
        """Get request status by ID"""
        try:
            # Check API key
            api_key = request.headers.get('X-API-Key')
            if not api_key or not vault_client.validate_api_key(api_key, config.get('FLASK_ENV')):
                return jsonify({'error': 'Invalid API key'}), 401
            
            # Get request from database
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
            logger.error(f"Failed to get request status: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/requests/crm/<crm_id>', methods=['GET'])
    def get_crm_requests(crm_id):
        """Get all requests for specific CRM"""
        try:
            # Check API key
            api_key = request.headers.get('X-API-Key')
            if not api_key or not vault_client.validate_api_key(api_key, config.get('FLASK_ENV')):
                return jsonify({'error': 'Invalid API key'}), 401
            
            # Get requests from database
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
            logger.error(f"Failed to get CRM requests: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/process', methods=['POST'])
    def process_pending_requests():
        """Process pending requests (internal endpoint)"""
        try:
            # Get request data
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            # Validate token in payload
            if not vault_client.validate_payload_token(data, config.get('FLASK_ENV')):
                return jsonify({'error': 'Invalid token in payload'}), 401
            
            # Initialize Jamf processor
            from app.jamf_processor import JamfProcessor
            jamf_processor = JamfProcessor(
                jamf_url=app.config['JAMF_PRO_URL'],
                username=app.config['JAMF_PRO_USERNAME'],
                password=app.config['JAMF_PRO_PASSWORD'],
                api_key=app.config['JAMF_PRO_API_KEY']
            )
            
            # Get pending requests
            pending_requests = db_manager.get_pending_requests()
            
            processed_count = 0
            for request_record in pending_requests:
                try:
                    # Update status to processing
                    db_manager.update_request_status(request_record.request_id, 'processing')
                    
                    # Decrypt data with integrity check
                    decrypted_payload = encryption_manager.decrypt_and_verify(
                        request_record.payload, 
                        request_record.checksum
                    )
                    if not decrypted_payload:
                        raise ValueError("Data integrity check failed")
                    employee_data = json.loads(decrypted_payload)
                    
                    # Process request based on type
                    if request_record.request_type == 'create':
                        result = jamf_processor.create_computer_record(employee_data)
                    elif request_record.request_type == 'update':
                        # Need jamf_pro_id for updates
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
                    
                    # Update status based on result
                    if result and result.get('success'):
                        db_manager.update_request_status(
                            request_record.request_id, 
                            'completed',
                            jamf_pro_id=result.get('jamf_pro_id')
                        )
                        processed_count += 1
                        logger.info(f"Request {request_record.request_id} processed")
                    else:
                        error_msg = result.get('error', 'Unknown error') if result else 'No result'
                        db_manager.update_request_status(
                            request_record.request_id, 
                            'failed',
                            error_message=error_msg
                        )
                        logger.error(f"Failed to process request {request_record.request_id}: {error_msg}")
                    
                except Exception as e:
                    logger.error(f"Failed to process request {request_record.request_id}: {e}")
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
            logger.error(f"Failed to process requests: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    debug = config.get_bool('FLASK_DEBUG', False)
    app.run(debug=debug, host='0.0.0.0', port=5000)
