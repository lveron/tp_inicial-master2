import psycopg2
import os
from datetime import datetime, date, time

class RegistrarAsistencias:
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
            
        except Exception as e:
            print(f"ERROR conectando a PostgreSQL en RegistrarAsistencias: {e}")
            raise e
    
    def registrar(self, legajo, turno):
        """
        Registra una asistencia (entrada o salida) para un empleado
        Determina automáticamente si es entrada o salida basado en el último registro
        """
        try:
            cursor = self.connection.cursor()
            
            # Obtener la fecha y hora actual
            ahora = datetime.now()
            fecha_hoy = ahora.date()
            hora_actual = ahora.time()
            
            # Verificar el último registro del empleado para hoy
            cursor.execute("""
                SELECT tipo FROM asistencias 
                WHERE legajo = %s AND fecha = %s 
                ORDER BY timestamp DESC 
                LIMIT 1
            """, (legajo, fecha_hoy))
            
            ultimo_registro = cursor.fetchone()
            
            # Determinar tipo de registro (entrada o salida)
            if ultimo_registro is None or ultimo_registro[0] == 'salida':
                tipo = 'entrada'
            else:
                tipo = 'salida'
            
            # Insertar el registro de asistencia
            cursor.execute("""
                INSERT INTO asistencias (legajo, turno, tipo, fecha, hora)
                VALUES (%s, %s, %s, %s, %s)
            """, (legajo, turno, tipo, fecha_hoy, hora_actual))
            
            cursor.close()
            
            print(f"INFO: Asistencia registrada - {legajo} - {tipo} - {turno}")
            return True
            
        except Exception as e:
            print(f"ERROR registrando asistencia: {e}")
            return False
    
    def obtener_asistencias_empleado(self, legajo):
        """Obtiene todas las asistencias de un empleado específico"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT legajo, turno, tipo, fecha, hora, timestamp
                FROM asistencias 
                WHERE legajo = %s 
                ORDER BY timestamp DESC
            """, (legajo,))
            
            asistencias = []
            for row in cursor.fetchall():
                asistencia = {
                    'legajo': row[0],
                    'turno': row[1],
                    'tipo': row[2],
                    'fecha': row[3].strftime('%Y-%m-%d') if row[3] else None,
                    'hora': row[4].strftime('%H:%M:%S') if row[4] else None,
                    'timestamp': row[5].isoformat() if row[5] else None
                }
                asistencias.append(asistencia)
            
            cursor.close()
            return asistencias
            
        except Exception as e:
            print(f"ERROR obteniendo asistencias: {e}")
            return []
    
    def obtener_asistencias_fecha(self, fecha):
        """Obtiene todas las asistencias de una fecha específica"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT legajo, turno, tipo, fecha, hora, timestamp
                FROM asistencias 
                WHERE fecha = %s 
                ORDER BY timestamp
            """, (fecha,))
            
            asistencias = []
            for row in cursor.fetchall():
                asistencia = {
                    'legajo': row[0],
                    'turno': row[1],
                    'tipo': row[2],
                    'fecha': row[3].strftime('%Y-%m-%d') if row[3] else None,
                    'hora': row[4].strftime('%H:%M:%S') if row[4] else None,
                    'timestamp': row[5].isoformat() if row[5] else None
                }
                asistencias.append(asistencia)
            
            cursor.close()
            return asistencias
            
        except Exception as e:
            print(f"ERROR obteniendo asistencias por fecha: {e}")
            return []
    
    def obtener_ultimo_registro(self, legajo):
        """Obtiene el último registro de asistencia de un empleado"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT legajo, turno, tipo, fecha, hora, timestamp
                FROM asistencias 
                WHERE legajo = %s 
                ORDER BY timestamp DESC
                LIMIT 1
            """, (legajo,))
            
            row = cursor.fetchone()
            cursor.close()
            
            if row:
                return {
                    'legajo': row[0],
                    'turno': row[1],
                    'tipo': row[2],
                    'fecha': row[3].strftime('%Y-%m-%d') if row[3] else None,
                    'hora': row[4].strftime('%H:%M:%S') if row[4] else None,
                    'timestamp': row[5].isoformat() if row[5] else None
                }
            return None
            
        except Exception as e:
            print(f"ERROR obteniendo último registro: {e}")
            return None
