from flask import Flask, render_template, jsonify, send_file, abort
import os
from src.core import database
from src.core.bcrypt import bcrypt
from src.core.config import config
from flask_wtf.csrf import CSRFProtect
from flask_session import Session
from datetime import timedelta
from src.web.seeds import seed_paises, seed_generos, seed_estados_civiles, seeds_usuarios, seeds_facultades
from src.web.controllers.routes import registrar_rutas
from src.web.handlers.auth import is_authenticated, get_id_sesion, get_rol_sesion, get_id_alumno_sesion
from src.web.handlers.permisos import check_permiso
from flask_mail import Mail
from src.web.handlers import error
    
session = Session()
def create_app(env="development", static_folder="../../static", template_folders=""):
    """
    Crea una instancia de la aplicación de Flask con la configuración dada.
    Args:
        env (str, optional): Defaults to "development".
        static_folder (str, optional): Defaults to "../../static".
        template_folders (str, optional): Defaults to "".
    Returns:
        Flask: Retorna la instancia de la aplicación de Flask.
    """
    app = Flask(__name__, static_folder=static_folder)
    app.config.from_object(config[env])
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
    database.init_app(app)
    csrf = CSRFProtect(app)
    session.init_app(app)
    bcrypt.init_app(app)
    app = registrar_rutas(app)
    mail = Mail(app)
        
    @app.route("/")
    def home():
        """
        Función que renderiza el template layout.html
        Returns:
            render_template: Retorna el template layout.html
        """
        return render_template("home.html")    

    app.jinja_env.globals.update(is_authenticated= is_authenticated)
    app.jinja_env.globals.update(get_id_sesion= get_id_sesion)
    app.jinja_env.globals.update(get_rol_sesion= get_rol_sesion)
    app.jinja_env.globals.update(check_permiso= check_permiso)
    app.jinja_env.globals.update(get_id_alumno_sesion= get_id_alumno_sesion)
    
    app.register_error_handler(404, error.error_not_found)
    app.register_error_handler(403, error.sin_permisos)    

    @app.cli.command(name="reset-db")
    def reset_db():
        """
        Comando para resetear la base de datos
        """
        database.reset()
   
    @app.cli.command(name="seeds-db")
    def usuarios_roles_seed():
        """
        Comando para crear los seeds de la base de datos
        """
        usuarios = seeds_usuarios()
        seed_paises()
        seed_generos()
        seed_estados_civiles()
        seeds_facultades(usuarios)

    return app