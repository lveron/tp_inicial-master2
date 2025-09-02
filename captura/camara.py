import cv2

class CapturadorFrame:
    def __init__(self, timeout=5):
        self.timeout = timeout
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

    def capturar(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return {"exito": False, "mensaje": "No se pudo abrir la cámara", "frame": None}

        frame_detectado = None
        start_time = cv2.getTickCount() / cv2.getTickFrequency()

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)

            if len(faces) > 0:
                frame_detectado = frame
                break

            elapsed = (cv2.getTickCount() / cv2.getTickFrequency()) - start_time
            if elapsed > self.timeout:
                break

        cap.release()
        cv2.destroyAllWindows()

        if frame_detectado is not None:
            return {"exito": True, "mensaje": "Cara detectada", "frame": frame_detectado}
        else:
            return {"exito": False, "mensaje": "No se detectó ninguna cara", "frame": None}
