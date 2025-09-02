import face_recognition
import json
import numpy as np
import os

class EmbeddingManager:
    def __init__(self, ruta_json="data/embeddings.json"):
        self.ruta = os.path.normpath(ruta_json)

    def generar_embedding(self, face_img):
        encodings = face_recognition.face_encodings(face_img)
        if not encodings:
            raise ValueError("No se pudo generar embedding para la cara recortada")
        return encodings[0].tolist()

    def cargar_embeddings(self):
        if not os.path.exists(self.ruta):
            return {}

        with open(self.ruta, "r") as f:
            contenido = f.read().strip()
            if not contenido:
                return {}

            try:
                return json.loads(contenido)
            except json.JSONDecodeError:
                return {}

    def guardar_embeddings(self, data):
        with open(self.ruta, "w") as f:
            json.dump(data, f, indent=2)

    def comparar_embeddings(self, emb1, emb2, threshold=0.6):
        v1 = np.array(emb1)
        v2 = np.array(emb2)
        distancia = np.linalg.norm(v1 - v2)
        return distancia < threshold
