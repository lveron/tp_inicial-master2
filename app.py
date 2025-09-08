from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from datetime import datetime

# Imports de los módulos locales
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

# Inicializar managers
database_manager = DatabaseManager()
print("INFO: DatabaseManager cargado correctamente")

# Cargar empleados desde la base de datos con manejo de errores mejorado
try:
    empleados = database_manager.obtener_todos_empleados()
    print(f"INFO: Cargados {len(empleados)} empleados desde la base de datos")
except Exception as e:
    print(f"ERROR cargando empleados: {e}")
    empleados = []

# Inicializar validadores
validador_legajo = ValidadorLegajo(empleados)
validador_turno = ValidadorTurno(empleados)

# Inicializar registro de asistencias
registrar_asistencias = RegistrarAsistencias()

def actualizar_validadores():
    """Función auxiliar para actualizar los validadores con empleados frescos"""
    try:
        empleados_actualizados = database_manager.obtener_todos_empleados()
        global validador_legajo, validador_turno
        validador_legajo = ValidadorLegajo(empleados_actualizados)
        validador_turno = ValidadorTurno(empleados_actualizados)
        return True
    except Exception as e:
        print(f"ERROR actualizando validadores: {e}")
        return False

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
        
        if not data:
            return jsonify({"error": "No se recibió datos JSON"}), 400
            
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
        import traceback
        traceback.print_exc()
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
            return jsonify({"error": "Faltan campos obligatorios: legajo, area, rol, turno"}), 400
            
        # Validar turno
        turnos_validos = ['mañana', 'tarde', 'noche']
        if turno not in turnos_validos:
            return jsonify({"error": f"Turno debe ser uno de: {', '.join(turnos_validos)}"}), 400
            
        # Verificar si el legajo ya existe
        if database_manager.empleado_existe(legajo):
            return jsonify({"error": "El empleado ya existe"}), 409
            
        # Procesar imagen y embedding
        if RECONOCIMIENTO_DISPONIBLE and imagen:
            try:
                # Generar embedding de la imagen
                embedding = generarEmbedding(imagen)
                if embedding is None:
                    return jsonify({"error": "No se pudo procesar la imagen facial"}), 400
            except Exception as e:
                print(f"ERROR procesando imagen: {e}")
                return jsonify({"error": "Error procesando la imagen facial"}), 400
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
            actualizar_validadores()
            
            return jsonify({
                "mensaje": "Empleado registrado exitosamente",
                "legajo": legajo,
                "area": area,
                "rol": rol,
                "turno": turno,
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
        
        if not empleados:
            return jsonify({"error": "No hay empleados registrados para comparar"}), 500
            
        for empleado in empleados:
            if empleado.get('embedding'):
                empleados_embeddings[empleado['legajo']] = empleado['embedding']
        
        if not empleados_embeddings:
            return jsonify({"error": "No hay embeddings disponibles para reconocimiento"}), 500
        
        # Reconocer empleado
        try:
            empleado_reconocido, distancia = reconocer_empleado(imagen, empleados_embeddings)
        except Exception as e:
            print(f"ERROR en reconocimiento facial: {e}")
            return jsonify({"error": "Error en el proceso de reconocimiento facial"}), 500
        
        if empleado_reconocido == legajo:
            # Registrar asistencia
            resultado = registrar_asistencias.registrar(legajo, turno)
            
            return jsonify({
                "legajo": legajo,
                "reconocido": True,
                "distancia": float(distancia) if distancia is not None else None,
                "asistencia_registrada": resultado,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "legajo": legajo,
                "reconocido": False,
                "distancia": float(distancia) if distancia is not None else None,
                "empleado_detectado": empleado_reconocido,
                "mensaje": "La persona no coincide con el legajo proporcionado"
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
            # Formatear fecha si existe
            if emp_limpio.get('fecha_registro'):
                emp_limpio['fecha_registro'] = emp_limpio['fecha_registro'].isoformat()
            empleados_sin_embedding.append(emp_limpio)
            
        return jsonify({
            "empleados": empleados_sin_embedding,
            "total": len(empleados_sin_embedding)
        })
        
    except Exception as e:
        print(f"ERROR en obtener_empleados: {e}")
        import traceback
        traceback.print_exc()
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
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Error interno del servidor"}), 500

@app.route('/asistencias', methods=['GET'])
def obtener_todas_asistencias():
    """Endpoint para obtener todas las asistencias con filtros opcionales"""
    try:
        fecha = request.args.get('fecha')  # Formato: YYYY-MM-DD
        
        if fecha:
            try:
                from datetime import datetime
                fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
                asistencias = registrar_asistencias.obtener_asistencias_fecha(fecha_obj)
            except ValueError:
                return jsonify({"error": "Formato de fecha inválido. Use YYYY-MM-DD"}), 400
        else:
            # Si no se especifica fecha, obtener todas (esto podría ser mucho)
            # Por seguridad, limitar a empleados existentes
            empleados = database_manager.obtener_todos_empleados()
            asistencias = []
            for empleado in empleados[:10]:  # Limitar a 10 empleados
                asist_emp = registrar_asistencias.obtener_asistencias_empleado(empleado['legajo'])
                asistencias.extend(asist_emp)
        
        return jsonify({
            "asistencias": asistencias,
            "total": len(asistencias),
            "fecha": fecha if fecha else "todas"
        })
        
    except Exception as e:
        print(f"ERROR en obtener_todas_asistencias: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Error interno del servidor"}), 500

@app.route('/empleado/<legajo>', methods=['GET'])
def obtener_empleado(legajo):
    """Obtener información de un empleado específico"""
    try:
        empleado = database_manager.obtener_empleado(legajo)
        
        if not empleado:
            return jsonify({"error": "Empleado no encontrado"}), 404
        
        # Remover embedding de la respuesta
        empleado_sin_embedding = {k: v for k, v in empleado.items() if k != 'embedding'}
        if empleado_sin_embedding.get('fecha_registro'):
            empleado_sin_embedding['fecha_registro'] = empleado_sin_embedding['fecha_registro'].isoformat()
        
        return jsonify({
            "empleado": empleado_sin_embedding
        })
        
    except Exception as e:
        print(f"ERROR en obtener_empleado: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Error interno del servidor"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check más detallado"""
    try:
        # Verificar base de datos
        try:
            empleados_count = database_manager.contar_empleados()
            db_health = "healthy"
        except Exception as e:
            empleados_count = 0
            db_health = f"error: {str(e)}"
        
        # Verificar servicios
        services_status = {
            "database": db_health,
            "validadores": "healthy" if validador_legajo and validador_turno else "error",
            "asistencias": "healthy" if registrar_asistencias else "error",
            "reconocimiento": "available" if RECONOCIMIENTO_DISPONIBLE else "not_available"
        }
        
        overall_status = "healthy" if all(
            status in ["healthy", "available", "not_available"] 
            for status in services_status.values()
        ) else "degraded"
        
        return jsonify({
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "services": services_status,
            "empleados_count": empleados_count,
            "version": "1.0"
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint no encontrado"}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error": "Método no permitido"}), 405

@app.errorhandler(500)
def internal_error(error):
    print(f"ERROR interno del servidor: {error}")
    return jsonify({"error": "Error interno del servidor"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"INFO: Iniciando aplicación en puerto {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
