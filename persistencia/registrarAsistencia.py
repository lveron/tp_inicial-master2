# persistencia/registrarAsistencia.py
import json
import os
import logging
from datetime import datetime, time, timedelta

logger = logging.getLogger(__name__)

class RegistrarAsistencias:
    def __init__(self, archivo_asistencias="data/asistencias.json"):
        """
        Inicializa el registrador de asistencias
        
        Args:
            archivo_asistencias (str): Ruta del archivo de asistencias
        """
        self.archivo_asistencias = archivo_asistencias
        
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(archivo_asistencias), exist_ok=True)
        
        # Crear archivo si no existe
        if not os.path.exists(archivo_asistencias):
            self._crear_archivo_vacio()
            
        logger.info(f"RegistrarAsistencias inicializado con archivo: {archivo_asistencias}")
    
    def _crear_archivo_vacio(self):
        """Crea un archivo de asistencias vacío"""
        try:
            with open(self.archivo_asistencias, "w") as f:
                json.dump([], f)
            logger.info("Archivo de asistencias creado")
        except Exception as e:
            logger.error(f"Error al crear archivo de asistencias: {e}")
            raise
    
    def cargar_asistencias(self):
        """
        Carga las asistencias desde el archivo
        
        Returns:
            list: Lista de registros de asistencia
        """
        try:
            with open(self.archivo_asistencias, "r") as f:
                asistencias = json.load(f)
                return asistencias if isinstance(asistencias, list) else []
        except json.JSONDecodeError:
            logger.warning("Archivo de asistencias corrupto, iniciando vacío")
            return []
        except FileNotFoundError:
            logger.info("Archivo de asistencias no encontrado, creando nuevo")
            self._crear_archivo_vacio()
            return []
        except Exception as e:
            logger.error(f"Error al cargar asistencias: {e}")
            return []
    
    def guardar_asistencias(self, asistencias):
        """
        Guarda las asistencias en el archivo
        
        Args:
            asistencias (list): Lista de registros de asistencia
        """
        try:
            with open(self.archivo_asistencias, "w") as f:
                json.dump(asistencias, f, indent=2, default=str)
            logger.info("Asistencias guardadas correctamente")
        except Exception as e:
            logger.error(f"Error al guardar asistencias: {e}")
            raise
    
    def registrar(self, legajo, turno, tipo_registro="entrada"):
        """
        Registra una asistencia
        
        Args:
            legajo (str): Legajo del empleado
            turno (str): Turno del empleado
            tipo_registro (str): Tipo de registro ("entrada" o "salida")
            
        Returns:
            dict: Resultado del registro
        """
        try:
            asistencias = self.cargar_asistencias()
            
            ahora = datetime.now()
            
            nuevo_registro = {
                "legajo": str(legajo),
                "turno": turno.lower(),
                "tipo": tipo_registro.lower(),
                "fecha": ahora.strftime("%Y-%m-%d"),
                "hora": ahora.strftime("%H:%M:%S"),
                "timestamp": ahora.isoformat()
            }
            
            asistencias.append(nuevo_registro)
            self.guardar_asistencias(asistencias)
            
            logger.info(f"Asistencia registrada: {legajo} - {tipo_registro} - {ahora}")
            
            return {
                "exito": True,
                "mensaje": f"{tipo_registro.capitalize()} registrada correctamente",
                "registro": nuevo_registro
            }
            
        except Exception as e:
            logger.error(f"Error al registrar asistencia: {e}")
            return {
                "exito": False,
                "mensaje": "Error al registrar asistencia"
            }
    
    def obtener_ultimo_tipo(self, legajo):
        """
        Obtiene el último tipo de registro para un empleado
        
        Args:
            legajo (str): Legajo del empleado
            
        Returns:
            str: "entrada" o "salida" o "entrada" por defecto
        """
        try:
            asistencias = self.cargar_asistencias()
            legajo_str = str(legajo)
            
            # Filtrar por legajo y ordenar por timestamp descendente
            registros_empleado = [
                reg for reg in asistencias 
                if reg.get("legajo") == legajo_str
            ]
            
            if not registros_empleado:
                return "salida"  # Si no hay registros, el próximo debería ser entrada
            
            # Ordenar por timestamp para obtener el más reciente
            registros_empleado.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            ultimo_tipo = registros_empleado[0].get("tipo", "salida")
            
            # Retornar el tipo opuesto
            return "entrada" if ultimo_tipo == "salida" else "salida"
            
        except Exception as e:
            logger.error(f"Error al obtener último tipo para {legajo}: {e}")
            return "entrada"
    
    def puede_registrar_hoy(self, legajo, tipo_registro):
        """
        Verifica si un empleado puede registrar un tipo específico hoy
        
        Args:
            legajo (str): Legajo del empleado
            tipo_registro (str): Tipo de registro a verificar
            
        Returns:
            bool: True si puede registrar, False en caso contrario
        """
        try:
            asistencias = self.cargar_asistencias()
            legajo_str = str(legajo)
            hoy = datetime.now().strftime("%Y-%m-%d")
            
            # Buscar registros de hoy para este empleado y tipo
            registros_hoy = [
                reg for reg in asistencias
                if (reg.get("legajo") == legajo_str and 
                    reg.get("fecha") == hoy and
                    reg.get("tipo") == tipo_registro.lower())
            ]
            
            # Si ya hay un registro del mismo tipo hoy, no puede registrar otro
            return len(registros_hoy) == 0
            
        except Exception as e:
            logger.error(f"Error al verificar si puede registrar: {e}")
            return True  # En caso de error, permitir el registro
    
    def calcular_puntualidad(self, timestamp, tipo_registro, turno):
        """
        Calcula si la asistencia es puntual, tardía o temprana
        
        Args:
            timestamp (str): Timestamp del registro
            tipo_registro (str): Tipo de registro
            turno (str): Turno del empleado
            
        Returns:
            str: "puntual", "tardío", "temprano", "fuera de turno"
        """
        try:
            hora_registro = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).time()
            
            # Definir horarios por turno
            horarios = {
                "mañana": {
                    "entrada": {"inicio": time(5, 30), "fin": time(6, 30)},
                    "salida": {"inicio": time(13, 30), "fin": time(14, 30)}
                },
                "tarde": {
                    "entrada": {"inicio": time(13, 30), "fin": time(14, 30)},
                    "salida": {"inicio": time(21, 30), "fin": time(22, 30)}
                },
                "noche": {
                    "entrada": {"inicio": time(21, 30), "fin": time(22, 30)},
                    "salida": {"inicio": time(5, 30), "fin": time(6, 30)}
                }
            }
            
            turno_lower = turno.lower()
            tipo_lower = tipo_registro.lower()
            
            if turno_lower not in horarios:
                return "fuera de turno"
            
            if tipo_lower not in horarios[turno_lower]:
                return "fuera de turno"
            
            horario = horarios[turno_lower][tipo_lower]
            inicio = horario["inicio"]
            fin = horario["fin"]
            
            # Verificar puntualidad
            if inicio <= hora_registro <= fin:
                return "puntual"
            elif hora_registro < inicio:
                return "temprano"
            else:
                return "tardío"
                
        except Exception as e:
            logger.error(f"Error al calcular puntualidad: {e}")
            return "puntual"  # Por defecto, considerar puntual en caso de error
    
    def obtener_asistencias_empleado(self, legajo, fecha_inicio=None, fecha_fin=None):
        """
        Obtiene las asistencias de un empleado en un rango de fechas
        
        Args:
            legajo (str): Legajo del empleado
            fecha_inicio (str, optional): Fecha de inicio (YYYY-MM-DD)
            fecha_fin (str, optional): Fecha de fin (YYYY-MM-DD)
            
        Returns:
            list: Lista de asistencias del empleado
        """
        try:
            asistencias = self.cargar_asistencias()
            legajo_str = str(legajo)
            
            registros = [
                reg for reg in asistencias
                if reg.get("legajo") == legajo_str
            ]
            
            if fecha_inicio:
                registros = [
                    reg for reg in registros
                    if reg.get("fecha", "") >= fecha_inicio
                ]
            
            if fecha_fin:
                registros = [
                    reg for reg in registros
                    if reg.get("fecha", "") <= fecha_fin
                ]
            
            # Ordenar por timestamp descendente
            registros.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            return registros
            
        except Exception as e:
            logger.error(f"Error al obtener asistencias de {legajo}: {e}")
            return []
    
    def obtener_estadisticas(self, legajo, mes=None, año=None):
        """
        Obtiene estadísticas de asistencia para un empleado
        
        Args:
            legajo (str): Legajo del empleado
            mes (int, optional): Mes a analizar
            año (int, optional): Año a analizar
            
        Returns:
            dict: Estadísticas de asistencia
        """
        try:
            if not mes:
                mes = datetime.now().month
            if not año:
                año = datetime.now().year
                
            fecha_inicio = f"{año}-{mes:02d}-01"
            
            # Calcular último día del mes
            if mes == 12:
                siguiente_mes = datetime(año + 1, 1, 1)
            else:
                siguiente_mes = datetime(año, mes + 1, 1)
            
            ultimo_dia = (siguiente_mes - timedelta(days=1)).day
            fecha_fin = f"{año}-{mes:02d}-{ultimo_dia:02d}"
            
            asistencias = self.obtener_asistencias_empleado(legajo, fecha_inicio, fecha_fin)
            
            # Calcular estadísticas
            total_registros = len(asistencias)
            entradas = len([reg for reg in asistencias if reg.get("tipo") == "entrada"])
            salidas = len([reg for reg in asistencias if reg.get("tipo") == "salida"])
            
            # Días únicos con asistencia
            fechas_unicas = set(reg.get("fecha") for reg in asistencias)
            dias_trabajados = len(fechas_unicas)
            
            return {
                "legajo": legajo,
                "mes": mes,
                "año": año,
                "total_registros": total_registros,
                "entradas": entradas,
                "salidas": salidas,
                "dias_trabajados": dias_trabajados,
                "registros": asistencias[:10]  # Solo los últimos 10
            }
            
        except Exception as e:
            logger.error(f"Error al obtener estadísticas para {legajo}: {e}")
            return {}

# ===================================================================

# persistencia/__init__.py
# Archivo vacío