class Empleado:
    def __init__(self, legajo, area, rol, turno, embedding=None):
        self.legajo = str(legajo).strip()
        self.area = area.strip()
        self.rol = rol.strip()
        self.turno = turno.strip().lower()
        self.embedding = embedding  # lista de 128 floats o None

    def to_dict(self):
        return {
            "legajo": self.legajo,
            "area": self.area,
            "rol": self.rol,
            "turno": self.turno,
            "embedding": self.embedding
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            legajo=data.get("legajo", ""),
            area=data.get("area", ""),
            rol=data.get("rol", ""),
            turno=data.get("turno", ""),
            embedding=data.get("embedding")
        )

    def tiene_embedding(self):
        return isinstance(self.embedding, list) and len(self.embedding) == 128
