from flask import Blueprint, request, render_template, redirect, url_for, flash, session, abort
from src.core.models.postulacion import Postulacion, PostulacionAsignatura
from src.core.models.asignatura import Asignatura
from src.core.services import (postulacion_service, alumno_service, estado_postulacion_service,
paises_service, genero_service, estado_civil_service, pasaporte_service, cedula_de_identidad_service,
programa_service, archivo_service, usuario_service, email_service, periodo_postulacion_service)
from src.core.services import facultades as facultades_service
from src.core.services import carreras as carreras_service
from src.core.services import asignaturas as asignaturas_service
from src.core.database import db
from flask import current_app as app
from src.web.forms.asignaturas_form import AsignaturasForm
from src.web.handlers.permisos import check
import os
import io
from src.web.handlers.auth import get_rol_sesion, get_id_sesion, get_usuario_actual
from src.web.handlers.permisos import check
import time
from src.web.forms.postulacion_form import PostulacionForm
from src.web.forms.postulacion_estadia_form import PostulacionEstadiaForm
from src.web.forms.presidencia_subir_precarga_form import PresidenciaPrecarga
from src.web.forms.estado_cursada_form import EstadoCursadaForm
from src.web.schemas.archivo_schema import archivo_schema
from src.web.forms.visado_seguro_medico_form import VisadoSeguroMedicoForm

postulacion_bp = Blueprint('postulacion', __name__, url_prefix='/postulaciones')


@postulacion_bp.get('/')
@check("postulaciones_listar")
def listar_postulaciones():

    nombre = request.args.get("nombre")
    apellido = request.args.get("apellido")
    email = request.args.get("email")
    fecha_desde = request.args.get("fecha_desde")
    fecha_hasta = request.args.get("fecha_hasta")
    estado = request.args.get("estado")
    pagina = request.args.get("pagina", 1, type=int)
    ordenado_por = request.args.get("ordenado_por", "nombre")
    orden = request.args.get("orden", "asc")
    id_periodo = request.args.get("id_periodo")
    por_pagina = 10

    postulaciones = postulacion_service.filtrar_postulaciones(
        nombre,
        apellido,
        email,
        estado,
        pagina,
        ordenado_por,
        orden,
        por_pagina,
        fecha_desde,
        fecha_hasta,
        id_periodo
    )

    periodos_postulacion = periodo_postulacion_service.listar_periodos_postulacion()

    estados = estado_postulacion_service.listar_estados()

    #postulaciones = postulacion_service.listar_postulaciones()
    return render_template('postulaciones/listar_postulaciones.html', postulaciones=postulaciones, estados=estados, periodos=periodos_postulacion)


@postulacion_bp.get('/ver_postulacion/<int:id_postulacion>')
@check("postulaciones_detalle")
def ver_postulacion(id_postulacion):
    postulacion = postulacion_service.get_postulacion_by_id(id_postulacion)
    alumno = alumno_service.get_alumno_by_id(postulacion.id_informacion_alumno_entrante)
    pais_residencia = paises_service.get_pais_by_id(alumno.id_pais_de_residencia)
    nacionalidad = paises_service.get_pais_by_id(alumno.id_pais_nacionalidad)
    pais_nacimiento = paises_service.get_pais_by_id(alumno.id_pais_de_nacimiento)
    genero = genero_service.get_genero_by_id(alumno.id_genero)
    estado_civil = estado_civil_service.get_estado_civil_by_id(alumno.id_estado_civil)
    form = None
    if alumno.id_pasaporte is not None:
        pasaporte = pasaporte_service.get_pasaporte_by_id(alumno.id_pasaporte)
        pais_pasaporte = paises_service.get_pais_by_id(pasaporte.id_pais)
    else:
        pasaporte = None
        pais_pasaporte = None
    if alumno.id_cedula_de_identidad is not None:
        cedula_de_identidad = cedula_de_identidad_service.get_cedula_de_identidad_by_id(alumno.id_cedula_de_identidad)
        pais_cedula_de_identidad = paises_service.get_pais_by_id(cedula_de_identidad.id_pais)
    else:
        cedula_de_identidad = None
        pais_cedula_de_identidad = None
    if postulacion.id_programa is not None:
        programa = programa_service.get_programa_by_id(postulacion.id_programa)
    else:
        programa = None

    tutores = postulacion.tutores
    tutor_institucional = None
    tutor_academico = None
    for tutor in tutores:
        if tutor.es_institucional:
            tutor_institucional = tutor
        else:
            tutor_academico = tutor

    archivos = {
        "pasaporte": archivo_service.get_archivo_by_postulacion_and_tipo("pasaporte", alumno.id),
        "cedula_de_identidad": archivo_service.get_archivo_by_postulacion_and_tipo("cedula", alumno.id),
        "carta_recomendacion": archivo_service.get_archivo_by_postulacion_and_tipo("cartaRecomendacion", alumno.id, id_postulacion),
        "plan_trabajo": archivo_service.get_archivo_by_postulacion_and_tipo("planDeTrabajo", alumno.id, id_postulacion),
        "certificado_b1": archivo_service.get_archivo_by_postulacion_and_tipo("certificadoB1", alumno.id, id_postulacion),
        "psicofisico": archivo_service.get_archivo_by_postulacion_and_tipo("psicofisico", alumno.id, id_postulacion),
        "politicas_institucionales": archivo_service.get_archivo_by_postulacion_and_tipo("politicasI", alumno.id, id_postulacion),
        "certificado_discapacidad": archivo_service.get_archivo_by_postulacion_and_tipo("certificadoDiscapacidad", alumno.id, id_postulacion),
        "visado": archivo_service.get_archivo_by_postulacion_and_tipo("visado", alumno.id, id_postulacion),
        "seguro_medico": archivo_service.get_archivo_by_postulacion_and_tipo("seguroMedico", alumno.id, id_postulacion)
    }
    #archivo_service.get_archivos_by_postulacion(postulacion.id)
    rol = get_rol_sesion(session)

    if ( (rol == "presidencia_jefe" or "presidencia_gestor") and (postulacion.estado.nombre == "Postulacion en Espera de Aceptacion") ):
        form = PresidenciaPrecarga()
    else:
        form = None

    if not rol:
        rol = "anonimo"
    
    asignaturas = postulacion.asignaturas

    usuario_actual = get_usuario_actual(session)
    if (rol == "punto_focal"):
        asignaturas_relevantes = postulacion_service.get_asignaturas_de_facultad(postulacion.id, usuario_actual.facultad_id )
        if not asignaturas_relevantes:
            abort(403)
        if any((not asignatura.validado) and (asignatura.asignatura.facultad_id == usuario_actual.facultad_id) for asignatura in postulacion.asignaturas):
            require_punto_focal = True
        else:
            require_punto_focal = False
    else:
        asignaturas_relevantes = None
        require_punto_focal = False

    data = {
        "postulacion": postulacion,
        "alumno": alumno,
        "pais_residencia": pais_residencia,
        "nacionalidad": nacionalidad,
        "pais_nacimiento": pais_nacimiento,
        "genero": genero,
        "estado_civil": estado_civil,
        "pasaporte": pasaporte,
        "cedula_de_identidad": cedula_de_identidad,
        "programa": programa,
        "pais_pasaporte": pais_pasaporte,
        "pais_cedula_de_identidad": pais_cedula_de_identidad,
        "tutor_institucional": tutor_institucional,
        "tutor_academico": tutor_academico,
        "archivos": archivos,
        "rol": rol,
        "asignaturas": asignaturas,
        "asignaturas_relevantes": asignaturas_relevantes,
        "require_punto_focal": require_punto_focal,
        "form": form,
        "rol": rol,
        "usuario_actual": usuario_actual
    }
    return render_template('postulaciones/ver_postulacion.html', **data)


@postulacion_bp.post('aprobar_solicitud_de_postulacion/<int:id_postulacion>')
@check("solicitud_postulacion_aceptar")
def aceptar_solicitud(id_postulacion):
    postulacion = postulacion_service.get_postulacion_by_id(id_postulacion)
    alumno = alumno_service.get_alumno_by_id(postulacion.id_informacion_alumno_entrante)
    if postulacion.estado.nombre == "Solicitud de Postulacion":
        postulacion_service.actualizar_estado_postulacion(postulacion, "Postulacion Iniciada")
        usuario_service.crear_usuario_solicitud_aprobada(alumno.nombre, alumno.apellido, alumno.email, alumno.id)
        flash('Solicitud de postulacion aprobada', 'success')
    elif postulacion.estado.nombre == "Postulacion en Espera de Aceptacion":
        form = PresidenciaPrecarga()
        if not form.validate_on_submit():
            flash('Error al cargar el archivo', 'danger')
            return redirect(url_for('postulacion.ver_postulacion', id_postulacion=id_postulacion))
        if not form.precarga.data:
            flash('Falta subir la precarga electronica antes de aprobar al alumno.', 'danger')
            return redirect(url_for('postulacion.ver_postulacion', id_postulacion=id_postulacion))
        precarga = form.precarga.data
        print(f"El archivo precarga se sube así: {precarga.filename}")
        path_precarga = f"{id_postulacion}_{alumno.id}_precarga_{precarga.filename}"
        archivo_precarga = {
            "titulo": "Precarga electronica",
            "path": path_precarga,
            "id_postulacion": id_postulacion,
            "id_informacion_alumno_entrante": alumno.id
        }

        try:
            archivo_precarga = archivo_schema.load(archivo_precarga)
        except Exception as err:
            print(err)
            flash('Error al cargar el archivo precarga', 'danger')
            return redirect(url_for('postulacion.ver_postulacion', id_postulacion=id_postulacion))
        archivo_service.crear_archivo(**archivo_precarga)
        archivo_service.save_file_minio(request.files['precarga'].read(), archivo_precarga['path'])

        postulacion_service.actualizar_estado_postulacion(postulacion, "Postulacion Aceptada")
        titulo = "Archivos firmados aceptados"
        cuerpo = f"Se han aceptado los archivos firmados que ha subido recientemente."
        destino = alumno.email
        email_service.send_email(titulo, cuerpo, [destino])
        flash('Archivos aprobados', 'success')
    elif postulacion.estado.nombre == "Postulacion en Espera de ser Completada":
        postulacion_service.actualizar_estado_postulacion(postulacion, "Postulacion Completada")
        titulo = "Postulacion completada"
        cuerpo = f"Se han aceptado los últimos archivos subidos y todos los pasos de la postulación han sido completados."
        destino = alumno.email
        email_service.send_email(titulo, cuerpo, [destino])
        flash('Archivos aprobados', 'success')
    elif postulacion.estado.nombre == "Postulacion Esperando Validacion por Facultad":
        punto_focal = usuario_service.buscar_usuario(get_id_sesion(session)) #current user
        postulacion_asignaturas = postulacion.asignaturas
        for postulacion_asignatura in postulacion_asignaturas:
            if (postulacion_asignatura.asignatura.facultad_id == punto_focal.facultad_id): #TODO: AND asignatura.postgrado == punto_focal.postgrado
                postulacion_asignatura.aceptado = True
        db.session.commit()
        flash('Asignaturas aceptadas', 'success')
    return redirect(url_for('postulacion.acciones_pendientes_presidencia'))
    

@postulacion_bp.post('rechazar_solicitud_de_postulacion/<int:id_postulacion>')
@check("solicitud_postulacion_rechazar")
def rechazar_solicitud(id_postulacion):
    postulacion = postulacion_service.get_postulacion_by_id(id_postulacion)
    alumno = alumno_service.get_alumno_by_id(postulacion.id_informacion_alumno_entrante)
    motivo = request.form.get('reject_reason')
    if not motivo:
        flash('El motivo de rechazo es obligatorio.', 'danger')
        return redirect(url_for('postulacion.ver_postulacion', id_postulacion=postulacion.id))
    else:
        if postulacion.estado.nombre == "Solicitud de Postulacion":
            postulacion_service.actualizar_estado_postulacion(postulacion, "Solicitud Rechazada")
            titulo = "Solicitud de Postulacion Rechazada"
            cuerpo = f"Su solicitud de postulacion ha sido rechazada. El motivo de rechazo es: {motivo}"
            
        elif postulacion.estado.nombre == "Postulacion en Espera de Aceptacion":
            postulacion_service.actualizar_estado_postulacion(postulacion, "Postulacion Validada por Facultad")
            titulo = "Archivos firmados rechazados"
            cuerpo = f"Alguno de los archivos firmados subidos en el ultimo paso fue rechazado. Por favor intente devuelta. El motivo de rechazo es: {motivo}"
        elif postulacion.estado.nombre == "Postulacion en Espera de ser Completada":
            postulacion_service.actualizar_estado_postulacion(postulacion, "Postulacion Aceptada")
            titulo = "Archivos nuevos rechazados"
            cuerpo = f"Alguno de los archivos subidos en el ultimo paso fue rechazado. Por favor intente devuelta. El motivo de rechazo es: {motivo}"
        elif postulacion.estado.nombre == "Postulacion Esperando Validacion por Facultad":
            postulacion_service.actualizar_estado_postulacion(postulacion, "Postulacion en Proceso")
            titulo = "Asignaturas rechazadas"
            facultad = get_facultad_by_id(get_usuario_actual().facultad_id).nombre #Éste rechazo solo lo hace un Punto Focal.
            cuerpo = f"Alguna o algunas de las asignaturas a las que se ha postulado han sido rechazadas por el Punto Focal de la siguiente facultad: {facultad} Por favor intente devuelta. El motivo de rechazo es: {motivo}"
        else:
            print("error en postulacion.rechazar_solicitud: Estado no cubierto")
        destino = alumno.email
        email_service.send_email(titulo, cuerpo, [destino])
        flash('Solicitud de postulacion rechazada', 'danger')
        return redirect(url_for('postulacion.acciones_pendientes_presidencia'))

#PUNTO FOCAL ACEPTAR/RECHAZAR ASIGNATURAS
@postulacion_bp.post('aprobar_asignaturas/<int:id_postulacion>')
@check("punto_focal")
def aceptar_asignaturas(id_postulacion):
    postulacion = postulacion_service.get_postulacion_by_id(id_postulacion)
    alumno = alumno_service.get_alumno_by_id(postulacion.id_informacion_alumno_entrante)
    punto_focal = usuario_service.buscar_usuario(get_id_sesion(session)) #current user
    postulacion_service.validar_asignaturas_de_postulacion(postulacion, punto_focal.facultad_id)
    flash('Asignaturas aceptadas', 'success')
    return redirect(url_for('postulacion.acciones_pendientes_focal'))
    
#PUNTO FOCAL ACEPTAR/RECHAZAR ASIGNATURAS
@postulacion_bp.post('rechazar_asignaturas/<int:id_postulacion>')
@check("punto_focal")
def rechazar_asignaturas(id_postulacion):
    postulacion = postulacion_service.get_postulacion_by_id(id_postulacion)
    alumno = alumno_service.get_alumno_by_id(postulacion.id_informacion_alumno_entrante)
    motivo = request.form.get('reject_reason')
    if not motivo:
        flash('El motivo de rechazo es obligatorio.', 'danger')
        return redirect(url_for('postulacion.ver_postulacion', id_postulacion=postulacion.id))
    else:
        postulacion_service.rechazar_asignaturas_de_postulacion(postulacion)
        titulo = "Asignaturas rechazadas"
        facultad = facultades_service.get_facultad_by_id(get_usuario_actual(session).facultad_id).nombre #Éste rechazo solo lo hace un Punto Focal.
        cuerpo = f"Alguna o algunas de las asignaturas a las que se ha postulado han sido rechazadas por el Punto Focal de la siguiente facultad: {facultad} Por favor intente devuelta. El motivo de rechazo es: {motivo}"
        destino = alumno.email
        email_service.send_email(titulo, cuerpo, [destino])
        flash('Solicitud de postulacion rechazada', 'danger')
        return redirect(url_for('postulacion.acciones_pendientes_focal'))


@postulacion_bp.get('/acciones_pendientes_presidencia')
@check("solicitud_postulacion_listar")
def acciones_pendientes_presidencia():
    nombre = request.args.get("nombre")
    apellido = request.args.get("apellido")
    email = request.args.get("email")
    pagina = request.args.get("pagina", 1, type=int)
    ordenado_por = request.args.get("ordenado_por", "nombre")
    orden = request.args.get("orden", "asc")
    por_pagina = 10

    postulaciones = postulacion_service.postulaciones_pendientes_presidencia(
        nombre = nombre,
        apellido = apellido,
        email = email,
        pagina = pagina,
        ordenado_por = ordenado_por,
        orden = orden,
        por_pagina = por_pagina
    )

    estados = estado_postulacion_service.listar_estados()

    #postulaciones = postulacion_service.listar_postulaciones()
    return render_template('postulaciones/acciones_pendientes_presidencia.html', postulaciones=postulaciones, estados=estados)

@postulacion_bp.get('/acciones_pendientes_focal')
@check("punto_focal")
def acciones_pendientes_focal():
    nombre = request.args.get("nombre")
    apellido = request.args.get("apellido")
    email = request.args.get("email")
    pagina = request.args.get("pagina", 1, type=int)
    ordenado_por = request.args.get("ordenado_por", "nombre")
    orden = request.args.get("orden", "asc")
    por_pagina = 10
    idPuntoFocal = session["user_id"]

    postulaciones = postulacion_service.postulaciones_pendientes_focal(
        idPuntoFocal = idPuntoFocal,
        nombre = nombre,
        apellido = apellido,
        email = email,
        pagina = pagina,
        ordenado_por = ordenado_por,
        orden = orden,
        por_pagina = por_pagina
    )

    estados = estado_postulacion_service.listar_estados()

    #postulaciones = postulacion_service.listar_postulaciones()
    return render_template('postulaciones/acciones_pendientes_focal.html', postulaciones=postulaciones, estados=estados)

@postulacion_bp.get('/estado-cursada/<int:id_postulacion>/<int:id_asignatura>') #TODO
@check("punto_focal")
def estado_cursada(id_postulacion, id_asignatura):
    form = EstadoCursadaForm()
    postulacion = postulacion_service.get_postulacion_by_id(id_postulacion)

    postulacion_asignatura = PostulacionAsignatura.query.filter_by(postulacion_id = id_postulacion).filter_by(asignatura_id = id_asignatura).one_or_none()

    form.estado.data = postulacion_asignatura.estado

    if postulacion_asignatura.estado == 'Cursada completada':
        form.nota.data = postulacion_asignatura.aprobado

    if not postulacion_asignatura:
        abort(404)
    return render_template('postulaciones/estado_cursada.html', postulacion=postulacion, form=form, postulacion_asignatura = postulacion_asignatura)

@postulacion_bp.post('/estado-cursada/<int:id_postulacion>/<int:id_asignatura>') #TODO
@check("punto_focal")
def estado_cursada_post(id_postulacion, id_asignatura):
    form = EstadoCursadaForm()

    postulacion = postulacion_service.get_postulacion_by_id(id_postulacion)

    postulacion_asignatura = PostulacionAsignatura.query.filter_by(postulacion_id = id_postulacion).filter_by(asignatura_id = id_asignatura).one_or_none()

    if not form.validate_on_submit():
        flash('Error al actualizar los datos', 'danger')
        return render_template('postulaciones/estado_cursada.html', postulacion=postulacion, form=form, postulacion_asignatura = postulacion_asignatura)
    
    if not form.estado.data:
        flash('Error al intentar leer el estado', 'danger')
        return render_template('postulaciones/estado_cursada.html', postulacion=postulacion, form=form, postulacion_asignatura = postulacion_asignatura)
    
    if form.estado.data == 'Cursada completada' and not form.nota.data:
        flash('Error al intentar leer la nota', 'danger')
        return render_template('postulaciones/estado_cursada.html', postulacion=postulacion, form=form, postulacion_asignatura = postulacion_asignatura)
    
    postulacion_asignatura.estado = form.estado.data
    if form.estado.data == 'Cursada completada':
        postulacion_asignatura.aprobado = form.nota.data
    else:
        postulacion_asignatura.aprobado = -1
    db.session.commit()


    return redirect(url_for('postulacion.ver_postulacion', id_postulacion=id_postulacion))

@postulacion_bp.get('/descargar_archivo/<filename>')
@check("archivo_descargar")
def descargar_archivo(filename):
    return archivo_service.descargar_archivo(filename)
    

@postulacion_bp.get('/mis_postulaciones')
@check("alumno")
def mis_postulaciones():
    id_alumno = None
    if get_rol_sesion(session) == "alumno":
        usuario = usuario_service.buscar_usuario(get_id_sesion(session))
        id_alumno = usuario.id_alumno   

    fecha_desde = request.args.get("fecha_desde")
    fecha_hasta = request.args.get("fecha_hasta")
    estado = request.args.get("estado")
    pagina = request.args.get("pagina", 1, type=int)
    por_pagina = 10

    
    postulaciones = postulacion_service.filtrar_postulaciones_por_alumno(
        estado,
        pagina,
        por_pagina,
        fecha_desde,
        fecha_hasta,
        id_alumno
    )

    estados = estado_postulacion_service.listar_estados()

    return render_template("postulaciones/mis_postulaciones.html", postulaciones=postulaciones, estados=estados)

@postulacion_bp.route('/toggle_inscripciones', methods=['GET', 'POST'])
@check("habilitar_periodo_postulacion")
def periodo_postulacion_toggle():

    periodos = None
    if request.method == 'POST':
        periodo_actual = periodo_postulacion_service.periodo_actual()
        if periodo_actual:
            periodo_postulacion_service.deshabilitar_periodo_postulacion()
        else:
            #fecha_desde = request.form.get("fecha_desde")
            #periodo_postulacion_service.habilitar_periodo_postulacion(fecha_desde)
            periodo_postulacion_service.habilitar_periodo_postulacion()
        time.sleep(0.2)  # TODO. Forma berreta de asegurarme que la lista se actualiza para cuando haga el redirect
        return redirect(url_for('postulacion.periodo_postulacion_toggle'))
    else:
        fecha_desde = request.args.get("fecha_desde")
        fecha_hasta = request.args.get("fecha_hasta")
        orden = request.args.get("orden", "desc")
        pagina = request.args.get("pagina", 1, type=int)
        por_pagina = 10

        periodos = periodo_postulacion_service.listar_periodos_postulacion(fecha_desde, fecha_hasta, pagina, por_pagina, orden)
    return render_template('postulaciones/toggle_inscripciones.html', periodos=periodos)

@postulacion_bp.get('/repostulacion')
#@check("alumno")
def repostulacion():
    form = PostulacionForm()
    return render_template('postulaciones/repostulacion.html', form=form)

@postulacion_bp.get('/ingresar_datos_estadia/<int:id_postulacion>')
#@check("alumno")
def ingresar_datos_estadia(id_postulacion):
    form = PostulacionEstadiaForm()
    postulacion = postulacion_service.get_postulacion_by_id(id_postulacion)
    return render_template('postulaciones/postulacion_estadia.html', form=form, id_postulacion=id_postulacion, consulado_dato=postulacion.consulado_visacion)

@postulacion_bp.post('/guardar_datos_estadia/<int:id_postulacion>')
#@check("alumno")
def guardar_datos_estadia(id_postulacion):
    form = PostulacionEstadiaForm()
    postulacion = postulacion_service.get_postulacion_by_id(id_postulacion)
    if not form.validate_on_submit():
        flash('Error al cargar los datos', 'danger')
        return render_template('postulaciones/postulacion_estadia.html', form=form, id_postulacion=id_postulacion, consulado_dato=postulacion.consulado_visacion)
    
    if not form.psicofisico.data:
        flash('El archivo psicofisico es obligatorio', 'danger')
        return render_template('postulaciones/postulacion_estadia.html', form=form, id_postulacion=id_postulacion, consulado_dato=postulacion.consulado_visacion)
    
    if not form.politicas_institucionales.data:
        flash('El archivo de politicas institucionales es obligatorio', 'danger')
        return render_template('postulaciones/postulacion_estadia.html', form=form, id_postulacion=id_postulacion, consulado_dato=postulacion.consulado_visacion)
    
    if not form.fecha_ingreso.data:
        flash('La fecha de ingreso es obligatoria', 'danger')
        return render_template('postulaciones/postulacion_estadia.html', form=form, id_postulacion=id_postulacion, consulado_dato=postulacion.consulado_visacion)
    
    if not form.duracion_estadia.data:
        flash('La duracion de la estadia es obligatoria', 'danger')
        return render_template('postulaciones/postulacion_estadia.html', form=form, id_postulacion=id_postulacion, consulado_dato=postulacion.consulado_visacion)
    
    alumno = postulacion.informacion_alumno_entrante
    psicofisico = form.psicofisico.data
    path_psicofisico = f"{id_postulacion}_{alumno.id}_psicofisico_{psicofisico.filename}"
    archivo_psicofisico = {
        "titulo": "Psicofisico firmado",
        "path": path_psicofisico,
        "id_postulacion": id_postulacion,
        "id_informacion_alumno_entrante": alumno.id
    }

    try:
        archivo_psicofisico = archivo_schema.load(archivo_psicofisico)
    except Exception as err:
        flash('Error al cargar el archivo psicofisico', 'danger')
        return render_template('postulaciones/postulacion_estadia.html', form=form, id_postulacion=id_postulacion, consulado_dato=postulacion.consulado_visacion)
    
    politicas_institucionales = form.politicas_institucionales.data
    path_politicas_institucionales = f"{id_postulacion}_{alumno.id}_politicasI_{politicas_institucionales.filename}"
    archivo_politicas = {
        "titulo": "Politicas institucionales firmadas",
        "path": path_politicas_institucionales,
        "id_postulacion": id_postulacion,
        "id_informacion_alumno_entrante": alumno.id
    }

    try:
        archivo_politicas = archivo_schema.load(archivo_politicas)
    except Exception as err:
        flash('Error al cargar el archivo de politicas institucionales', 'danger')
        return render_template('postulaciones/postulacion_estadia.html', form=form, id_postulacion=id_postulacion, consulado_dato=postulacion.consulado_visacion)
    
    alumno.discapacidad = form.discapacidad.data
    if form.discapacidad.data == True and form.certificado_discapacidad.data:
        certificado_discapacidad = form.certificado_discapacidad.data
        path_certificado_discapacidad = f"{id_postulacion}_{alumno.id}_certificadoDiscapacidad_{certificado_discapacidad.filename}"
        archivo_certificado_discapacidad = {
            "titulo": "Certificado de discapacidad",
            "path": path_certificado_discapacidad,
            "id_postulacion": id_postulacion,
            "id_informacion_alumno_entrante": alumno.id
        }
        try:
            archivo_certificado_discapacidad = archivo_schema.load(archivo_certificado_discapacidad)
        except Exception as err:
            flash('Error al cargar el archivo de certificado de discapacidad', 'danger')
            return render_template('postulaciones/postulacion_estadia.html', form=form, id_postulacion=id_postulacion, consulado_dato=postulacion.consulado_visacion)

    postulacion.fecha_ingreso = form.fecha_ingreso.data
    postulacion.duracion_estadia = form.duracion_estadia.data
    estado = estado_postulacion_service.get_estado_by_name("Postulacion en Espera de Aceptacion")
    postulacion.estado = estado
    postulacion.id_estado = estado.id

    if form.consulado_visacion.data != "":
        postulacion.consulado_visacion = form.consulado_visacion.data
   
    db.session.commit()
    file_psicofisico = archivo_service.crear_archivo(**archivo_psicofisico)
    file_psicofisico.postulacion = postulacion
    file_politicas = archivo_service.crear_archivo(**archivo_politicas)
    file_politicas.postulacion = postulacion

    if form.discapacidad.data == True and form.certificado_discapacidad.data:
        file_certificado = archivo_service.crear_archivo(**archivo_certificado_discapacidad)
        file_certificado.postulacion = postulacion
        archivo_service.save_file_minio(request.files['certificado_discapacidad'].read(), archivo_certificado_discapacidad['path'])
    
    archivo_service.save_file_minio(request.files['psicofisico'].read(), archivo_psicofisico['path'])
    archivo_service.save_file_minio(request.files['politicas_institucionales'].read(), archivo_politicas['path'])

    emails = usuario_service.get_email_admin_presidencia()
    email_service.send_email("Se subieron los archivos psicofíisico y políticas institucionales", f"Se han subido los archivos psicofísico y políticas institucionales por parte del alumno {alumno.nombre} {alumno.apellido}", emails)

    flash('Datos guardados exitosamente', 'success')
    return redirect(url_for('postulacion.mis_postulaciones'))

@postulacion_bp.get('/<int:postulacion_id>/seleccionar_materias')
#@check("alumno")
def seleccionar_materias(postulacion_id):

    facultades = facultades_service.get_all_facultades()

    cantidad_materias = 5

    asignaturas_seleccionadas = []
    for i in range(0,cantidad_materias):
        f_id = request.args.get(f"asignatura_{i}", None)
        if f_id and f_id != "":
            asignaturas_seleccionadas.append(asignaturas_service.get_asignatura_by_id(f_id))
        else:
            asignaturas_seleccionadas.append(None)

    facultades_seleccionadas = []
    for i in range(0,cantidad_materias):
        f_id = request.args.get(f"facultad_{i}", None)
        if f_id and f_id != "":
            facultades_seleccionadas.append(facultades_service.get_facultad_by_id(f_id))
        else:
            facultades_seleccionadas.append(None)
    
    carreras_seleccionadas = []
    for i in range(0,cantidad_materias):
        f_id = request.args.get(f"carrera_{i}", None)
        if f_id and f_id != "":
            carreras_seleccionadas.append(carreras_service.get_carrera_by_id(f_id))
        else:
            carreras_seleccionadas.append(None)

    return render_template('postulaciones/elegir_materias.html', cantidad_materias=cantidad_materias, facultades=facultades, facultades_seleccionadas=facultades_seleccionadas, carreras_seleccionadas=carreras_seleccionadas, asignaturas_seleccionadas=asignaturas_seleccionadas, postulacion_id=postulacion_id)

@postulacion_bp.post('/guardar_materias/<int:postulacion_id>')
#@check("alumno")
def guardar_materias(postulacion_id):
    cantidad_materias = 5  
    asignaturas_ids = []
    facultades_ids = set()

    postulacion = postulacion_service.get_postulacion_by_id(postulacion_id)

    # Procesar los inputs enviados
    for i in range(cantidad_materias):
        asignatura_id = request.form.get(f"asignatura_{i}")
        facultad_id = request.form.get(f"facultad_{i}")

        if asignatura_id and asignatura_id.strip() and facultad_id and facultad_id.strip():
            asignaturas_ids.append(int(asignatura_id))  # Convertir a entero si es necesario
            facultades_ids.add(int(facultad_id))

    if len(asignaturas_ids) > 5:
        flash('No puede seleccionar más de 5 asignaturas', 'danger')
        return redirect(url_for('postulacion.seleccionar_materias', postulacion_id=postulacion_id))
    
    if len(facultades_ids) > 3:
        flash('No puede seleccionar más de 3 facultades', 'danger')
        return redirect(url_for('postulacion.seleccionar_materias', postulacion_id=postulacion_id))

    if not asignaturas_ids and not facultades_ids:
        if not postulacion.de_posgrado:
            flash('Debe seleccionar al menos una asignatura', 'danger')
            return redirect(url_for('postulacion.seleccionar_materias', postulacion_id=postulacion_id))
        else:
            postulacion.estado = estado_postulacion_service.get_estado_by_name("Postulacion Validada por Facultad")
            db.session.commit()
            flash('Datos guardados exitosamente', 'success')
            return redirect(url_for('postulacion.mis_postulaciones'))

    # Relacionar asignaturas con la postulación
    postulacion_service.asociar_asignaturas_a_postulacion(postulacion_id, asignaturas_ids)

    # Obtener puntos focales de las facultades seleccionadas
    # Obtener los puntos focales únicos de las facultades seleccionadas
    puntos_focales = facultades_service.get_puntos_focales_by_facultades(list(facultades_ids))

    # Enviar mensajes a los puntos focales
    enviados = set()
    for punto_focal in puntos_focales:
        if punto_focal.email not in enviados:  # Evitar duplicados por email
            enviados.add(punto_focal.email)
    email_service.send_email("Nueva postulación", "Se ha realizado una nueva postulación", list(enviados))

    postulacion_service.actualizar_estado_postulacion(postulacion, "Postulacion Esperando Validacion por Facultad")
    db.session.commit()
    flash('Datos guardados exitosamente', 'success')
    return redirect(url_for('postulacion.mis_postulaciones'))

@postulacion_bp.get('/visado_seguro_medico/<int:id_postulacion>')
#@check("alumno")
def visado_seguro_medico(id_postulacion):
    form = VisadoSeguroMedicoForm()
    return render_template('postulaciones/visado_seguro_medico_form.html', form=form, id_postulacion=id_postulacion)

@postulacion_bp.post('/guardar_visado_seguro_medico/<int:id_postulacion>')
#@check("alumno")
def visado_seguro_medico_post(id_postulacion):
    form = VisadoSeguroMedicoForm()
    postulacion = postulacion_service.get_postulacion_by_id(id_postulacion)
    if not form.validate_on_submit():
        flash('Error al cargar los datos', 'danger')
        return render_template('postulaciones/visado_seguro_medico.html', form=form, id_postulacion=id_postulacion)
    
    if not form.visado.data:
        flash('El archivo de visado es obligatorio', 'danger')
        return render_template('postulaciones/visado_seguro_medico.html', form=form, id_postulacion=id_postulacion)
    
    if not form.seguro_medico.data:
        flash('El archivo de seguro medico es obligatorio', 'danger')
        return render_template('postulaciones/visado_seguro_medico.html', form=form, id_postulacion=id_postulacion)
    

    alumno = postulacion.informacion_alumno_entrante
    visado = form.visado.data
    path_visado = f"{id_postulacion}_{alumno.id}_visado_{visado.filename}"
    archivo_visado = {
        "titulo": visado.filename,
        "path": path_visado,
        "id_postulacion": id_postulacion,
        "id_informacion_alumno_entrante": alumno.id
    }

    try:
        archivo_visado_load = archivo_schema.load(archivo_visado)
    except Exception as err:
        flash('Error al cargar el archivo visado', 'danger')
        return render_template('postulaciones/visado_seguro_medico.html', form=form, id_postulacion=id_postulacion)
    
    seguro_medico = form.seguro_medico.data
    path_seguro_medico = f"{id_postulacion}_{alumno.id}_seguroMedico_{seguro_medico.filename}"
    archivo_seguro_medico = {
        "titulo": seguro_medico.filename,
        "path": path_seguro_medico,
        "id_postulacion": id_postulacion,
        "id_informacion_alumno_entrante": alumno.id
    }

    try:
        archivo_seguro_medico_load = archivo_schema.load(archivo_seguro_medico)
    except Exception as err:
        flash('Error al cargar el archivo de seguro medico', 'danger')
        return render_template('postulaciones/visado_seguro_medico.html', form=form, id_postulacion=id_postulacion)
    
    postulacion.estado = estado_postulacion_service.get_estado_by_name("Postulacion en Espera de ser Completada")

    db.session.commit()
    
    file_visado = archivo_service.crear_archivo(**archivo_visado) 
    file_visado.postulacion = postulacion
    file_seguro_medico = archivo_service.crear_archivo(**archivo_seguro_medico)
    file_seguro_medico.postulacion = postulacion
    archivo_service.save_file_minio(request.files['visado'].read(), archivo_visado['path'])
    archivo_service.save_file_minio(request.files['seguro_medico'].read(), archivo_seguro_medico['path'])

    emails = usuario_service.get_email_admin_presidencia()
    email_service.send_email("Se han subidos los archivos visado y seguro médico", f"Se han recibido los archivos visado y seguro médico del alumno {alumno.nombre} {alumno.apellido}", emails)

    flash('Datos guardados exitosamente', 'success')
    return redirect(url_for('postulacion.mis_postulaciones'))
