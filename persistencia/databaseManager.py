import logging
import json
import os
from datetime import datetime
from models.database import (
    DATABASE_AVAILABLE, Empleado, Asistencia, 
    get_db_session, create_tables
)

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.use_postgresql = DATABASE_AVAILABLE
        if self.use_postgresql:
            # Crear tablas e inicializar PostgreSQL
            create_tables()
            self._migrar_desde_json_si_necesario()
        logger.info(f"DatabaseManager inicializado - PostgreSQL: {self.use_postgresql}")
    
    def _migrar_desde_json_si_necesario(self):
        """Migra datos desde JSON a PostgreSQL si es la primera vez"""
        if not self.use_postgresql:
            return
            
        session = get_db_session()
        if not session:
            return
            
        try:
            # Verificar si ya hay datos
            count = session.query(Empleado).count()
            if count > 0:
                logger.info(f"Ya hay {count} empleados en PostgreSQL")
                return
            
            # Intentar migrar desde JSON
            json_path = "data/embeddings.json"
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    datos = json.load(f)
                
                for legajo, info in datos.items():
                    empleado = Empleado(
                        legajo=legajo,
                        area=info.get('area', ''),
                        rol=info.get('rol', ''),
                        turno=info.get('turno', ''),
                        embedding=info.get('embedding', [])
                    )
                    session.add(empleado)
                
                session.commit()
                logger.info(f"Migrados {len(datos)} empleados desde JSON a PostgreSQL")
            else:
                # Crear empleados de ejemplo
                empleados_ejemplo = [
                    {'legajo': '40895446', 'area': 'Producción', 'rol': 'Operario', 'turno': 'mañana'},
                    {'legajo': '12345678', 'area': 'Administración', 'rol': 'Supervisor', 'turno': 'tarde'},
                    {'legajo': '87654321', 'area': 'Mantenimiento', 'rol': 'Técnico', 'turno': 'noche'}
                ]
                
                for emp_data in empleados_ejemplo:
                    empleado = Empleado(
                        legajo=emp_data['legajo'],
                        area=emp_data['area'],
                        rol=emp_data['rol'],
                        turno=emp_data['turno'],
                        embedding=[]  # Sin embedding inicial
                    )
                    session.add(empleado)
                
                session.commit()
                logger.info("Creados empleados de ejemplo en PostgreSQL")
                
        except Exception as e:
            logger.error(f"Error en migración: {e}")
            session.rollback()
        finally:
            session.close()
    
    def cargar_empleados(self):
        """Carga empleados - compatible con código existente"""
        if self.use_postgresql:
            return self._cargar_empleados_postgresql()
        else:
            return self._cargar_empleados_json()
    
    def _cargar_empleados_postgresql(self):
        """Carga empleados desde PostgreSQL"""
        session = get_db_session()
        if not session:
            return {}
            
        try:
            empleados = session.query(Empleado).all()
            resultado = {}
            
            for emp in empleados:
                resultado[emp.legajo] = {
                    "area": emp.area,
                    "rol": emp.rol,
                    "turno": emp.turno,
                    "embedding": emp.embedding
                }
            
            logger.info(f"Cargados {len(resultado)} empleados desde PostgreSQL")
            return resultado
            
        except Exception as e:
            logger.error(f"Error cargando empleados PostgreSQL: {e}")
            return {}
        finally:
            session.close()
    
    def _cargar_empleados_json(self):
        """Carga empleados desde JSON (fallback)"""
        try:
            ruta = "data/embeddings.json"
            if not os.path.exists(ruta):
                return {}
            with open(ruta, "r") as f:
                data = json.load(f)
                logger.info(f"Cargados {len(data)} empleados desde JSON")
                return data
        except Exception as e:
            logger.error(f"Error cargando JSON: {e}")
            return {}
    
    def guardar_empleado(self, legajo, area, rol, turno, embedding):
        """Guarda un empleado"""
        if self.use_postgresql:
            return self._guardar_empleado_postgresql(legajo, area, rol, turno, embedding)
        else:
            return self._guardar_empleado_json(legajo, area, rol, turno, embedding)
    
    def _guardar_empleado_postgresql(self, legajo, area, rol, turno, embedding):
        """Guarda empleado en PostgreSQL"""
        session = get_db_session()
        if not session:
            return {"exito": False, "mensaje": "Error de conexión a base de datos"}
            
        try:
            # Verificar si existe
            existente = session.query(Empleado).filter(Empleado.legajo == legajo).first()
            if existente:
                return {"exito": False, "mensaje": "Legajo ya registrado"}
            
            # Crear nuevo
            nuevo = Empleado(
                legajo=legajo,
                area=area,
                rol=rol,
                turno=turno,
                embedding=embedding
            )
            
            session.add(nuevo)
            session.commit()
            
            logger.info(f"Empleado {legajo} guardado en PostgreSQL")
            return {"exito": True, "mensaje": "Empleado registrado correctamente"}
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error guardando empleado PostgreSQL: {e}")
            return {"exito": False, "mensaje": "Error al guardar empleado"}
        finally:
            session.close()
    
    def _guardar_empleado_json(self, legajo, area, rol, turno, embedding):
        """Guarda empleado en JSON (fallback)"""
        try:
            base = self._cargar_empleados_json()
            if legajo in base:
                return {"exito": False, "mensaje": "Legajo ya registrado"}
            
            base[legajo] = {
                "area": area,
                "rol": rol,
                "turno": turno,
                "embedding": embedding
            }
            
            os.makedirs("data", exist_ok=True)
            with open("data/embeddings.json", "w") as f:
                json.dump(base, f, indent=4)
            
            logger.info(f"Empleado {legajo} guardado en JSON")
            return {"exito": True, "mensaje": "Empleado registrado correctamente"}
            
        except Exception as e:
            logger.error(f"Error guardando empleado JSON: {e}")
            return {"exito": False, "mensaje": "Error al guardar empleado"}
    
    def registrar_asistencia(self, legajo, turno, tipo_registro="entrada"):
        """Registra una asistencia"""
        if self.use_postgresql:
            return self._registrar_asistencia_postgresql(legajo, turno, tipo_registro)
        else:
            # Usar el sistema JSON existente
            from persistencia.registrarAsistencia import RegistrarAsistencias
            asistencia = RegistrarAsistencias()
            return asistencia.registrar(legajo, turno, tipo_registro)
    
    def _registrar_asistencia_postgresql(self, legajo, turno, tipo_registro):
        """Registra asistencia en PostgreSQL"""
        session = get_db_session()
        if not session:
            return {"exito": False, "mensaje": "Error de conexión a base de datos"}
            
        try:
            ahora = datetime.now()
            
            nueva_asistencia = Asistencia(
                legajo=legajo,
                turno=turno,
                tipo=tipo_registro.lower(),
                fecha=ahora.strftime("%Y-%m-%d"),
                hora=ahora.strftime("%H:%M:%S")
            )
            
            session.add(nueva_asistencia)
            session.commit()
            
            logger.info(f"Asistencia registrada en PostgreSQL: {legajo} - {tipo_registro}")
            return {"exito": True, "mensaje": f"{tipo_registro.capitalize()} registrada correctamente"}
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error registrando asistencia PostgreSQL: {e}")
            return {"exito": False, "mensaje": "Error al registrar asistencia"}
        finally:
            session.close()

# Instancia global
db_manager = DatabaseManager()