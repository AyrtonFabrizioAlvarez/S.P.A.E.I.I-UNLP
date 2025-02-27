from src.core.database import db
from datetime import datetime

class Postulacion(db.Model):
    __tablename__ = 'postulacion'

    id = db.Column(db.Integer, primary_key=True)
    de_posgrado = db.Column(db.Boolean, nullable=False)
    universidad_origen = db.Column(db.String(50), nullable=False)
    consulado_visacion = db.Column(db.String(50), nullable=True)
    convenio = db.Column(db.String(50), nullable=True)
    fecha_ingreso = db.Column(db.Date, nullable=True)
    duracion_estadia = db.Column(db.Integer, nullable=True)
    
    id_estado = db.Column(db.Integer, db.ForeignKey('estado.id'), nullable=False)
    id_informacion_alumno_entrante = db.Column(db.Integer, db.ForeignKey('informacion_alumno_entrante.id'), nullable=False)
    id_programa = db.Column(db.Integer, db.ForeignKey('programa.id'), nullable=True)
    id_periodo_postulacion = db.Column(db.Integer, db.ForeignKey('periodo_postulacion.id'), nullable=False)
    
    creacion = db.Column(db.DateTime, default=datetime.now)
    actualizacion = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    estado = db.relationship('Estado', back_populates='postulaciones')
    informacion_alumno_entrante = db.relationship('InformacionAlumnoEntrante', back_populates='postulaciones')
    tutores = db.relationship('Tutor', secondary='postulacion_tutor', back_populates='postulaciones')
    asignaturas = db.relationship('PostulacionAsignatura', back_populates='postulacion', passive_deletes=True)
    programa = db.relationship('Programa', back_populates='postulaciones')
    archivos = db.relationship('Archivo', back_populates='postulacion', foreign_keys='Archivo.id_postulacion')
    periodo_postulacion = db.relationship('PeriodoPostulacion', back_populates='postulaciones')

    def __repr__(self):
        return f'<Postulacion id-{self.id}, alumno-{self.informacion_alumno_entrante}, de_posgrado-{self.de_posgrado}, estado-{self.estado}>'
    
    def get_asignaturas(self):
        materias = []
        for asignatura in self.asignaturas:
            materias.append(asignatura.asignatura)
        return materias