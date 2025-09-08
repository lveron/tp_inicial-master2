# generarEmbedding.py - Nueva versión sin dlib
import cv2
import numpy as np
import mediapipe as mp
from PIL import Image
import io

# Inicializar MediaPipe
mp_face_detection = mp.solutions.face_detection
mp_face_mesh = mp.solutions.face_mesh

def generarEmbedding(imagen_file):
    """
    Genera embedding facial usando MediaPipe (sin dependencias X11)
    """
    try:
        # Leer imagen
        imagen_bytes = imagen_file.read()
        imagen = Image.open(io.BytesIO(imagen_bytes))
        
        # Convertir a RGB numpy array
        imagen_rgb = np.array(imagen.convert('RGB'))
        
        # Detectar caras con MediaPipe
        with mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5) as face_detection:
            results = face_detection.process(imagen_rgb)
            
            if not results.detections:
                print("No se detectó ninguna cara en la imagen")
                return None
                
        # Extraer características faciales con Face Mesh
        with mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5) as face_mesh:
            
            results = face_mesh.process(imagen_rgb)
            
            if not results.multi_face_landmarks:
                print("No se pudieron extraer características faciales")
                return None
                
            # Extraer landmarks de la primera cara
            face_landmarks = results.multi_face_landmarks[0]
            
            # Convertir landmarks a embedding de 128 dimensiones
            landmarks_array = []
            for landmark in face_landmarks.landmark:
                landmarks_array.extend([landmark.x, landmark.y, landmark.z])
            
            # Normalizar y reducir a 128 dimensiones
            landmarks_array = np.array(landmarks_array)
            
            # Usar PCA simple o tomar las primeras 128 características más significativas
            if len(landmarks_array) > 128:
                # Tomar cada n-ésimo elemento para llegar a 128
                step = len(landmarks_array) // 128
                embedding = landmarks_array[::step][:128]
            else:
                # Pad con ceros si es necesario
                embedding = np.pad(landmarks_array, (0, max(0, 128 - len(landmarks_array))))
            
            # Normalizar el embedding
            embedding = embedding / np.linalg.norm(embedding)
            
            return embedding.tolist()
            
    except Exception as e:
        print(f"Error generando embedding: {e}")
        return None


def calcular_distancia_coseno(embedding1, embedding2):
    """
    Calcula distancia coseno entre dos embeddings
    """
    try:
        emb1 = np.array(embedding1)
        emb2 = np.array(embedding2)
        
        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        
        if norm1 == 0 or norm2 == 0:
            return 1.0
            
        similarity = dot_product / (norm1 * norm2)
        distance = 1 - similarity
        
        return distance
        
    except Exception as e:
        print(f"Error calculando distancia: {e}")
        return 1.0


def reconocer_empleado(imagen_file, empleados_embeddings, umbral=0.4):
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
            distancia = calcular_distancia_coseno(nuevo_embedding, embedding_guardado)
            
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
        return None, 1.0
