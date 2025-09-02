import face_recognition
import json
import os
import numpy as np
import logging

logger = logging.getLogger(__name__)

RUTA_EMBEDDINGS = "data/embeddings.json"
UMBRAL_SIMILITUD = 0.6  # Ajustable según tu tolerancia

def generar_embedding(ruta_imagen):
    """
    Genera el embedding facial desde una imagen y verifica si ya existe uno similar.
    
    Args:
        ruta_imagen (str): Ruta del archivo de imagen
        
    Returns:
        list: Lista con el embedding facial
        
    Raises:
        RuntimeError: Si no se detecta cara o si ya existe un embedding similar
        FileNotFoundError: Si no existe el archivo de imagen
    """
    if not os.path.exists(ruta_imagen):
        raise FileNotFoundError(f"No se encontró el archivo de imagen: {ruta_imagen}")
    
    try:
        # Cargar y procesar imagen
        image = face_recognition.load_image_file(ruta_imagen)
        encodings = face_recognition.face_encodings(image)

        if not encodings:
            raise RuntimeError("No se detectó ninguna cara en la imagen. Asegúrate de que la imagen contenga una cara visible.")

        nuevo_embedding = encodings[0]
        logger.info(f"Embedding generado exitosamente con {len(nuevo_embedding)} dimensiones")

        # Cargar base existente
        base = cargar_base_existente()

        # Comparar con embeddings existentes para evitar duplicados
        verificar_similitud(nuevo_embedding, base)

        return nuevo_embedding.tolist()
        
    except Exception as e:
        logger.error(f"Error al generar embedding: {str(e)}")
        raise

def cargar_base_existente():
    """Carga la base de embeddings existente"""
    if os.path.exists(RUTA_EMBEDDINGS):
        try:
            with open(RUTA_EMBEDDINGS, "r") as f:
                base = json.load(f)
                logger.info(f"Base cargada con {len(base)} empleados existentes")
                return base
        except json.JSONDecodeError:
            logger.warning("Archivo JSON corrupto, iniciando base vacía")
            return {}
        except Exception as e:
            logger.error(f"Error al cargar base: {e}")
            return {}
    else:
        logger.info("No existe base previa, iniciando vacía")
        return {}

def verificar_similitud(nuevo_embedding, base):
    """
    Verifica si el nuevo embedding es similar a alguno existente
    
    Args:
        nuevo_embedding: Nuevo embedding a verificar
        base: Base de datos de embeddings existentes
        
    Raises:
        RuntimeError: Si encuentra un embedding similar
    """
    for legajo, datos in base.items():
        if "embedding" not in datos:
            continue
            
        try:
            existente = np.array(datos["embedding"])
            
            # Calcular distancia euclidiana
            distancia = np.linalg.norm(nuevo_embedding - existente)
            
            logger.debug(f"Distancia con empleado {legajo}: {distancia:.4f}")
            
            if distancia < UMBRAL_SIMILITUD:
                raise RuntimeError(
                    f"Ya existe un empleado con embedding similar (legajo: {legajo}, "
                    f"distancia: {distancia:.4f}). El umbral es {UMBRAL_SIMILITUD}"
                )
                
        except Exception as e:
            logger.warning(f"Error al comparar con empleado {legajo}: {e}")
            continue

def validar_embedding(embedding):
    """
    Valida que el embedding tenga el formato correcto
    
    Args:
        embedding: Embedding a validar
        
    Returns:
        bool: True si es válido, False en caso contrario
    """
    if not isinstance(embedding, (list, np.ndarray)):
        return False
        
    if isinstance(embedding, list):
        embedding = np.array(embedding)
        
    # Los embeddings de face_recognition tienen 128 dimensiones
    if embedding.shape[0] != 128:
        return False
        
    # Verificar que sean números válidos
    if not np.all(np.isfinite(embedding)):
        return False
        
    return True

def obtener_info_embedding(embedding):
    """
    Obtiene información estadística del embedding
    
    Args:
        embedding: Embedding a analizar
        
    Returns:
        dict: Información estadística
    """
    if isinstance(embedding, list):
        embedding = np.array(embedding)
        
    return {
        "dimensiones": len(embedding),
        "media": float(np.mean(embedding)),
        "std": float(np.std(embedding)),
        "min": float(np.min(embedding)),
        "max": float(np.max(embedding)),
        "valido": validar_embedding(embedding)
    }