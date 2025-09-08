from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from datetime import datetime

# Imports de los módulos locales
from models.database import init_db
from persistencia.databaseManager import DatabaseManager
from validarEmpleado.validarLegajo import ValidadorLegajo
from validarEmpleado.validarTurno import ValidadorTurno
from persistencia.registrarAsistencia import RegistrarAsistencias

# Intentar cargar módulos de reconocimiento facial
try:
    from generarEmbedding import generarEmbedding, reconocer_empleado
    RECONOCIMIENTO_DISPONIBLE = True
    EMBEDDING_DISPONIBLE = True
    print("INFO: Reconocimiento facial con OpenCV cargado correctamente")
except Exception as e:
    RECONOCIMIENTO_DISPONIBLE = False
    EMBEDDING_DISPONIBLE = False
    print(f"WARNING: Error cargando reconocimiento: {e}")

app = Flask(__name__)
CORS(app)

# Inicializar base de datos
init_db()

# Inicializar managers
database_manager = DatabaseManager()
print("INFO: DatabaseManager cargado correctamente")

# Cargar empleados desde la base de datos
empleados = database_manager.obtener_todos_empleados()

# Inicializar validadores
validador_legajo = ValidadorLegajo(empleados)
validador_turno = ValidadorTurno(empleados)

# Inicializar registro de asistencias
registrar_asistencias = RegistrarAsistencias()

@app.route('/')
def home():
    try:
        # Verificar conectividad con base de datos
        empleados_count = database_manager.contar_empleados()
        db_status = True
    except Exception as e:
        print(f"ERROR consultando PostgreSQL: {e}")
        empleados_count = 0
        db_status = False
        
    return jsonify({
        "mensaje": "Backend activo",
        "servicios": {
            "database_manager": db_status,
            "validador": validador_legajo is not None and validador_turno is not None,
            "asistencia": registrar_asistencias is not None,
            "embedding": EMBEDDING_DISPONIBLE,
            "reconocimiento": RECONOCIMIENTO_DISPONIBLE
        },
        "empleados_registrados": empleados_count,
        "modo": "con_reconocimiento" if RECONOCIMIENTO_DISPONIBLE else "sin_reconocimiento",
        "status": "OK"
    })

@app.route('/ping')
def ping():
    print("INFO: Recibí un ping desde el cliente")
    try:
        empleados_count = database_manager.contar_empleados()
        return jsonify({
            "mensaje": "pong",
            "timestamp": datetime.now().isoformat(),
            "empleados": empleados_count,
            "reconocimiento": RECONOCIMIENTO_DISPONIBLE
        })
    except Exception as e:
        print(f"ERROR consultando PostgreSQL: {e}")
        return jsonify({
            "mensaje": "pong",
            "timestamp": datetime.now().isoformat(),
            "empleados": 0,
            "reconocimiento": RECONOCIMIENTO_DISPONIBLE,
            "db_error": str(e)
        })

@app.route('/validar', methods=['POST'])
def validar_empleado():
    try:
        data = request.get_json()
        legajo = data.get('legajo')
        turno = data.get('turno')
        
        if not legajo or not turno:
            return jsonify({"error": "Legajo y turno son requeridos"}), 400
        
        # Validar legajo
        legajo_valido = validador_legajo.validar(legajo)
        if not legajo_valido:
            return jsonify({"error": "Legajo no válido"}), 404
        
        # Validar turno
        turno_valido = validador_turno.validar(legajo, turno)
        if not turno_valido:
            return jsonify({"error": "Turno no válido para este empleado"}), 400
        
        return jsonify({
            "legajo": legajo,
            "turno": turno,
            "valido": True
        })
        
    except Exception as e:
        print(f"ERROR en validar_empleado: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

@app.route('/registrar_empleado', methods=['POST'])
def registrar_empleado():
    try:
        # Obtener datos del formulario
        legajo = request.form.get('legajo')
        area = request.form.get('area') 
        rol = request.form.get('rol')
        turno = request.form.get('turno')
        imagen = request.files.get('imagen')
        
        # Validar campos obligatorios
        if not all([legajo, area, rol, turno]):
            return jsonify({"error": "Faltan campos obligatorios"}), 400
            
        # Verificar si el legajo ya existe
        if database_manager.empleado_existe(legajo):
            return jsonify({"error": "El empleado ya existe"}), 409
            
        if RECONOCIMIENTO_DISPONIBLE and imagen:
            # Generar embedding de la imagen
            embedding = generarEmbedding(imagen)
            if embedding is None:
                return jsonify({"error": "No se pudo procesar la imagen facial"}), 400
        else:
            # Usar embedding dummy si no hay reconocimiento o imagen
            embedding = [0.0] * 128
            
        # Registrar empleado en la base de datos
        resultado = database_manager.registrar_empleado(
            legajo=legajo,
            area=area,
            rol=rol, 
            turno=turno,
            embedding=embedding
        )
        
        if resultado:
            # Actualizar validadores con el nuevo empleado
            empleados_actualizados = database_manager.obtener_todos_empleados()
            global validador_legajo, validador_turno
            validador_legajo = ValidadorLegajo(empleados_actualizados)
            validador_turno = ValidadorTurno(empleados_actualizados)
            
            return jsonify({
                "mensaje": "Empleado registrado exitosamente",
                "legajo": legajo,
                "modo": "con_reconocimiento" if RECONOCIMIENTO_DISPONIBLE and imagen else "sin_reconocimiento"
            }), 201
        else:
            return jsonify({"error": "Error al registrar empleado en la base de datos"}), 500
            
    except Exception as e:
        print(f"ERROR en registrar_empleado: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error interno: {str(e)}"}), 500

@app.route('/reconocer', methods=['POST'])
def reconocer():
    try:
        if not RECONOCIMIENTO_DISPONIBLE:
            return jsonify({"error": "Servicio de reconocimiento no disponible"}), 503
            
        # Obtener datos
        legajo = request.form.get('legajo')
        turno = request.form.get('turno')
        imagen = request.files.get('imagen')
        
        if not all([legajo, turno, imagen]):
            return jsonify({"error": "Legajo, turno e imagen son requeridos"}), 400
        
        # Validar legajo y turno
        if not validador_legajo.validar(legajo):
            return jsonify({"error": "Legajo no válido"}), 404
            
        if not validador_turno.validar(legajo, turno):
            return jsonify({"error": "Turno no válido"}), 400
        
        # Obtener embeddings de todos los empleados
        empleados_embeddings = {}
        empleados = database_manager.obtener_todos_empleados()
        for empleado in empleados:
            empleados_embeddings[empleado['legajo']] = empleado['embedding']
        
        # Reconocer empleado
        empleado_reconocido, distancia = reconocer_empleado(imagen, empleados_embeddings)
        
        if empleado_reconocido == legajo:
            # Registrar asistencia
            resultado = registrar_asistencias.registrar(legajo, turno)
            
            return jsonify({
                "legajo": legajo,
                "reconocido": True,
                "distancia": distancia,
                "asistencia_registrada": resultado,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "legajo": legajo,
                "reconocido": False,
                "distancia": distancia,
                "empleado_detectado": empleado_reconocido
            }), 403
            
    except Exception as e:
        print(f"ERROR en reconocer: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error interno: {str(e)}"}), 500

@app.route('/empleados', methods=['GET'])
def obtener_empleados():
    try:
        empleados = database_manager.obtener_todos_empleados()
        
        # Remover embeddings de la respuesta (son muy largos)
        empleados_sin_embedding = []
        for emp in empleados:
            emp_limpio = {k: v for k, v in emp.items() if k != 'embedding'}
            empleados_sin_embedding.append(emp_limpio)
            
        return jsonify({
            "empleados": empleados_sin_embedding,
            "total": len(empleados_sin_embedding)
        })
        
    except Exception as e:
        print(f"ERROR en obtener_empleados: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

@app.route('/asistencias/<legajo>', methods=['GET'])
def obtener_asistencias(legajo):
    try:
        if not validador_legajo.validar(legajo):
            return jsonify({"error": "Legajo no válido"}), 404
            
        asistencias = registrar_asistencias.obtener_asistencias_empleado(legajo)
        
        return jsonify({
            "legajo": legajo,
            "asistencias": asistencias,
            "total": len(asistencias)
        })
        
    except Exception as e:
        print(f"ERROR en obtener_asistencias: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint no encontrado"}), 404

@app.errorhandler(500)
def internal_error(error):
    print(f"ERROR interno del servidor: {error}")
    return jsonify({"error": "Error interno del servidor"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
