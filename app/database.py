"""
Database Module
Модуль для работы с Google Cloud PostgreSQL
"""

import os
import logging
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

Base = declarative_base()

class JamfRequest(Base):
    """Модель для хранения запросов к Jamf Pro"""
    __tablename__ = 'jamf_requests'
    
    # Основные поля
    id = Column(Integer, primary_key=True)
    request_id = Column(String(255), unique=True, nullable=False)
    crm_id = Column(String(255), nullable=False)
    jamf_pro_id = Column(String(255), nullable=True)
    
    # Статус и тип запроса
    status = Column(String(50), default='pending')  # pending, processing, completed, failed
    request_type = Column(String(100), nullable=False)  # create, update, delete
    
    # Зашифрованные данные (всегда в base64)
    payload = Column(Text, nullable=False)  # Зашифрованные данные сотрудника
    encrypted_key = Column(String(500), nullable=False)  # Зашифрованный ключ для расшифровки
    
    # Метаданные
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    
    # Обработка ошибок
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Безопасность
    encryption_version = Column(String(10), default='v1')  # Версия шифрования
    checksum = Column(String(64), nullable=True)  # SHA256 хеш для проверки целостности
    
    # Индексы для производительности
    __table_args__ = (
        Index('idx_crm_id', 'crm_id'),
        Index('idx_status', 'status'),
        Index('idx_created_at', 'created_at'),
        Index('idx_request_type', 'request_type'),
    )

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
            # Настройки для PostgreSQL
            self.engine = create_engine(
                self.connection_string,
                pool_pre_ping=True,
                pool_recycle=300,
                pool_size=10,
                max_overflow=20,
                echo=False,
                # PostgreSQL специфичные настройки
                connect_args={
                    "options": "-c timezone=utc"
                }
            )
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            logger.info("База данных PostgreSQL инициализирована")
        except Exception as e:
            logger.error(f"Ошибка инициализации базы данных: {e}")
            raise
    
    def create_tables(self):
        """Создание таблиц если они не существуют"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Таблицы PostgreSQL созданы/проверены")
        except Exception as e:
            logger.error(f"Ошибка создания таблиц: {e}")
            raise
    
    def get_session(self):
        """Получение сессии базы данных"""
        return self.SessionLocal()
    
    def create_request(self, request_id: str, crm_id: str, request_type: str, 
                      payload: str, encrypted_key: str, checksum: str = None) -> Optional[JamfRequest]:
        """
        Создание нового запроса
        
        Args:
            request_id: Уникальный ID запроса
            crm_id: ID CRM системы
            request_type: Тип запроса (create, update, delete)
            payload: Зашифрованные данные сотрудника (base64)
            encrypted_key: Зашифрованный ключ (base64)
            checksum: SHA256 хеш для проверки целостности
        """
        session = self.get_session()
        try:
            request = JamfRequest(
                request_id=request_id,
                crm_id=crm_id,
                request_type=request_type,
                payload=payload,  # Уже зашифрованные данные
                encrypted_key=encrypted_key,  # Зашифрованный ключ
                checksum=checksum,
                encryption_version='v1'
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
                    request.retry_count += 1
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
    
    def get_pending_requests(self, limit: int = 100) -> list:
        """Получение ожидающих запросов с лимитом"""
        session = self.get_session()
        try:
            return session.query(JamfRequest)\
                .filter(JamfRequest.status == 'pending')\
                .order_by(JamfRequest.created_at.asc())\
                .limit(limit)\
                .all()
        except SQLAlchemyError as e:
            logger.error(f"Ошибка получения ожидающих запросов: {e}")
            return []
        finally:
            session.close()
    
    def get_requests_by_crm(self, crm_id: str, limit: int = 50) -> list:
        """Получение запросов для конкретного CRM"""
        session = self.get_session()
        try:
            return session.query(JamfRequest)\
                .filter(JamfRequest.crm_id == crm_id)\
                .order_by(JamfRequest.created_at.desc())\
                .limit(limit)\
                .all()
        except SQLAlchemyError as e:
            logger.error(f"Ошибка получения запросов для CRM {crm_id}: {e}")
            return []
        finally:
            session.close()
    
    def cleanup_old_requests(self, days: int = 30) -> int:
        """Очистка старых запросов"""
        session = self.get_session()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            deleted = session.query(JamfRequest)\
                .filter(JamfRequest.created_at < cutoff_date)\
                .filter(JamfRequest.status.in_(['completed', 'failed']))\
                .delete()
            session.commit()
            logger.info(f"Удалено {deleted} старых запросов")
            return deleted
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Ошибка очистки старых запросов: {e}")
            return 0
        finally:
            session.close()
