# COPIA ESTE CÓDIGO COMPLETO:

import logging
from datetime import datetime, time

logger = logging.getLogger(__name__)

class ValidadorTurno:
    def __init__(self, base_empleados):
        """
        Inicializa el validador de turnos
        
        Args:
            base_empleados (dict): Base de datos de empleados
        """
        self.base_empleados = base_empleados
        
        # Definir horarios de turnos (puedes ajustar según tus necesidades)
        self.horarios_turnos = {
            "mañana": {
                "inicio": time(6, 0),    # 06:00
                "fin": time(14, 0)       # 14:00
            },
            "tarde": {
                "inicio": time(14, 0),   # 14:00
                "fin": time(22, 0)       # 22:00
            },
            "noche": {
                "inicio": time(22, 0),   # 22:00
                "fin": time(6, 0)        # 06:00 (del día siguiente)
            }
        }
        
        logger.info(f"ValidadorTurno inicializado con {len(base_empleados)} empleados")
    
    def validar(self, legajo, turno_solicitado):
        """
        Valida si un empleado puede trabajar en el turno solicitado
        
        Args:
            legajo (str): Legajo del empleado
            turno_solicitado (str): Turno solicitado
            
        Returns:
            dict: Resultado de la validación
        """
        try:
            legajo_str = str(legajo).strip()
            turno_solicitado = turno_solicitado.lower().strip()
            
            # Verificar que el empleado existe
            if legajo_str not in self.base_empleados:
                return {
                    "valido": False,
                    "mensaje": f"El legajo {legajo_str} no existe"
                }
            
            empleado = self.base_empleados[legajo_str]
            turno_asignado = empleado.get("turno", "").lower().strip()
            
            if not turno_asignado:
                return {
                    "valido": False,
                    "mensaje": "El empleado no tiene turno asignado"
                }
            
            # Validar turno
            if turno_solicitado == turno_asignado:
                # Verificar horario actual
                ahora = datetime.now().time()
                if self.esta_en_horario(turno_solicitado, ahora):
                    logger.info(f"Turno {turno_solicitado} validado para legajo {legajo_str}")
                    return {
                        "valido": True,
                        "mensaje": f"Turno {turno_solicitado} válido",
                        "turno_asignado": turno_asignado,
                        "en_horario": True
                    }
                else:
                    return {
                        "valido": True,
                        "mensaje": f"Turno {turno_solicitado} válido pero fuera de horario",
                        "turno_asignado": turno_asignado,
                        "en_horario": False,
                        "advertencia": "Está fuera del horario normal del turno"
                    }
            else:
                logger.warning(f"Turno incorrecto para legajo {legajo_str}. Asignado: {turno_asignado}, Solicitado: {turno_solicitado}")
                return {
                    "valido": False,
                    "mensaje": f"Turno incorrecto. Su turno asignado es: {turno_asignado}",
                    "turno_asignado": turno_asignado
                }
                
        except Exception as e:
            logger.error(f"Error al validar turno para legajo {legajo}: {str(e)}")
            return {
                "valido": False,
                "mensaje": "Error interno al validar turno"
            }
    
    def esta_en_horario(self, turno, hora_actual):
        """
        Verifica si la hora actual está dentro del horario del turno
        
        Args:
            turno (str): Nombre del turno
            hora_actual (time): Hora actual
            
        Returns:
            bool: True si está en horario, False en caso contrario
        """
        if turno not in self.horarios_turnos:
            logger.warning(f"Turno {turno} no definido en horarios")
            return False
        
        horario = self.horarios_turnos[turno]
        inicio = horario["inicio"]
        fin = horario["fin"]
        
        # Caso especial para turno noche (cruza medianoche)
        if turno == "noche":
            # El turno noche va de 22:00 a 06:00 del día siguiente
            return hora_actual >= inicio or hora_actual <= fin
        else:
            # Turnos normales
            return inicio <= hora_actual <= fin
    
    def obtener_horario_turno(self, turno):
        """
        Obtiene el horario de un turno específico
        
        Args:
            turno (str): Nombre del turno
            
        Returns:
            dict or None: Horario del turno o None si no existe
        """
        return self.horarios_turnos.get(turno.lower(), None)
    
    def listar_turnos_disponibles(self):
        """
        Lista todos los turnos disponibles
        
        Returns:
            list: Lista de nombres de turnos
        """
        return list(self.horarios_turnos.keys())