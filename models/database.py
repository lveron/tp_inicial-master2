import os
from sqlalchemy import create_engine, Column, String, Integer, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    DATABASE_AVAILABLE = True
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()

    class Empleado(Base):
        __tablename__ = 'empleados'
        
        legajo = Column(String(50), primary_key=True)
        area = Column(String(100), nullable=False)
        rol = Column(String(100), nullable=False)
        turno = Column(String(20), nullable=False)
        embedding = Column(JSON, nullable=False)
        fecha_registro = Column(DateTime, default=datetime.utcnow)

    class Asistencia(Base):
        __tablename__ = 'asistencias'
        
        id = Column(Integer, primary_key=True, autoincrement=True)
        legajo = Column(String(50), nullable=False)
        turno = Column(String(20), nullable=False)
        tipo = Column(String(10), nullable=False)
        fecha = Column(String(10), nullable=False)
        hora = Column(String(8), nullable=False)
        timestamp = Column(DateTime, default=datetime.utcnow)

    def create_tables():
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Tablas PostgreSQL creadas exitosamente")
            return True
        except Exception as e:
            logger.error(f"Error creando tablas: {e}")
            return False

    def get_db_session():
        return SessionLocal()

else:
    DATABASE_AVAILABLE = False
    
    class Empleado:
        pass
    
    class Asistencia:
        pass
    
    def create_tables():
        return False
    
    def get_db_session():
        return None