"""
Database Module
Module for Google Cloud PostgreSQL operations
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
    """Model for storing Jamf Pro requests"""
    __tablename__ = 'jamf_requests'
    
    id = Column(Integer, primary_key=True)
    request_id = Column(String(255), unique=True, nullable=False)
    crm_id = Column(String(255), nullable=False)
    jamf_pro_id = Column(String(255), nullable=True)
    
    status = Column(String(50), default='pending')
    request_type = Column(String(100), nullable=False)
    
    payload = Column(Text, nullable=False)
    encrypted_key = Column(String(500), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    encryption_version = Column(String(10), default='v1')
    checksum = Column(String(64), nullable=True)
    __table_args__ = (
        Index('idx_crm_id', 'crm_id'),
        Index('idx_status', 'status'),
        Index('idx_created_at', 'created_at'),
        Index('idx_request_type', 'request_type'),
    )

class DatabaseManager:
    """Database manager"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.engine = None
        self.SessionLocal = None
        self._initialize()
    
    def _initialize(self):
        """Initialize database connection"""
        try:
            # PostgreSQL settings
            self.engine = create_engine(
                self.connection_string,
                pool_pre_ping=True,
                pool_recycle=300,
                pool_size=10,
                max_overflow=20,
                echo=False,
                # PostgreSQL specific settings
                connect_args={
                    "options": "-c timezone=utc"
                }
            )
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            logger.info("PostgreSQL database initialized")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def create_tables(self):
        """Create tables if they don't exist"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("PostgreSQL tables created/verified")
        except Exception as e:
            logger.error(f"Table creation failed: {e}")
            raise
    
    def get_session(self):
        """Get database session"""
        return self.SessionLocal()
    
    def create_request(self, request_id: str, crm_id: str, request_type: str, 
                      payload: str, encrypted_key: str, checksum: str = None) -> Optional[JamfRequest]:
        """
        Create new request
        
        Args:
            request_id: Unique request ID
            crm_id: CRM system ID
            request_type: Request type (create, update, delete)
            payload: Encrypted employee data (base64)
            encrypted_key: Encrypted key (base64)
            checksum: SHA256 hash for integrity verification
        """
        session = self.get_session()
        try:
            request = JamfRequest(
                request_id=request_id,
                crm_id=crm_id,
                request_type=request_type,
                payload=payload,
                encrypted_key=encrypted_key,
                checksum=checksum,
                encryption_version='v1'
            )
            session.add(request)
            session.commit()
            session.refresh(request)
            logger.info(f"Created request {request_id} for CRM {crm_id}")
            return request
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to create request: {e}")
            return None
        finally:
            session.close()
    
    def get_request(self, request_id: str) -> Optional[JamfRequest]:
        """Get request by ID"""
        session = self.get_session()
        try:
            return session.query(JamfRequest).filter(JamfRequest.request_id == request_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Failed to get request {request_id}: {e}")
            return None
        finally:
            session.close()
    
    def update_request_status(self, request_id: str, status: str, 
                            jamf_pro_id: str = None, error_message: str = None) -> bool:
        """Update request status"""
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
                logger.info(f"Updated request {request_id} status to {status}")
                return True
            return False
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to update request {request_id} status: {e}")
            return False
        finally:
            session.close()
    
    def get_pending_requests(self, limit: int = 100) -> list:
        """Get pending requests with limit"""
        session = self.get_session()
        try:
            return session.query(JamfRequest)\
                .filter(JamfRequest.status == 'pending')\
                .order_by(JamfRequest.created_at.asc())\
                .limit(limit)\
                .all()
        except SQLAlchemyError as e:
            logger.error(f"Failed to get pending requests: {e}")
            return []
        finally:
            session.close()
    
    def get_requests_by_crm(self, crm_id: str, limit: int = 50) -> list:
        """Get requests for specific CRM"""
        session = self.get_session()
        try:
            return session.query(JamfRequest)\
                .filter(JamfRequest.crm_id == crm_id)\
                .order_by(JamfRequest.created_at.desc())\
                .limit(limit)\
                .all()
        except SQLAlchemyError as e:
            logger.error(f"Failed to get requests for CRM {crm_id}: {e}")
            return []
        finally:
            session.close()
    
    def cleanup_old_requests(self, days: int = 30) -> int:
        """Cleanup old requests"""
        session = self.get_session()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            deleted = session.query(JamfRequest)\
                .filter(JamfRequest.created_at < cutoff_date)\
                .filter(JamfRequest.status.in_(['completed', 'failed']))\
                .delete()
            session.commit()
            logger.info(f"Deleted {deleted} old requests")
            return deleted
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to cleanup old requests: {e}")
            return 0
        finally:
            session.close()
