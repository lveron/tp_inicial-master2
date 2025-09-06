# app.py
import os
import json
import logging
from datetime import datetime, date
import cv2
import numpy as np

from flask import Flask, request, jsonify
from flask_cors import CORS

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear directorios necesarios
os.makedirs("data", exist_ok=True)
os.makedirs("temp", exist_ok=True)
os.makedirs("persistencia", exist_ok=True)
os.makedirs("reconocimiento", exist_ok=True)
os.makedirs("validarEmpleado", exist_ok=True)
os.makedirs("models", exist_ok=True)

# Import PostgreSQL DatabaseManager
try:
    from persistencia.databaseManager import db_manager
    DATABASE_MANAGER_DISPONIBLE = True
    logger.info("DatabaseManager cargado correctamente")
except ImportError as e:
    logger.warning(f"No se pudo importar DatabaseManager: {e}")
    DATABASE_MANAGER_DISPONIBLE = False

# Importaciones condicionales para evitar crashes
try:
    from generarEmbedinng import generar_embedding
    EMBEDDING_DISPONIBLE = True
except ImportError as e:
    logger.warning(f"No se pudo importar generarEmbedding: {e}")
    EMBEDDING_DISPONIBLE = False

try:
    from persistencia.registrarAsistencia import RegistrarAsistencias
    ASISTENCIA_DISPONIBLE = True
except ImportError as e:
    logger.warning(f"No se pudo importar RegistrarAsistencias: {e}")
    ASISTENCIA_DISPONIBLE = False

try:
    from reconocimiento.verificador import reconocer_empleado
    RECONOCIMIENTO_DISPONIBLE = True
except ImportError as e:
    logger.warning(f"No se pudo importar reconocer_empleado: {e}")
    RECONOCIMIENTO_DISPONIBLE = False

try:
    from validarEmpleado.validarLegajo import ValidadorLegajo
    from validarEmpleado.validarTurno import ValidadorTurno
    VALIDADOR_DISPONIBLE = True
except ImportError as e:
    logger.warning(f"No se pudo importar validadores: {e}")
    VALIDADOR_DISPONIBLE = False

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/')
def home():
    return jsonify({
        "mensaje": "Backend activo",
        "status": "OK",
        "servicios": {
            "embedding": EMBEDDING_DISPONIBLE,
            "asistencia": ASISTENCIA_DISPONIBLE,
            "reconocimiento": RECONOCIMIENTO_DISPONIBLE,
            "validador": VALIDADOR_DISPONIBLE,
            "database_manager": DATABASE_MANAGER_DISPONIBLE
        }
    })

def cargar_base_empleados():
    """Carga la base de empleados usando DatabaseManager o fallback a JSON"""
    if DATABASE_MANAGER_DISPONIBLE:
        return db_manager.cargar_empleados()
    else:
        # Fallback al sistema JSON tradicional
        ruta = os.path.normpath("data/embeddings.json")
        if not os.path.exists(ruta):
            logger.info("Archivo embeddings.json no existe, creando base vacía")
            with open(ruta, "w") as f:
                json.dump({}, f)
            return {}
        
        try:
            with open(ruta, "r") as f:
                data = json.load(f)
                logger.info(f"Base de empleados cargada desde JSON: {len(data)} empleados")
                return data
        except json.JSONDecodeError:
            logger.error("Error al decodificar JSON, iniciando base vacía")
            return {}
        except Exception as e:
            logger.error(f"Error al cargar base de empleados: {e}")
            return {}

# Inicializar componentes si están disponibles
base = cargar_base_empleados()

if VALIDADOR_DISPONIBLE:
    val_legajo = ValidadorLegajo(base)
    val_turno = ValidadorTurno(base)

if ASISTENCIA_DISPONIBLE:
    asistencia = RegistrarAsistencias()

@app.route("/validar", methods=["POST"])
def validar():
    """Endpoint para validar legajo y turno"""
    try:
        if not VALIDADOR_DISPONIBLE:
            return jsonify({"valido": False, "mensaje": "Servicio de validación no disponible"}), 503
        
        data = request.get_json()
        if not data:
            return jsonify({"valido": False, "mensaje": "No se enviaron datos"}), 400
            
        legajo = data.get("legajo")
        turno = data.get("turno")

        if not legajo or not turno:
            return jsonify({"valido": False, "mensaje": "Faltan datos: legajo y turno son requeridos"}), 400

        # Recargar base por si hubo cambios
        base = cargar_base_empleados()
        val_legajo = ValidadorLegajo(base)
        val_turno = ValidadorTurno(base)

        r1 = val_legajo.validar(legajo)
        if not r1["valido"]:
            return jsonify(r1)

        r2 = val_turno.validar(legajo, turno)
        return jsonify(r2)
        
    except Exception as e:
        logger.error(f"Error en validación: {str(e)}")
        return jsonify({"valido": False, "mensaje": "Error interno del servidor"}), 500

@app.route("/reconocer", methods=["POST"])
def reconocer():
    """Endpoint para reconocimiento facial"""
    try:
        if not RECONOCIMIENTO_DISPONIBLE or not ASISTENCIA_DISPONIBLE:
            return jsonify({"exito": False, "mensaje": "Servicio de reconocimiento no disponible"}), 503
            
        legajo = request.form.get("legajo")
        turno = request.form.get("turno")
        imagen_file = request.files.get("imagen")

        if not legajo or not turno:
            return jsonify({"exito": False, "mensaje": "Faltan datos: legajo y turno son requeridos"}), 400

        if not imagen_file:
            logger.warning("No se recibió imagen en el request")
            return jsonify({"exito": False, "mensaje": "No se recibió imagen"}), 400

        try:
            npimg = np.frombuffer(imagen_file.read(), np.uint8)
            frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
            
            if frame is None:
                raise ValueError("No se pudo decodificar la imagen")
                
        except Exception as e:
            logger.error(f"Error al procesar imagen: {e}")
            return jsonify({"exito": False, "mensaje": "Error al procesar imagen"}), 400

        logger.info(f"Imagen recibida correctamente para legajo: {legajo}")

        resultado = reconocer_empleado(frame, legajo)
        if not resultado.get("coincide", False):
            return jsonify({"exito": False, "mensaje": "Empleado no reconocido"})

        # Usar DatabaseManager para registrar asistencia si está disponible
        if DATABASE_MANAGER_DISPONIBLE:
            tipo = "entrada"  # Por simplicidad, siempre entrada por ahora
            resultado_asistencia = db_manager.registrar_asistencia(legajo, turno, tipo)
            return jsonify(resultado_asistencia)
        else:
            # Usar sistema tradicional
            tipo = asistencia.obtener_ultimo_tipo(legajo)
            if not asistencia.puede_registrar_hoy(legajo, tipo):
                return jsonify({"exito": False, "mensaje": f"Ya se registró un {tipo.lower()} hoy"})

            estado = asistencia.calcular_puntualidad(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), tipo, turno)
            if estado == "fuera de turno":
                return jsonify({"exito": False, "mensaje": "Fuera de turno"})

            asistencia.registrar(legajo, turno, tipo)
            return jsonify({"exito": True, "mensaje": f"{tipo} registrado correctamente"})
        
    except Exception as e:
        logger.error(f"Error en reconocimiento: {str(e)}")
        return jsonify({"exito": False, "mensaje": "Error interno del servidor"}), 500

@app.route("/registrar_empleado", methods=["POST"])
def registrar_empleado():
    """Endpoint para registrar nuevo empleado"""
    try:
        if not EMBEDDING_DISPONIBLE:
            return jsonify({"exito": False, "mensaje": "Servicio de embedding no disponible"}), 503
            
        imagen_file = request.files.get("imagen")
        legajo = request.form.get("legajo", "").strip()
        area = request.form.get("area", "").strip()
        rol = request.form.get("rol", "").strip()
        turno = request.form.get("turno", "").strip()

        if not imagen_file or not legajo or not area or not rol or not turno:
            return jsonify({"exito": False, "mensaje": "Faltan datos: imagen, legajo, area, rol y turno son requeridos"}), 400

        # Guardar imagen temporal
        ruta_temp = f"temp/{legajo}.jpg"
        imagen_file.save(ruta_temp)

        try:
            embedding = generar_embedding(ruta_temp)
        except Exception as e:
            logger.error(f"Error al procesar imagen: {e}")
            return jsonify({"exito": False, "mensaje": f"Error al procesar imagen: {str(e)}"}), 500
        finally:
            # Limpiar archivo temporal
            if os.path.exists(ruta_temp):
                os.remove(ruta_temp)

        if not isinstance(embedding, list) or len(embedding) < 128:
            return jsonify({"exito": False, "mensaje": "Embedding inválido"}), 400

        # Usar DatabaseManager si está disponible
        if DATABASE_MANAGER_DISPONIBLE:
            resultado = db_manager.guardar_empleado(legajo, area, rol, turno, embedding)
            if not resultado["exito"]:
                return jsonify(resultado), 400
            return jsonify(resultado)
        else:
            # Fallback al sistema JSON tradicional
            base = cargar_base_empleados()
            if legajo in base:
                return jsonify({"exito": False, "mensaje": "Legajo ya registrado"}), 400

            base[legajo] = {
                "area": area,
                "rol": rol,
                "turno": turno,
                "embedding": embedding
            }

            ruta_embeddings = "data/embeddings.json"
            with open(ruta_embeddings, "w") as f:
                json.dump(base, f, indent=4)

            logger.info(f"Empleado {legajo} registrado correctamente en JSON")
            return jsonify({"exito": True, "mensaje": "Empleado registrado correctamente"})
        
    except Exception as e:
        logger.error(f"Error en registro de empleado: {str(e)}")
        return jsonify({"exito": False, "mensaje": "Error interno del servidor"}), 500

@app.route("/ping", methods=["GET"])
def ping():
    """Endpoint de health check"""
    logger.info("Recibí un ping desde el cliente")
    return jsonify({
        "mensaje": "Conexión OK",
        "timestamp": datetime.now().isoformat(),
        "status": "healthy",
        "database_available": DATABASE_MANAGER_DISPONIBLE
    })

@app.route("/empleados", methods=["GET"])
def listar_empleados():
    """Endpoint para listar empleados registrados"""
    try:
        base = cargar_base_empleados()
        empleados = []
        
        for legajo, datos in base.items():
            empleados.append({
                "legajo": legajo,
                "area": datos.get("area", ""),
                "rol": datos.get("rol", ""),
                "turno": datos.get("turno", ""),
                "tiene_embedding": "embedding" in datos
            })
            
        return jsonify({
            "exito": True,
            "empleados": empleados,
            "total": len(empleados),
            "using_database": DATABASE_MANAGER_DISPONIBLE
        })
        
    except Exception as e:
        logger.error(f"Error al listar empleados: {str(e)}")
        return jsonify({"exito": False, "mensaje": "Error interno del servidor"}), 500

@app.route("/dashboard", methods=["GET"])
def dashboard_data():
    """Endpoint que devuelve datos para el dashboard"""
    try:
        if DATABASE_MANAGER_DISPONIBLE:
            # Obtener datos desde PostgreSQL
            from models.database import get_db_session, Empleado, Asistencia
            session = get_db_session()
            if session:
                try:
                    # Contar empleados totales
                    total_empleados = session.query(Empleado).count()
                    
                    # Contar asistencias de hoy
                    hoy = date.today().strftime("%Y-%m-%d")
                    asistencias_hoy = session.query(Asistencia).filter(
                        Asistencia.fecha == hoy
                    ).count()
                    
                    # Empleados por turno
                    empleados_manana = session.query(Empleado).filter(
                        Empleado.turno == "mañana"
                    ).count()
                    empleados_tarde = session.query(Empleado).filter(
                        Empleado.turno == "tarde"
                    ).count()
                    empleados_noche = session.query(Empleado).filter(
                        Empleado.turno == "noche"
                    ).count()
                    
                    # Obtener asistencias de los últimos 7 días
                    from datetime import datetime, timedelta
                    hace_7_dias = datetime.now() - timedelta(days=7)
                    
                    asistencias_semana = []
                    for i in range(7):
                        fecha_consulta = (hace_7_dias + timedelta(days=i)).strftime("%Y-%m-%d")
                        count = session.query(Asistencia).filter(
                            Asistencia.fecha == fecha_consulta
                        ).count()
                        asistencias_semana.append({
                            "fecha": fecha_consulta,
                            "count": count
                        })
                    
                    session.close()
                    
                    return jsonify({
                        "exito": True,
                        "totalEmpleados": total_empleados,
                        "asistenciasHoy": asistencias_hoy,
                        "empleadosPorTurno": {
                            "mañana": empleados_manana,
                            "tarde": empleados_tarde,
                            "noche": empleados_noche
                        },
                        "asistenciasSemana": asistencias_semana,
                        "fuente": "PostgreSQL"
                    })
                    
                except Exception as e:
                    logger.error(f"Error consultando PostgreSQL: {e}")
                    session.close()
                    
        # Si no hay PostgreSQL, usar datos simulados basados en JSON
        base = cargar_base_empleados()
        total_empleados = len(base)
        
        # Contar por turnos desde JSON
        turnos = {"mañana": 0, "tarde": 0, "noche": 0}
        for empleado_data in base.values():
            turno = empleado_data.get("turno", "").lower()
            if turno in turnos:
                turnos[turno] += 1
        
        # Datos simulados para la semana
        asistencias_semana = []
        from datetime import datetime, timedelta
        for i in range(7):
            fecha = (datetime.now() - timedelta(days=6-i)).strftime("%Y-%m-%d")
            # Simular datos basados en número de empleados
            count = max(1, total_empleados // 2 + (i % 3))
            asistencias_semana.append({
                "fecha": fecha,
                "count": count
            })
        
        return jsonify({
            "exito": True,
            "totalEmpleados": total_empleados,
            "asistenciasHoy": max(1, total_empleados // 2),
            "empleadosPorTurno": turnos,
            "asistenciasSemana": asistencias_semana,
            "fuente": "JSON/Simulado"
        })
        
    except Exception as e:
        logger.error(f"Error en dashboard: {str(e)}")
        return jsonify({
            "exito": False,
            "mensaje": "Error obteniendo datos del dashboard"
        }), 500

@app.route("/asistencias/<legajo>", methods=["GET"])
def obtener_asistencias(legajo):
    """Endpoint para obtener asistencias de un empleado"""
    try:
        if DATABASE_MANAGER_DISPONIBLE:
            # Usar PostgreSQL si está disponible
            # Por ahora retornar placeholder hasta implementar en DatabaseManager
            return jsonify({
                "exito": True,
                "legajo": legajo,
                "asistencias": [],
                "mensaje": "Funcionalidad en desarrollo con PostgreSQL"
            })
        else:
            # Usar sistema JSON tradicional
            if ASISTENCIA_DISPONIBLE:
                registros = asistencia.obtener_asistencias_empleado(legajo)
                return jsonify({
                    "exito": True,
                    "legajo": legajo,
                    "asistencias": registros
                })
            else:
                return jsonify({"exito": False, "mensaje": "Servicio de asistencias no disponible"}), 503
                
    except Exception as e:
        logger.error(f"Error al obtener asistencias: {str(e)}")
        return jsonify({"exito": False, "mensaje": "Error interno del servidor"}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint no encontrado"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Error interno del servidor: {error}")
    return jsonify({"error": "Error interno del servidor"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    debug = os.environ.get("FLASK_ENV") != "production"
    
    logger.info(f"Iniciando aplicación en puerto {port}")
    logger.info(f"Modo debug: {debug}")
    logger.info(f"DatabaseManager disponible: {DATABASE_MANAGER_DISPONIBLE}")
    
    app.run(host="0.0.0.0", port=port, debug=debug)
