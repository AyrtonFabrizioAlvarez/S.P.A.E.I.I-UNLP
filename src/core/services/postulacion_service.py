from src.core.models.postulacion.postulacion import Postulacion
from src.core.database import db
from src.core.models.alumno.informacion_alumno_entrante import InformacionAlumnoEntrante
from src.core.models.postulacion.estado import Estado
from src.core.models.usuario import Usuario
from src.core.models.asignatura import Asignatura
from src.core.models.postulacion.tutor import Tutor
from src.core.models.postulacion import PostulacionAsignatura
from src.core.services import alumno_service, email_service, usuario_service
from sqlalchemy import or_, and_, desc

def crear_postulacion(**data):
    """
    Crea una postulación.
    """
    postulacion = Postulacion(**data)
    db.session.add(postulacion)
    db.session.commit()
    return postulacion

def listar_postulaciones():
    """
    Lista todas las postulaciones.
    """
    return Postulacion.query.all()

def get_postulacion_by_id(id_postulacion):
    """
    Obtiene una postulación por su id.
    """
    return Postulacion.query.get_or_404(id_postulacion)

def filtrar_postulaciones(
        nombre,
        apellido,
        email,
        estado,
        pagina,
        ordenado_por,
        orden,
        por_pagina,
        fecha_desde=None,
        fecha_hasta=None,
        id_periodo=None,
):
    
    query = Postulacion.query
    if nombre:
        query = query.filter(Postulacion.informacion_alumno_entrante.has(InformacionAlumnoEntrante.nombre.ilike(f"%{nombre}%")))
    if apellido:
        query = query.filter(Postulacion.informacion_alumno_entrante.has(InformacionAlumnoEntrante.apellido.ilike(f"%{apellido}%")))
    if email:
        query = query.filter(Postulacion.informacion_alumno_entrante.has(InformacionAlumnoEntrante.email.ilike(f"%{email}%")))
    if estado:
        query = query.filter(Postulacion.estado.has(Estado.nombre.ilike(f"%{estado}%")))
    if fecha_desde:
        query = query.filter(Postulacion.creacion >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Postulacion.creacion <= fecha_hasta)
    if id_periodo:
        query = query.filter(Postulacion.id_periodo_postulacion == id_periodo)

    if ordenado_por:
        query = ordenar_postulaciones(query, ordenado_por, orden)

    return query.paginate(page=pagina, per_page=por_pagina, error_out=False)

def ordenar_postulaciones(
        query,
        ordenado_por,
        orden
):
    query = query.join(InformacionAlumnoEntrante, InformacionAlumnoEntrante.id == Postulacion.id_informacion_alumno_entrante)

    if orden == "asc":
        if ordenado_por == "nombre":
            return query.order_by(InformacionAlumnoEntrante.nombre.asc())
        elif ordenado_por == "apellido":
            return query.order_by(InformacionAlumnoEntrante.apellido.asc())
        else:
            return query.order_by(InformacionAlumnoEntrante.email.asc())
    else:
        if ordenado_por == "nombre":
            return query.order_by(InformacionAlumnoEntrante.nombre.desc())
        elif ordenado_por == "apellido":
            return query.order_by(InformacionAlumnoEntrante.apellido.desc())
        else:
            return query.order_by(InformacionAlumnoEntrante.email.desc())
        

def actualizar_estado_postulacion(postulacion, nuevo_estado):
    """
    Actualiza el estado de una postulación.
    """
    nuevo_estado = Estado.query.filter_by(nombre=nuevo_estado).first()
    if not nuevo_estado:
        return None
    else:
        postulacion.estado = nuevo_estado
        db.session.commit()
        return postulacion
    

def filtrar_postulaciones_por_alumno(
        estado,
        pagina,
        por_pagina,
        fecha_desde,
        fecha_hasta,
        id_alumno
):
    query = Postulacion.query

    if estado:
        query = query.filter(Postulacion.estado.has(Estado.nombre.ilike(f"%{estado}%")))
    if fecha_desde:
        query = query.filter(Postulacion.creacion >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Postulacion.creacion <= fecha_hasta)
    if id_alumno:
        query = query.filter(Postulacion.id_informacion_alumno_entrante == id_alumno)

    return query.paginate(page=pagina, per_page=por_pagina, error_out=False)

def postulaciones_pendientes_presidencia(
        nombre = None,
        apellido = None,
        email = None,
        ordenado_por = None,
        orden = None,
        fecha_desde=None,
        fecha_hasta=None,
        id_periodo=None,
        pagina = None, 
        por_pagina = None):
    query = Postulacion.query
    query = query.filter(Postulacion.estado.has(Estado.requiere_accion_presidencia))
    if nombre:
        query = query.filter(Postulacion.informacion_alumno_entrante.has(InformacionAlumnoEntrante.nombre.ilike(f"%{nombre}%")))
    if apellido:
        query = query.filter(Postulacion.informacion_alumno_entrante.has(InformacionAlumnoEntrante.apellido.ilike(f"%{apellido}%")))
    if email:
        query = query.filter(Postulacion.informacion_alumno_entrante.has(InformacionAlumnoEntrante.email.ilike(f"%{email}%")))
    if fecha_desde:
        query = query.filter(Postulacion.creacion >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Postulacion.creacion <= fecha_hasta)
    if id_periodo:
        query = query.filter(Postulacion.id_periodo_postulacion == id_periodo) 

    if ordenado_por:
        query = ordenar_postulaciones(query, ordenado_por, orden)

    if not pagina:
        return query.all()
    return query.paginate(page=pagina, per_page=por_pagina, error_out=False)

def postulaciones_pendientes_focal(
        idPuntoFocal,
        nombre = None,
        apellido = None,
        email = None,
        ordenado_por = None,
        orden = None,
        fecha_desde=None,
        fecha_hasta=None,
        id_periodo=None,
        pagina = None, 
        por_pagina = None):
    
    punto_focal = Usuario.query.get(idPuntoFocal)
    query = Postulacion.query
    query = query.filter(Postulacion.estado.has(Estado.requiere_accion_focal))
    query = query.filter(Postulacion.asignaturas.any(
        and_(
            (PostulacionAsignatura.asignatura.has(Asignatura.facultad_id == punto_focal.facultad_id)),
            ~(PostulacionAsignatura.validado))
        ))
    query = query.filter(
        or_(
            Postulacion.de_posgrado == punto_focal.posgrado, #Si la postulacion es de posgrado y el punto focal tambien
            ~Postulacion.de_posgrado == punto_focal.grado #Si la postulacion es de grado y el punto focal tambien
        )
    )

    if nombre:
        query = query.filter(Postulacion.informacion_alumno_entrante.has(InformacionAlumnoEntrante.nombre.ilike(f"%{nombre}%")))
    if apellido:
        query = query.filter(Postulacion.informacion_alumno_entrante.has(InformacionAlumnoEntrante.apellido.ilike(f"%{apellido}%")))
    if email:
        query = query.filter(Postulacion.informacion_alumno_entrante.has(InformacionAlumnoEntrante.email.ilike(f"%{email}%")))
    if fecha_desde:
        query = query.filter(Postulacion.creacion >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Postulacion.creacion <= fecha_hasta)
    if id_periodo:
        query = query.filter(Postulacion.id_periodo_postulacion == id_periodo)
    
    if ordenado_por:
        query = ordenar_postulaciones(query, ordenado_por, orden)

    if not pagina:
        return query.all()
    return query.paginate(page=pagina, per_page=por_pagina, error_out=False)
def asociar_asignaturas_a_postulacion(postulacion_id, asignaturas):
    """
    Asocia asignaturas a una postulación.
    """
    postulacion = get_postulacion_by_id(postulacion_id)
    if not postulacion:
        return False
    for asignatura in asignaturas:
        a = Asignatura.query.get(asignatura)
        relacion = PostulacionAsignatura(postulacion = postulacion, asignatura = a)
        db.session.add(relacion)
    db.session.commit()
    return True

def obtener_postulacion_actual_de_alumno(alumno_id): #nota, esto requiere la ID del modelo informacion_alumno_entrante, NO la del usuario.
    return (
        db.session.query(Postulacion)
        .filter(Postulacion.id_informacion_alumno_entrante == alumno_id)
        .order_by(desc(Postulacion.creacion))
        .first()
    )

def obtener_tutor_academico_de_postulacion(postulacion_id):
    return (
        db.session.query(Tutor)
        .join(Postulacion.tutores)
        .filter(Postulacion.id == postulacion_id, Tutor.es_institucional == False)
        .first()
    )

def validar_asignaturas_de_postulacion(postulacion, facultad_id):
    for postulacion_asignatura in postulacion.asignaturas:
        if postulacion_asignatura.asignatura.facultad_id == facultad_id:
            postulacion_asignatura.validado = True
            postulacion_asignatura.estado = "Cursando"
    
    db.session.commit()
    for postulacion_asignatura in postulacion.asignaturas:
        if (not postulacion_asignatura.validado):
            return
    
    actualizar_estado_postulacion(postulacion, "Postulacion Esperando Carta de Aceptacion")
    emails = usuario_service.get_email_admin_presidencia()
    alumno = alumno_service.get_alumno_by_id(postulacion.id_informacion_alumno_entrante)
    titulo = "Todas las asignaturas aceptadas alumno "+alumno.nombre+" "+alumno.apellido
    cuerpo = f"Se han aceptado todas las asignaturas a las que se ha postulado. Por favor validar las asignaturas y subir carta de aceptacion."
    #emails.append(alumno.email)
    email_service.send_email(titulo, cuerpo, emails)
    return

def rechazar_asignaturas_de_postulacion(postulacion):
    db.session.query(PostulacionAsignatura).filter_by(postulacion_id=postulacion.id).delete(synchronize_session=False)
    db.session.commit()
    actualizar_estado_postulacion(postulacion, "Postulacion Iniciada")
    return

def get_asignaturas_de_facultad(postulacion_id, facultad_id):
    postulacion = get_postulacion_by_id(postulacion_id)

    materias = []
    for asignatura in postulacion.get_asignaturas():
        if asignatura.facultad_id == facultad_id:
            materias.append(asignatura)
    return materias


def puede_postularse(email):
    id_alumno = alumno_service.get_alumno_by_email(email).id if alumno_service.get_alumno_by_email(email) else None
    if id_alumno:
        postulacion = obtener_postulacion_actual_de_alumno(id_alumno)
        if postulacion.estado.nombre == "Postulacion Finalizada" or postulacion.estado.nombre == "Postulacion Cancelada o Interrumpida" or postulacion.estado.nombre == "Solicitud Rechazada":
            return True
        else:
            return False
    else:
        return True

def postulacion_corresponde_a_punto_focal(postulacion, user_punto_focal):
    #si la postulacion es de posgrado y el punto focal tambien, O si la postulacion es de grado y el punto focal tambien
    if ( (postulacion.de_posgrado == user_punto_focal.posgrado) or (not postulacion.de_posgrado == user_punto_focal.grado) ):
        for postulacion_asignatura in postulacion.asignaturas:
            if postulacion_asignatura.asignatura.facultad_id == user_punto_focal.facultad_id:
                return True #si existe al menos una asignatura que le corresponda al punto focal
    return False

def postulacion_en_paso5(postulacion):
    estados_validos = [
        "Postulacion Validada por Facultad",
        "Postulacion Aceptada",
        "Postulacion Completada",
        "Postulacion Esperando Certificado Calificaciones",
        "Postulacion Finalizada",
        "Postulacion en Espera de Aceptacion",
        "Postulacion en Espera de ser Completada"
    ]
    return (postulacion.estado.nombre in estados_validos)

def postulacion_en_paso6(postulacion):
    estados_validos = [
        "Postulacion Aceptada",
        "Postulacion Completada",
        "Postulacion Esperando Certificado Calificaciones",
        "Postulacion Finalizada",
        "Postulacion en Espera de ser Completada"
    ]
    return (postulacion.estado.nombre in estados_validos)