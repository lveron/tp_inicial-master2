# COPIA ESTE CÓDIGO COMPLETO:

import logging

logger = logging.getLogger(__name__)

class ValidadorLegajo:
    def __init__(self, base_empleados):
        """
        Inicializa el validador de legajos
        
        Args:
            base_empleados (dict): Base de datos de empleados
        """
        self.base_empleados = base_empleados
        logger.info(f"ValidadorLegajo inicializado con {len(base_empleados)} empleados")
    
    def validar(self, legajo):
        """
        Valida si un legajo existe en la base de datos
        
        Args:
            legajo (str): Legajo a validar
            
        Returns:
            dict: Resultado de la validación
        """
        try:
            if not legajo:
                return {
                    "valido": False,
                    "mensaje": "El legajo no puede estar vacío"
                }
            
            legajo_str = str(legajo).strip()
            
            if legajo_str in self.base_empleados:
                empleado = self.base_empleados[legajo_str]
                logger.info(f"Legajo {legajo_str} validado correctamente")
                
                return {
                    "valido": True,
                    "mensaje": "Legajo válido",
                    "empleado": {
                        "legajo": legajo_str,
                        "area": empleado.get("area", ""),
                        "rol": empleado.get("rol", ""),
                        "turno": empleado.get("turno", "")
                    }
                }
            else:
                logger.warning(f"Legajo {legajo_str} no encontrado en la base de datos")
                return {
                    "valido": False,
                    "mensaje": f"El legajo {legajo_str} no está registrado"
                }
                
        except Exception as e:
            logger.error(f"Error al validar legajo {legajo}: {str(e)}")
            return {
                "valido": False,
                "mensaje": "Error interno al validar legajo"
            }
    
    def existe(self, legajo):
        """
        Verifica si un legajo existe (método auxiliar)
        
        Args:
            legajo (str): Legajo a verificar
            
        Returns:
            bool: True si existe, False en caso contrario
        """
        return str(legajo).strip() in self.base_empleados
    
    def obtener_empleado(self, legajo):
        """
        Obtiene los datos de un empleado por legajo
        
        Args:
            legajo (str): Legajo del empleado
            
        Returns:
            dict or None: Datos del empleado o None si no existe
        """
        legajo_str = str(legajo).strip()
        return self.base_empleados.get(legajo_str, None)