"""
Database Module
Модуль для работы с GCP Cloud SQL
"""

import os
import logging
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

Base = declarative_base()

class JamfRequest(Base):
    """Модель для хранения запросов к Jamf Pro"""
    __tablename__ = 'jamf_requests'
    
    id = Column(Integer, primary_key=True)
    request_id = Column(String(255), unique=True, nullable=False)
    crm_id = Column(String(255), nullable=False)
    jamf_pro_id = Column(String(255), nullable=True)
    status = Column(String(50), default='pending')  # pending, processing, completed, failed
    request_type = Column(String(100), nullable=False)  # create, update, delete
    payload = Column(Text, nullable=False)
    encrypted_key = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    error_message = Column(Text, nullable=True)
    processed_at = Column(DateTime, nullable=True)

class DatabaseManager:
    """Менеджер базы данных"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.engine = None
        self.SessionLocal = None
        self._initialize()
    
    def _initialize(self):
        """Инициализация подключения к базе данных"""
        try:
            self.engine = create_engine(
                self.connection_string,
                pool_pre_ping=True,
                pool_recycle=300,
                echo=False
            )
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            logger.info("База данных инициализирована")
        except Exception as e:
            logger.error(f"Ошибка инициализации базы данных: {e}")
            raise
    
    def create_tables(self):
        """Создание таблиц если они не существуют"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Таблицы созданы/проверены")
        except Exception as e:
            logger.error(f"Ошибка создания таблиц: {e}")
            raise
    
    def get_session(self):
        """Получение сессии базы данных"""
        return self.SessionLocal()
    
    def create_request(self, request_id: str, crm_id: str, request_type: str, 
                      payload: str, encrypted_key: str) -> Optional[JamfRequest]:
        """Создание нового запроса"""
        session = self.get_session()
        try:
            request = JamfRequest(
                request_id=request_id,
                crm_id=crm_id,
                request_type=request_type,
                payload=payload,
                encrypted_key=encrypted_key
            )
            session.add(request)
            session.commit()
            session.refresh(request)
            logger.info(f"Создан запрос {request_id} для CRM {crm_id}")
            return request
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Ошибка создания запроса: {e}")
            return None
        finally:
            session.close()
    
    def get_request(self, request_id: str) -> Optional[JamfRequest]:
        """Получение запроса по ID"""
        session = self.get_session()
        try:
            return session.query(JamfRequest).filter(JamfRequest.request_id == request_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Ошибка получения запроса {request_id}: {e}")
            return None
        finally:
            session.close()
    
    def update_request_status(self, request_id: str, status: str, 
                            jamf_pro_id: str = None, error_message: str = None) -> bool:
        """Обновление статуса запроса"""
        session = self.get_session()
        try:
            request = session.query(JamfRequest).filter(JamfRequest.request_id == request_id).first()
            if request:
                request.status = status
                if jamf_pro_id:
                    request.jamf_pro_id = jamf_pro_id
                if error_message:
                    request.error_message = error_message
                if status in ['completed', 'failed']:
                    request.processed_at = datetime.utcnow()
                session.commit()
                logger.info(f"Обновлен статус запроса {request_id} на {status}")
                return True
            return False
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Ошибка обновления статуса запроса {request_id}: {e}")
            return False
        finally:
            session.close()
    
    def get_pending_requests(self) -> list:
        """Получение всех ожидающих запросов"""
        session = self.get_session()
        try:
            return session.query(JamfRequest).filter(JamfRequest.status == 'pending').all()
        except SQLAlchemyError as e:
            logger.error(f"Ошибка получения ожидающих запросов: {e}")
            return []
        finally:
            session.close()
    
    def get_requests_by_crm(self, crm_id: str) -> list:
        """Получение всех запросов для конкретного CRM"""
        session = self.get_session()
        try:
            return session.query(JamfRequest).filter(JamfRequest.crm_id == crm_id).all()
        except SQLAlchemyError as e:
            logger.error(f"Ошибка получения запросов для CRM {crm_id}: {e}")
            return []
        finally:
            session.close()
