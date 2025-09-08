# generarEmbedding.py - Versión sin sklearn para evitar errores de importación
import cv2
import numpy as np
from PIL import Image
import io

# Inicializar detector de caras de OpenCV
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def extraer_caracteristicas_cara(imagen_gris, x, y, w, h):
    """
    Extrae características básicas de una cara detectada
    """
    # Recortar la cara
    cara = imagen_gris[y:y+h, x:x+w]
    
    # Redimensionar a tamaño fijo
    cara_resize = cv2.resize(cara, (100, 100))
    
    # Calcular histograma como característica base
    hist = cv2.calcHist([cara_resize], [0], None, [256], [0, 256])
    
    # Calcular gradientes (bordes)
    grad_x = cv2.Sobel(cara_resize, cv2.CV_64F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(cara_resize, cv2.CV_64F, 0, 1, ksize=3)
    
    # Características estadísticas
    caracteristicas = []
    
    # Del histograma (normalizado)
    caracteristicas.extend(hist.flatten() / np.sum(hist))
    
    # De los gradientes
    caracteristicas.extend([
        np.mean(grad_x), np.std(grad_x),
        np.mean(grad_y), np.std(grad_y),
        np.mean(np.abs(grad_x)), np.mean(np.abs(grad_y))
    ])
    
    # Estadísticas básicas de la imagen
    caracteristicas.extend([
        np.mean(cara_resize), np.std(cara_resize),
        np.min(cara_resize), np.max(cara_resize)
    ])
    
    return np.array(caracteristicas)

def generarEmbedding(imagen_file):
    """
    Genera embedding facial usando OpenCV y análisis estadístico
    """
    try:
        # Leer imagen
        imagen_bytes = imagen_file.read()
        imagen = Image.open(io.BytesIO(imagen_bytes))
        
        # Convertir a numpy array y escala de grises
        imagen_rgb = np.array(imagen.convert('RGB'))
        imagen_gris = cv2.cvtColor(imagen_rgb, cv2.COLOR_RGB2GRAY)
        
        # Detectar caras con parámetros menos estrictos
        caras = face_cascade.detectMultiScale(
            imagen_gris, 
            scaleFactor=1.05,  # Más sensible (era 1.1)
            minNeighbors=3,    # Menos estricto (era 5)  
            minSize=(20, 20)   # Caras más pequeñas (era 30, 30)
        )
        
        if len(caras) == 0:
            print("No se detectó ninguna cara en la imagen")
            return None
            
        # Tomar la cara más grande
        cara_principal = max(caras, key=lambda c: c[2] * c[3])
        x, y, w, h = cara_principal
        
        # Extraer características
        caracteristicas = extraer_caracteristicas_cara(imagen_gris, x, y, w, h)
        
        # Reducir dimensionalidad a 128 usando selección manual
        if len(caracteristicas) > 128:
            # Tomar las características más significativas
            indices = np.argsort(np.abs(caracteristicas))[-128:]
            embedding = caracteristicas[indices]
        else:
            # Pad con ceros si es necesario
            embedding = np.pad(caracteristicas, (0, max(0, 128 - len(caracteristicas))))
        
        # Normalizar
        embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
        
        return embedding.tolist()
        
    except Exception as e:
        print(f"Error generando embedding: {e}")
        import traceback
        traceback.print_exc()
        return None

def calcular_distancia_euclidiana(embedding1, embedding2):
    """
    Calcula distancia euclidiana entre dos embeddings
    """
    try:
        emb1 = np.array(embedding1)
        emb2 = np.array(embedding2)
        
        distancia = np.linalg.norm(emb1 - emb2)
        return distancia
        
    except Exception as e:
        print(f"Error calculando distancia: {e}")
        return 1.0

def reconocer_empleado(imagen_file, empleados_embeddings, umbral=0.6):
    """
    Reconoce empleado comparando con embeddings guardados
    """
    try:
        # Generar embedding de la imagen nueva
        nuevo_embedding = generarEmbedding(imagen_file)
        if nuevo_embedding is None:
            return None, 1.0
            
        mejor_match = None
        menor_distancia = float('inf')
        
        # Comparar con todos los empleados
        for legajo, embedding_guardado in empleados_embeddings.items():
            distancia = calcular_distancia_euclidiana(nuevo_embedding, embedding_guardado)
            
            if distancia < menor_distancia:
                menor_distancia = distancia
                mejor_match = legajo
                
        # Verificar si está dentro del umbral
        if menor_distancia <= umbral:
            return mejor_match, menor_distancia
        else:
            return None, menor_distancia
            
    except Exception as e:
        print(f"Error en reconocimiento: {e}")
        import traceback
        traceback.print_exc()
        return None, 1.0
