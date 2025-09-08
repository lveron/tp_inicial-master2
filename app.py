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

# Cargar empleados desde la base de datos con manejo de errores
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
            return jsonify({"valido": False, "mensaje": "No se recibieron datos"}), 200
            
        legajo = data.get('legajo')
        turno = data.get('turno')
        
        if not legajo or not turno:
            return jsonify({"valido": False, "mensaje": "Legajo y turno son requeridos"}), 200
        
        # Validar legajo
        legajo_valido = validador_legajo.validar(legajo)
        if not legajo_valido:
            return jsonify({"valido": False, "mensaje": "Legajo no válido"}), 200
        
        # Validar turno
        turno_valido = validador_turno.validar(legajo, turno)
        if not turno_valido:
            return jsonify({"valido": False, "mensaje": "Turno no válido para este empleado"}), 200
        
        return jsonify({
            "valido": True,
            "mensaje": "Validación exitosa",
            "legajo": legajo,
            "turno": turno
        }), 200
        
    except Exception as e:
        print(f"ERROR en validar_empleado: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"valido": False, "mensaje": "Error interno del servidor"}), 200

@app.route('/registrar_empleado', methods=['POST'])
def registrar_empleado():
    try:
        # Obtener datos del formulario
        legajo = request.form.get('legajo')
        area = request.form.get('area') 
        rol = request.form.get('rol')
        turno = request.form.get('turno')
        
        # La imagen puede venir como file o como string base64
        imagen_file = request.files.get('imagen')
        imagen_base64 = request.form.get('imagen')
        
        # Usar la imagen que esté disponible
        imagen = imagen_file if imagen_file else imagen_base64
        
        # Validar campos obligatorios
        if not all([legajo, area, rol, turno]):
            return jsonify({"exito": False, "mensaje": "Faltan campos obligatorios"}), 200
            
        # Validar turno
        turnos_validos = ['mañana', 'tarde', 'noche']
        if turno not in turnos_validos:
            return jsonify({"exito": False, "mensaje": f"Turno debe ser uno de: {', '.join(turnos_validos)}"}), 200
            
        # Verificar si el legajo ya existe
        if database_manager.empleado_existe(legajo):
            return jsonify({"exito": False, "mensaje": "El empleado ya existe"}), 200
            
        # Procesar imagen y embedding
        if RECONOCIMIENTO_DISPONIBLE and imagen:
            try:
                # Generar embedding de la imagen
                embedding = generarEmbedding(imagen)
                if embedding is None:
                    return jsonify({"exito": False, "mensaje": "No se pudo procesar la imagen facial"}), 200
            except Exception as e:
                print(f"ERROR procesando imagen: {e}")
                return jsonify({"exito": False, "mensaje": "Error procesando la imagen facial"}), 200
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
                "exito": True,
                "mensaje": "Empleado registrado exitosamente",
                "legajo": legajo,
                "area": area,
                "rol": rol,
                "turno": turno,
                "modo": "con_reconocimiento" if RECONOCIMIENTO_DISPONIBLE and imagen else "sin_reconocimiento"
            }), 200
        else:
            return jsonify({"exito": False, "mensaje": "Error al registrar empleado en la base de datos"}), 200
            
    except Exception as e:
        print(f"ERROR en registrar_empleado: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"exito": False, "mensaje": f"Error interno: {str(e)}"}), 200

@app.route('/reconocer', methods=['POST'])
def reconocer():
    try:
        if not RECONOCIMIENTO_DISPONIBLE:
            return jsonify({"exito": False, "mensaje": "Servicio de reconocimiento no disponible"}), 200
            
        # Obtener datos
        legajo = request.form.get('legajo')
        turno = request.form.get('turno')
        imagen = request.files.get('imagen')
        
        if not all([legajo, turno, imagen]):
            return jsonify({"exito": False, "mensaje": "Legajo, turno e imagen son requeridos"}), 200
        
        # Validar legajo y turno
        if not validador_legajo.validar(legajo):
            return jsonify({"exito": False, "mensaje": "Legajo no válido"}), 200
            
        if not validador_turno.validar(legajo, turno):
            return jsonify({"exito": False, "mensaje": "Turno no válido para este empleado"}), 200
        
        # Obtener embeddings de todos los empleados
        empleados_embeddings = {}
        empleados = database_manager.obtener_todos_empleados()
        
        if not empleados:
            return jsonify({"exito": False, "mensaje": "No hay empleados registrados"}), 200
            
        for empleado in empleados:
            if empleado.get('embedding'):
                empleados_embeddings[empleado['legajo']] = empleado['embedding']
        
        if not empleados_embeddings:
            return jsonify({"exito": False, "mensaje": "No hay embeddings disponibles para reconocimiento"}), 200
        
        # Reconocer empleado
        try:
            empleado_reconocido, distancia = reconocer_empleado(imagen, empleados_embeddings)
        except Exception as e:
            print(f"ERROR en reconocimiento facial: {e}")
            return jsonify({"exito": False, "mensaje": "Error en el proceso de reconocimiento facial"}), 200
        
        if empleado_reconocido == legajo:
            # Registrar asistencia
            try:
                resultado = registrar_asistencias.registrar(legajo, turno)
                
                return jsonify({
                    "exito": True,
                    "mensaje": "Ingreso registrado correctamente",
                    "legajo": legajo,
                    "reconocido": True,
                    "distancia": float(distancia) if distancia is not None else None,
                    "asistencia_registrada": resultado,
                    "timestamp": datetime.now().isoformat()
                }), 200
            except Exception as e:
                print(f"ERROR registrando asistencia: {e}")
                return jsonify({
                    "exito": True,
                    "mensaje": "Empleado reconocido, pero error registrando asistencia",
                    "legajo": legajo,
                    "reconocido": True,
                    "distancia": float(distancia) if distancia is not None else None,
                    "asistencia_registrada": False,
                    "timestamp": datetime.now().isoformat()
                }), 200
        else:
            return jsonify({
                "exito": False,
                "mensaje": f"La persona no coincide con el legajo {legajo}. Detectado: {empleado_reconocido or 'Desconocido'}",
                "legajo": legajo,
                "reconocido": False,
                "distancia": float(distancia) if distancia is not None else None,
                "empleado_detectado": empleado_reconocido
            }), 200
            
    except Exception as e:
        print(f"ERROR en reconocer: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"exito": False, "mensaje": f"Error interno: {str(e)}"}), 200

@app.route('/dashboard', methods=['GET'])
def get_dashboard():
    try:
        # Obtener estadísticas básicas
        total_empleados = database_manager.contar_empleados()
        
        # Obtener todos los empleados para análisis de turnos
        empleados = database_manager.obtener_todos_empleados()
        
        # Contar empleados por turno
        turnos = {'mañana': 0, 'tarde': 0, 'noche': 0}
        for empleado in empleados:
            turno = empleado.get('turno', '').lower()
            if turno in turnos:
                turnos[turno] += 1
        
        # Obtener asistencias de hoy (simulado por ahora)
        from datetime import date
        today = date.today()
        asistencias_hoy = 0  # Por ahora simulado
        
        # Generar datos de asistencias de los últimos 7 días (simulado)
        from datetime import datetime, timedelta
        asistencias_semana = []
        for i in range(7):
            fecha = today - timedelta(days=6-i)
            # Por ahora datos simulados - puedes implementar lógica real después
            count = min(total_empleados, max(0, total_empleados - (i % 3)))
            asistencias_semana.append({
                'fecha': fecha.isoformat(),
                'count': count
            })
        
        return jsonify({
            'exito': True,
            'totalEmpleados': total_empleados,
            'asistenciasHoy': asistencias_hoy,
            'empleadosPorTurno': turnos,
            'asistenciasSemana': asistencias_semana
        })
        
    except Exception as e:
        print(f"ERROR en dashboard: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'exito': False,
            'mensaje': f'Error interno: {str(e)}'
        }), 200

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

# Endpoint de debug
@app.route('/debug', methods=['GET'])
def debug():
    return jsonify({
        "RECONOCIMIENTO_DISPONIBLE": RECONOCIMIENTO_DISPONIBLE,
        "EMBEDDING_DISPONIBLE": EMBEDDING_DISPONIBLE,
        "database_ok": database_manager is not None,
        "validadores_ok": validador_legajo is not None and validador_turno is not None,
        "asistencias_ok": registrar_asistencias is not None,
        "total_empleados": len(database_manager.obtener_todos_empleados()) if database_manager else 0
    })

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
