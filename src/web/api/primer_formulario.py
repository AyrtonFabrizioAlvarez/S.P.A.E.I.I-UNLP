from flask import Blueprint, jsonify, request, make_response, session
from flask_wtf.csrf import generate_csrf
import base64
from src.core.database import db

from src.core.services import (paises_service, genero_service, usuario_service,
estado_civil_service, archivo_service, alumno_service, pasaporte_service, 
cedula_de_identidad_service, postulacion_service, tutor_service, programa_service,
estado_postulacion_service, email_service, periodo_postulacion_service)
from src.web.schemas.archivo_schema import archivo_schema
from src.web.schemas.cedula_de_identidad_schema import cedula_de_identidad_schema
from src.web.schemas.postulacion_schema import postulacion_schema
from src.web.schemas.pasaporte_schema import pasaporte_schema
from src.web.schemas.estado_civil_schema import estados_civiles_schema
from src.web.schemas.tutor_schema import tutor_schema
from src.web.schemas.genero_schema import generos_schema
from src.web.schemas.pais_schema import paises_schema
from src.web.schemas.informacion_alumno_entrante_schema import informacion_alumno_entrante_schema
from src.web.schemas.programa_schema import programas_schema
from src.web.handlers.auth import get_rol_sesion, get_id_sesion




bp = Blueprint("solicitud_postulacion", __name__, url_prefix="/api/postulacion")


#@base.validation(schema=PostulacionForm, method="POST")

@bp.post("/primer-formulario")
def primer_formulario():
    """
    Primer formulario de postulación.
    """
    #return jsonify({"error": "Hola"}), 400
    data = request.get_json()
    if not data:
        return jsonify({"error": "No se encontraron datos en el request"}), 400
    
    periodo = periodo_postulacion_service.periodo_actual().id
    if periodo is None:
        return jsonify({"error": "No hay un periodo de postulación activo"}), 400
    data_postulacion = data["postulacion"]
    data_alumno = data["alumno"]
    id_programa = data["id_programa"]
    data_tutor_institucional = data["tutorInstitucional"]
    data_tutor_academico = data["tutorAcademico"]
    data_cedula = data["cedula_de_identidad"]
    data_pasaporte = data["pasaporte"]
    data_archivos = data["archivo"]
    mercosur = data["mercosur"]
    convenio_programa = data["convenioPrograma"]
    data_titulos = data["titulos"]
    id_periodo_postulacion = periodo_postulacion_service.periodo_actual().id
    
    if not id_periodo_postulacion:
        return jsonify({"error": "Actualmente no hay un periodo de inscripción abierto"}), 400
    if not data_postulacion:
        return jsonify({"error": "No se encontraron datos de la postulación"}), 400
    if not data_alumno:
        return jsonify({"error": "No se encontraron datos del alumno"}), 400
    if not data_tutor_institucional:
        return jsonify({"error": "No se encontraron datos del tutor institucional"}), 400
    if not data_tutor_academico:
        return jsonify({"error": "No se encontraron datos del tutor académico"}), 400
    if not data_archivos:
        return jsonify({"error": "No se encontraron datos de los archivos"}), 400
    if not convenio_programa:
        return jsonify({"error": "No se encontraron datos sobre si es por convenio o programa"}), 400
    if not data_titulos:
        return jsonify({"error": "No se encontraron datos de los títulos"}), 400


    
    try:
        alumno = informacion_alumno_entrante_schema.load(data_alumno)
    except Exception as err:
        return jsonify({"error": f"Error al cargar los datos del alumno: {err}"}), 400
    alumno = alumno_service.crear_informacion_alumno_entrante(**alumno)
    if not alumno:
        return jsonify({"error": "Error al crear el alumno. El alumno ya posee un usuario en el sistema o posee una solicitud pendiente."}), 400

    estado_postulacion = estado_postulacion_service.get_estado_by_name("Solicitud de Postulacion")
    data_postulacion["id_estado"] = estado_postulacion.id
    data_postulacion["id_periodo_postulacion"] = periodo
    data_postulacion["id_informacion_alumno_entrante"] = alumno.id
    if convenio_programa == "programa":
        data_postulacion["id_programa"] = id_programa
        del data_postulacion["convenio"]
    if data_postulacion["consulado_visacion"] == "":
        del data_postulacion["consulado_visacion"]
    try:
        postulacion = postulacion_schema.load(data_postulacion)
    except Exception as err:
        return jsonify({"error": f"Error al cargar los datos de la postulación: {err}"}), 400
    try:
        postulacion = postulacion_service.crear_postulacion(**postulacion)
    except Exception as err:
        return jsonify({"error": f"Error al crear la postulación: {err}"}), 400
    postulacion.informacion_alumno_entrante = alumno
    postulacion.estado = estado_postulacion


    if not mercosur:
        if not data_pasaporte:
            return jsonify({"error": "No se encontraron datos del pasaporte"}), 400
        else:
            archivo_pasaporte = base64.b64decode(data_archivos["pasaporte"])
            if not data_titulos["titulo_pasaporte"]:
                return jsonify({"error": "No se encontraron datos del título del pasaporte"}), 400
            filename = f"{alumno.id}_pasaporte_{data_titulos['titulo_pasaporte']}"
            archivo_service.save_file_minio(archivo_pasaporte, filename)
            titulo_pasaporte = {
                "titulo": data_titulos["titulo_pasaporte"],
                "path": filename
            }
            try:
                pasaporte = archivo_schema.load(titulo_pasaporte)
            except Exception as err:
                return jsonify({"error": f"Error al cargar los datos del pasaporte: {err}"}), 400
            pasaporte_archivo = archivo_service.crear_archivo(**pasaporte)
            data_pasaporte["id_archivo"] = pasaporte_archivo.id
            pasaporte = pasaporte_schema.load(data_pasaporte)
            pasaporte = pasaporte_service.crear_pasaporte(**pasaporte)
            pasaporte_archivo.pasaporte = pasaporte
            pasaporte_archivo.informacion_alumno_entrante = alumno
            pasaporte_archivo.postulacion = postulacion
            alumno.id_pasaporte = pasaporte.id
    else:
        if not data_pasaporte and not data_cedula:
            return jsonify({"error": "No se encontraron datos de la cédula de identidad ni del pasaporte"}), 400
        if data_pasaporte:
            archivo_pasaporte = base64.b64decode(data_archivos["pasaporte"])
            if not data_titulos["titulo_pasaporte"]:
                return jsonify({"error": "No se encontraron datos del título del pasaporte"}), 400
            filename = f"{alumno.id}_pasaporte_{data_titulos['titulo_pasaporte']}"
            archivo_service.save_file_minio(archivo_pasaporte, filename)
            titulo_pasaporte = {
                "titulo": data_titulos["titulo_pasaporte"],
                "path": filename
            }
            try:
                pasaporte = archivo_schema.load(titulo_pasaporte)
            except Exception as err:
                return jsonify({"error": f"Error al cargar los datos del pasaporte: {err}"}), 400
            pasaporte_archivo = archivo_service.crear_archivo(**pasaporte)
            data_pasaporte["id_archivo"] = pasaporte_archivo.id
            pasaporte = pasaporte_schema.load(data_pasaporte)
            pasaporte = pasaporte_service.crear_pasaporte(**pasaporte)
            pasaporte_archivo.pasaporte = pasaporte
            pasaporte_archivo.informacion_alumno_entrante = alumno
            pasaporte_archivo.postulacion = postulacion
            alumno.id_pasaporte = pasaporte.id
        if data_cedula:
            archivo_cedula = base64.b64decode(data_archivos["cedula_de_identidad"])
            if not data_titulos["titulo_cedula_de_identidad"]:
                return jsonify({"error": "No se encontraron datos del título del pasaporte"}), 400
            filename = f"{alumno.id}_cedula_{data_titulos['titulo_pasaporte']}"
            archivo_service.save_file_minio(archivo_cedula, filename)
            titulo_cedula = {
                "titulo": data_titulos["titulo_cedula_de_identidad"],
                "path": filename
            }
            try:
                cedula_de_identidad = archivo_schema.load(titulo_cedula)
            except Exception as err:
                return jsonify({"error": f"Error al cargar los datos de la cedula de identidad: {err}"}), 400
            cedula_de_identidad_archivo = archivo_service.crear_archivo(**cedula_de_identidad)
            data_cedula["id_archivo"] = cedula_de_identidad_archivo.id
            cedula_de_identidad = cedula_de_identidad_schema.load(data_cedula)
            cedula_de_identidad = cedula_de_identidad_service.crear_cedula_de_identidad(**cedula_de_identidad)
            cedula_de_identidad_archivo.cedula_identidad = cedula_de_identidad
            cedula_de_identidad_archivo.informacion_alumno_entrante = alumno
            cedula_de_identidad_archivo.postulacion = postulacion
            alumno.id_cedula_de_identidad = cedula_de_identidad.id

   
    carta_recomendacion = data_archivos["carta_recomendacion"]
    if not carta_recomendacion:
        return jsonify({"error": "No se encontraron datos de la carta de recomendación"}), 400
    else:
        archivo_carta_recomendacion = base64.b64decode(data_archivos["carta_recomendacion"])
        if not data_titulos["titulo_carta_recomendacion"]:
            return jsonify({"error": "No se encontraron datos del título de la carta de recomendación"}), 400
        filename = f"{postulacion.id}_{alumno.id}_cartaRecomendacion_{data_titulos['titulo_carta_recomendacion']}"
        archivo_service.save_file_minio(archivo_carta_recomendacion, filename)
        titulo_carta_recomendacion = {
            "titulo": data_titulos["titulo_carta_recomendacion"],
            "path": filename
        }
        try:
            carta_recomendacion = archivo_schema.load(titulo_carta_recomendacion)
        except Exception as err:
            return jsonify({"error": f"Error al cargar los datos de la carta de recomendación: {err}"}), 400
        carta_recomendacion = archivo_service.crear_archivo(**carta_recomendacion)
        
    
    if alumno.discapacitado:
        if data_archivos["certificadoDiscapacidad"]:
            archivo_certificado_discapacidad = base64.b64decode(data_archivos["certificadoDiscapacidad"])
            if not data_titulos["titulo_certificado_discapacidad"]:
                return jsonify({"error": "No se encontraron datos del título del certificado de discapacidad"}), 400
            
            path_certificado_discapacidad = f"{alumno.id}_certificadoDiscapacidad_{data_titulos['titulo_certificado_discapacidad']}"
            archivo_service.save_file_minio(archivo_certificado_discapacidad, path_certificado_discapacidad)
            titulo_certificado_discapacidad = {
                "titulo": data_titulos["titulo_certificado_discapacidad"],
                "path": path_certificado_discapacidad
            }
            try:
                certificado_discapacidad = archivo_schema.load(titulo_certificado_discapacidad)
            except Exception as err:
                return jsonify({"error": f"Error al cargar los datos del certificado de discapacidad: {err}"}), 400
            certificado_discapacidad = archivo_service.crear_archivo(**certificado_discapacidad)
            certificado_discapacidad.informacion_alumno_entrante = alumno
            certificado_discapacidad.postulacion = postulacion


    if postulacion.de_posgrado:
        if not data_archivos["plan_trabajo"]:
            return jsonify({"error": "No se encontraron datos del plan de trabajo"}), 400
        else:
            plan_trabajo = base64.b64decode(data_archivos["plan_trabajo"])
            if not data_titulos["titulo_plan_trabajo"]:
                return jsonify({"error": "No se encontraron datos del título del plan de trabajo"}), 400
            filename = f"{postulacion.id}_{alumno.id}_planDeTrabajo_{data_titulos['titulo_plan_trabajo']}"
            archivo_service.save_file_minio(plan_trabajo, filename)
            titulo_plan_trabajo = {
                "titulo": data_titulos["titulo_plan_trabajo"],
                "path": filename
            }
            try:
                plan_trabajo = archivo_schema.load(titulo_plan_trabajo)
            except Exception as err:
                return jsonify({"error": f"Error al cargar los datos del plan de trabajo: {err}"}), 400
            plan_trabajo = archivo_service.crear_archivo(**plan_trabajo)
            plan_trabajo.informacion_alumno_entrante = alumno
            plan_trabajo.postulacion = postulacion

    
    pais_nacionalidad = paises_service.get_pais_by_id(alumno.id_pais_nacionalidad)
    if pais_nacionalidad.hispanohablante:
        if data_archivos["certificado_b1"]:
            archivo_certificado_b1 = base64.b64decode(data_archivos["certificado_b1"])
            if not data_titulos["titulo_certificado_b1"]:
                return jsonify({"error": "No se encontraron datos del título del certificado B1"}), 400
            filename = f"{alumno.id}_certificadoB1_{data_titulos['titulo_certificado_b1']}"
            archivo_service.save_file_minio(archivo_certificado_b1, filename)
            titulo_certificado_b1 = {
                "titulo": data_titulos["titulo_certificado_b1"],
                "path": filename
            }
            try:
                certificado_b1 = archivo_schema.load(titulo_certificado_b1)
            except Exception as err:
                return jsonify({"error": f"Error al cargar los datos del certificado B1: {err}"}), 400
            certificado_b1 = archivo_service.crear_archivo(**certificado_b1)
            certificado_b1.informacion_alumno_entrante = alumno
            certificado_b1.postulacion = postulacion
    else:
        if not data_archivos["certificado_b1"]:
            return jsonify({"error": "No se encontraron datos del certificado B1"}), 400
        else:
            archivo_certificado_b1 = base64.b64decode(data_archivos["certificado_b1"])
            if not data_titulos["titulo_certificado_b1"]:
                return jsonify({"error": "No se encontraron datos del título del certificado B1"}), 400
            filename = f"{alumno.id}_certificadoB1_{data_titulos['titulo_certificado_b1']}"
            archivo_service.save_file_minio(archivo_certificado_b1, filename)
            titulo_certificado_b1 = {
                "titulo": data_titulos["titulo_certificado_b1"],
                "path": filename
            }
            try:
                certificado_b1 = archivo_schema.load(titulo_certificado_b1)
            except Exception as err:
                return jsonify({"error": f"Error al cargar los datos del certificado B1: {err}"}), 400
            certificado_b1 = archivo_service.crear_archivo(**certificado_b1)
            certificado_b1.informacion_alumno_entrante = alumno
            certificado_b1.postulacion = postulacion
    
    try:
        tutor_institucional = tutor_schema.load(data_tutor_institucional)
    except:
        return jsonify({"error": "Error al cargar los datos del tutor institucional"}), 400
    tutor_institucional = tutor_service.crear_obtener_tutor(**tutor_institucional)
    try:
        tutor_academico = tutor_schema.load(data_tutor_academico)
    except:
        return jsonify({"error": "Error al cargar los datos del tutor académico"}), 400
    tutor_academico = tutor_service.crear_obtener_tutor(**tutor_academico)

    carta_recomendacion.informacion_alumno_entrante = alumno
    carta_recomendacion.postulacion = postulacion
    
        

    postulacion.tutores.append(tutor_institucional)
    postulacion.tutores.append(tutor_academico)
    db.session.commit()

    emails = usuario_service.get_email_admin_presidencia()
    email_service.send_email("Solicitud de Postulación", "Se ha recibido una solicitud de postulación", emails)
    return jsonify(data), 201
    
    
    

@bp.get("/primer-formulario-data")
def primer_formulario_get():
    """
    
    """
    paises = paises_service.listar_paises()
    generos = genero_service.listar_generos()
    estados_civiles = estado_civil_service.listar_estados_civiles()
    programas = programa_service.listar_programas_habilitados()
    data_paises = paises_schema.dump(paises)
    data_generos = generos_schema.dump(generos)
    data_estados_civiles = estados_civiles_schema.dump(estados_civiles)
    data_programas = programas_schema.dump(programas)

    token = generate_csrf()
    data_response = {
        "paises": data_paises,
        "generos": data_generos,
        "estados_civiles": data_estados_civiles,
        "csrf_token": token,
        "programas": data_programas,
        "periodo_activo": periodo_postulacion_service.esta_activo(),
    }

    return jsonify(data_response), 200

