import cv2
import face_recognition
import json
import os

RUTA_EMBEDDINGS = "data/embeddings.json"

RUTA_EMBEDDINGS = "data/embeddings.json"

def cargar_embeddings():
    if os.path.exists(RUTA_EMBEDDINGS):
        with open(RUTA_EMBEDDINGS, "r") as f:
            try:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
                else:
                    print("⚠ El JSON no es un diccionario, iniciando vacío.")
            except json.JSONDecodeError:
                print("⚠ Error de formato JSON, iniciando vacío.")
    return {}

def guardar_embeddings(base):
    with open(RUTA_EMBEDDINGS, "w") as f:
        json.dump(base, f)

def registrar_empleado(nombre):
    cap = cv2.VideoCapture(0)
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )

    print("Mostrate a la cámara y presioná 'q' para capturar...")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 5)

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

        cv2.imshow("Registro de empleado", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            if len(faces) > 0:
                x, y, w, h = faces[0]
                face_img = frame[y:y + h, x:x + w]
                face_img = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)

                encodings = face_recognition.face_encodings(face_img)
                if encodings:
                    embedding = encodings[0].tolist()
                    base = cargar_embeddings()
                    base[nombre] = embedding
                    guardar_embeddings(base)
                    print(f"✅ Embedding de {nombre} guardado correctamente.")
                else:
                    print("❌ No se pudo generar el embedding. Intentá de nuevo.")
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    nombre = input("Ingresá el nombre del empleado: ")
    registrar_empleado(nombre)