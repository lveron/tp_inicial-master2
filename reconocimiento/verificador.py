# reconocimiento/verificador.py
import cv2
import numpy as np
import face_recognition
import json
import os
import logging

logger = logging.getLogger(__name__)

class VerificadorFacial:
    def __init__(self, ruta_embeddings="data/embeddings.json", umbral_distancia=0.6):
        """
        Inicializa el verificador facial
        
        Args:
            ruta_embeddings (str): Ruta del archivo de embeddings
            umbral_distancia (float): Umbral para considerar una coincidencia
        """
        self.ruta_embeddings = ruta_embeddings
        self.umbral_distancia = umbral_distancia
        self.base_empleados = self._cargar_embeddings()
        
        logger.info(f"VerificadorFacial inicializado con {len(self.base_empleados)} empleados")
        logger.info(f"Umbral de distancia: {umbral_distancia}")
    
    def _cargar_embeddings(self):
        """Carga los embeddings desde el archivo"""
        if not os.path.exists(self.ruta_embeddings):
            logger.warning(f"Archivo de embeddings no encontrado: {self.ruta_embeddings}")
            return {}
        
        try:
            with open(self.ruta_embeddings, "r") as f:
                data = json.load(f)
                logger.info(f"Embeddings cargados: {len(data)} empleados")
                return data
        except json.JSONDecodeError:
            logger.error("Error al decodificar JSON de embeddings")
            return {}
        except Exception as e:
            logger.error(f"Error al cargar embeddings: {e}")
            return {}
    
    def recargar_embeddings(self):
        """Recarga los embeddings desde el archivo"""
        self.base_empleados = self._cargar_embeddings()
        logger.info("Embeddings recargados")
    
    def detectar_cara(self, imagen):
        """
        Detecta y extrae caras de una imagen
        
        Args:
            imagen: Imagen en formato OpenCV (BGR)
            
        Returns:
            tuple: (caras_detectadas, locations)
        """
        try:
            # Convertir de BGR a RGB para face_recognition
            rgb_imagen = cv2.cvtColor(imagen, cv2.COLOR_BGR2RGB)
            
            # Detectar ubicaciones de caras
            face_locations = face_recognition.face_locations(rgb_imagen)
            
            if not face_locations:
                logger.warning("No se detectaron caras en la imagen")
                return [], []
            
            logger.info(f"Detectadas {len(face_locations)} cara(s)")
            
            # Generar encodings para las caras detectadas
            face_encodings = face_recognition.face_encodings(rgb_imagen, face_locations)
            
            return face_encodings, face_locations
            
        except Exception as e:
            logger.error(f"Error al detectar cara: {e}")
            return [], []
    
    def comparar_con_empleado(self, encoding_imagen, legajo):
        """
        Compara un encoding de imagen con el embedding de un empleado específico
        
        Args:
            encoding_imagen: Encoding facial de la imagen
            legajo (str): Legajo del empleado a comparar
            
        Returns:
            dict: Resultado de la comparación
        """
        try:
            legajo_str = str(legajo)
            
            if legajo_str not in self.base_empleados:
                return {
                    "coincide": False,
                    "distancia": float('inf'),
                    "mensaje": f"Empleado {legajo_str} no encontrado en la base de datos"
                }
            
            empleado_data = self.base_empleados[legajo_str]
            
            if "embedding" not in empleado_data:
                return {
                    "coincide": False,
                    "distancia": float('inf'),
                    "mensaje": f"Empleado {legajo_str} no tiene embedding registrado"
                }
            
            # Obtener embedding del empleado
            embedding_empleado = np.array(empleado_data["embedding"])
            
            # Calcular distancia
            distancia = np.linalg.norm(encoding_imagen - embedding_empleado)
            
            logger.info(f"Distancia calculada para {legajo_str}: {distancia:.4f}")
            
            coincide = distancia <= self.umbral_distancia
            
            return {
                "coincide": coincide,
                "distancia": float(distancia),
                "mensaje": f"{'Coincidencia' if coincide else 'No coincidencia'} para empleado {legajo_str}",
                "empleado": {
                    "legajo": legajo_str,
                    "area": empleado_data.get("area", ""),
                    "rol": empleado_data.get("rol", ""),
                    "turno": empleado_data.get("turno", "")
                }
            }
            
        except Exception as e:
            logger.error(f"Error al comparar con empleado {legajo}: {e}")
            return {
                "coincide": False,
                "distancia": float('inf'),
                "mensaje": f"Error al procesar comparación: {str(e)}"
            }
    
    def verificar_imagen(self, imagen, legajo):
        """
        Verifica si una imagen corresponde a un empleado específico
        
        Args:
            imagen: Imagen en formato OpenCV
            legajo (str): Legajo del empleado a verificar
            
        Returns:
            dict: Resultado de la verificación
        """
        try:
            # Detectar caras en la imagen
            encodings, locations = self.detectar_cara(imagen)
            
            if not encodings:
                return {
                    "coincide": False,
                    "mensaje": "No se detectó ninguna cara en la imagen",
                    "caras_detectadas": 0
                }
            
            if len(encodings) > 1:
                logger.warning(f"Se detectaron {len(encodings)} caras, usando la primera")
            
            # Usar la primera cara detectada
            encoding_principal = encodings[0]
            
            # Comparar con el empleado específico
            resultado = self.comparar_con_empleado(encoding_principal, legajo)
            resultado["caras_detectadas"] = len(encodings)
            resultado["ubicacion_cara"] = locations[0] if locations else None
            
            return resultado
            
        except Exception as e:
            logger.error(f"Error en verificación de imagen: {e}")
            return {
                "coincide": False,
                "mensaje": f"Error al procesar imagen: {str(e)}",
                "caras_detectadas": 0
            }
    
    def buscar_empleado_similar(self, imagen, umbral_personalizado=None):
        """
        Busca qué empleado es más similar a la imagen proporcionada
        
        Args:
            imagen: Imagen en formato OpenCV
            umbral_personalizado (float, optional): Umbral personalizado para la búsqueda
            
        Returns:
            dict: Resultado de la búsqueda
        """
        try:
            umbral = umbral_personalizado or self.umbral_distancia
            
            encodings, locations = self.detectar_cara(imagen)
            
            if not encodings:
                return {
                    "encontrado": False,
                    "mensaje": "No se detectó ninguna cara en la imagen"
                }
            
            encoding_principal = encodings[0]
            
            mejor_coincidencia = None
            menor_distancia = float('inf')
            
            for legajo, empleado_data in self.base_empleados.items():
                if "embedding" not in empleado_data:
                    continue
                
                embedding_empleado = np.array(empleado_data["embedding"])
                distancia = np.linalg.norm(encoding_principal - embedding_empleado)
                
                if distancia < menor_distancia:
                    menor_distancia = distancia
                    mejor_coincidencia = {
                        "legajo": legajo,
                        "distancia": distancia,
                        "empleado": empleado_data
                    }
            
            if mejor_coincidencia and menor_distancia <= umbral:
                return {
                    "encontrado": True,
                    "legajo": mejor_coincidencia["legajo"],
                    "distancia": float(menor_distancia),
                    "empleado": {
                        "legajo": mejor_coincidencia["legajo"],
                        "area": mejor_coincidencia["empleado"].get("area", ""),
                        "rol": mejor_coincidencia["empleado"].get("rol", ""),
                        "turno": mejor_coincidencia["empleado"].get("turno", "")
                    },
                    "mensaje": f"Empleado encontrado: {mejor_coincidencia['legajo']}"
                }
            else:
                return {
                    "encontrado": False,
                    "distancia_minima": float(menor_distancia) if mejor_coincidencia else None,
                    "mensaje": "Ningún empleado coincide con la imagen"
                }
                
        except Exception as e:
            logger.error(f"Error en búsqueda de empleado similar: {e}")
            return {
                "encontrado": False,
                "mensaje": f"Error al procesar búsqueda: {str(e)}"
            }

# Instancia global del verificador
_verificador = None

def obtener_verificador():
    """Obtiene la instancia global del verificador"""
    global _verificador
    if _verificador is None:
        _verificador = VerificadorFacial()
    return _verificador

def reconocer_empleado(imagen, legajo):
    """
    Función de conveniencia para reconocimiento de empleado
    
    Args:
        imagen: Imagen en formato OpenCV
        legajo (str): Legajo del empleado
        
    Returns:
        dict: Resultado del reconocimiento
    """
    verificador = obtener_verificador()
    return verificador.verificar_imagen(imagen, legajo)

def buscar_empleado(imagen):
    """
    Función de conveniencia para búsqueda de empleado
    
    Args:
        imagen: Imagen en formato OpenCV
        
    Returns:
        dict: Resultado de la búsqueda
    """
    verificador = obtener_verificador()
    return verificador.buscar_empleado_similar(imagen)

def recargar_base_empleados():
    """Recarga la base de empleados"""
    verificador = obtener_verificador()
    verificador.recargar_embeddings()

# ===================================================================

# reconocimiento/__init__.py
# Archivo vacío