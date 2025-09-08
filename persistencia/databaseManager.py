import psycopg2
import json
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        """Inicializa la conexión con la base de datos PostgreSQL"""
        try:
            # Obtener URL de conexión desde variable de entorno
            self.database_url = os.environ.get('DATABASE_URL')
            if not self.database_url:
                raise Exception("DATABASE_URL no encontrada en variables de entorno")
            
            # Establecer conexión
            self.connection = psycopg2.connect(self.database_url)
            self.connection.autocommit = True
            
            # Crear tablas si no existen
            self._crear_tablas()
            logger.info("DatabaseManager inicializado correctamente con PostgreSQL")
            
        except Exception as e:
            logger.error(f"ERROR conectando a PostgreSQL: {e}")
            raise e
    
    def _crear_tablas(self):
        """Crea las tablas necesarias si no existen"""
        try:
            cursor = self.connection.cursor()
            
            # Tabla de empleados
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS empleados (
                    legajo VARCHAR(50) PRIMARY KEY,
                    area VARCHAR(100) NOT NULL,
                    rol VARCHAR(100) NOT NULL,
                    turno VARCHAR(20) NOT NULL CHECK (turno IN ('mañana', 'tarde', 'noche')),
                    embedding JSONB NOT NULL,
                    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla de asistencias
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS asistencias (
                    id SERIAL PRIMARY KEY,
                    legajo VARCHAR(50) NOT NULL,
                    turno VARCHAR(20) NOT NULL,
                    tipo VARCHAR(10) NOT NULL CHECK (tipo IN ('entrada', 'salida')),
                    fecha DATE NOT NULL,
                    hora TIME NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (legajo) REFERENCES empleados(legajo)
                )
            """)
            
            cursor.close()
            logger.info("Tablas de base de datos verificadas/creadas")
            
        except Exception as e:
            logger.error(f"ERROR creando tablas: {e}")
            raise e
    
    def cargar_empleados(self):
        """
        Carga todos los empleados y los retorna en formato compatible con el sistema JSON
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT legajo, area, rol, turno, embedding, fecha_registro 
                FROM empleados 
                ORDER BY legajo
            """)
            
            empleados_dict = {}
            for row in cursor.fetchall():
                legajo = row[0]
                empleados_dict[legajo] = {
                    'area': row[1],
                    'rol': row[2],
                    'turno': row[3],
                    'embedding': json.loads(row[4]) if isinstance(row[4], str) else row[4],
                    'fecha_registro': row[5].isoformat() if row[5] else None
                }
            
            cursor.close()
            logger.info(f"Cargados {len(empleados_dict)} empleados desde PostgreSQL")
            return empleados_dict
            
        except Exception as e:
            logger.error(f"ERROR cargando empleados: {e}")
            return {}
    
    def obtener_todos_empleados(self):
        """
        Obtiene todos los empleados de la base de datos
        Retorna una lista de diccionarios con la información de cada empleado
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT legajo, area, rol, turno, embedding, fecha_registro 
                FROM empleados 
                ORDER BY legajo
            """)
            
            empleados = []
            for row in cursor.fetchall():
                empleado = {
                    'legajo': row[0],
                    'area': row[1],
                    'rol': row[2],
                    'turno': row[3],
                    'embedding': json.loads(row[4]) if isinstance(row[4], str) else row[4],
                    'fecha_registro': row[5]
                }
                empleados.append(empleado)
            
            cursor.close()
            return empleados
            
        except Exception as e:
            logger.error(f"ERROR obteniendo empleados: {e}")
            return []
    
    def contar_empleados(self):
        """Cuenta el número total de empleados"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM empleados")
            count = cursor.fetchone()[0]
            cursor.close()
            return count
        except Exception as e:
            logger.error(f"ERROR contando empleados: {e}")
            return 0
    
    def empleado_existe(self, legajo):
        """Verifica si un empleado con el legajo dado ya existe"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM empleados WHERE legajo = %s", (legajo,))
            count = cursor.fetchone()[0]
            cursor.close()
            return count > 0
        except Exception as e:
            logger.error(f"ERROR verificando empleado: {e}")
            return False
    
    def guardar_empleado(self, legajo, area, rol, turno, embedding):
        """Guarda un nuevo empleado en la base de datos"""
        try:
            # Verificar si ya existe
            if self.empleado_existe(legajo):
                return {"exito": False, "mensaje": "Empleado ya existe"}
            
            cursor = self.connection.cursor()
            
            # Convertir embedding a JSON si es una lista
            embedding_json = json.dumps(embedding) if isinstance(embedding, list) else embedding
            
            cursor.execute("""
                INSERT INTO empleados (legajo, area, rol, turno, embedding)
                VALUES (%s, %s, %s, %s, %s)
            """, (legajo, area, rol, turno, embedding_json))
            
            cursor.close()
            logger.info(f"Empleado {legajo} guardado en PostgreSQL")
            return {"exito": True, "mensaje": "Empleado registrado correctamente"}
            
        except Exception as e:
            logger.error(f"ERROR guardando empleado: {e}")
            return {"exito": False, "mensaje": f"Error guardando empleado: {str(e)}"}
    
    def registrar_empleado(self, legajo, area, rol, turno, embedding):
        """Registra un nuevo empleado en la base de datos"""
        return self.guardar_empleado(legajo, area, rol, turno, embedding)
    
    def registrar_asistencia(self, legajo, turno, tipo):
        """Registra una asistencia en la base de datos"""
        try:
            cursor = self.connection.cursor()
            
            # Obtener la fecha y hora actual
            ahora = datetime.now()
            fecha_hoy = ahora.date()
            hora_actual = ahora.time()
            
            # Insertar el registro de asistencia
            cursor.execute("""
                INSERT INTO asistencias (legajo, turno, tipo, fecha, hora)
                VALUES (%s, %s, %s, %s, %s)
            """, (legajo, turno, tipo, fecha_hoy, hora_actual))
            
            cursor.close()
            logger.info(f"Asistencia registrada: {legajo} - {tipo} - {turno}")
            return {"exito": True, "mensaje": f"{tipo.capitalize()} registrada correctamente"}
            
        except Exception as e:
            logger.error(f"ERROR registrando asistencia: {e}")
            return {"exito": False, "mensaje": f"Error registrando asistencia: {str(e)}"}
    
    def obtener_empleado(self, legajo):
        """Obtiene un empleado específico por legajo"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT legajo, area, rol, turno, embedding, fecha_registro 
                FROM empleados 
                WHERE legajo = %s
            """, (legajo,))
            
            row = cursor.fetchone()
            cursor.close()
            
            if row:
                return {
                    'legajo': row[0],
                    'area': row[1],
                    'rol': row[2],
                    'turno': row[3],
                    'embedding': json.loads(row[4]) if isinstance(row[4], str) else row[4],
                    'fecha_registro': row[5]
                }
            return None
            
        except Exception as e:
            logger.error(f"ERROR obteniendo empleado: {e}")
            return None
    
    def eliminar_empleado(self, legajo):
        """Elimina un empleado de la base de datos"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM empleados WHERE legajo = %s", (legajo,))
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"ERROR eliminando empleado: {e}")
            return False
    
    def cerrar_conexion(self):
        """Cierra la conexión con la base de datos"""
        try:
            if self.connection:
                self.connection.close()
        except Exception as e:
            logger.error(f"ERROR cerrando conexión: {e}")
    
    def __del__(self):
        """Destructor para cerrar automáticamente la conexión"""
        self.cerrar_conexion()

# Instancia global para ser importada por app.py
try:
    db_manager = DatabaseManager()
except Exception as e:
    logger.error(f"No se pudo inicializar DatabaseManager: {e}")
    db_manager = None
