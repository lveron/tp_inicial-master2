from datetime import datetime

class Asistencia:
    def __init__(self, legajo, tipo, turno, estado, observacion="", timestamp=None):
        self.legajo = str(legajo).strip()
        self.tipo = tipo.strip().lower()  # 'ingreso' o 'egreso'
        self.turno = turno.strip().lower()
        self.estado = estado.strip().lower()  # 'puntual', 'tarde', etc.
        self.observacion = observacion.strip()
        self.timestamp = timestamp or datetime.now()

    def to_dict(self):
        return {
            "legajo": self.legajo,
            "tipo": self.tipo,
            "turno": self.turno,
            "estado": self.estado,
            "observacion": self.observacion,
            "timestamp": self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            legajo=data.get("legajo", ""),
            tipo=data.get("tipo", ""),
            turno=data.get("turno", ""),
            estado=data.get("estado", ""),
            observacion=data.get("observacion", ""),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else None
        )

