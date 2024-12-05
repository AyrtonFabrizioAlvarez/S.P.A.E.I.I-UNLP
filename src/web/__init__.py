from flask import Flask, render_template, jsonify
# from src.web.handlers import error
from src.core import database
from src.core.bcrypt import bcrypt
from src.core.config import config
from flask_wtf.csrf import CSRFProtect
from flask_session import Session
from src.web.seeds import seed_countries, seed_generos, seed_estados_civiles, seeds_usuarios
from src.web.controllers.routes import registrar_rutas
from src.web.handlers.auth import is_authenticated, get_id_sesion, get_rol_sesion
from flask_jwt_extended import JWTManager, create_access_token, get_jwt_identity, jwt_required
    
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
    database.init_app(app)
    csrf = CSRFProtect(app)
    session.init_app(app)
    bcrypt.init_app(app)
    app = registrar_rutas(app)
    jwt = JWTManager(app)
    



    @app.route("/")
    def home():
        """
        Función que renderiza el template layout.html
        Returns:
            render_template: Retorna el template layout.html
        """
        token = create_access_token(identity="usuario")
        print("Hola, esto es un JWT")
        print(type(token))
        return render_template("home.html")
    

    app.jinja_env.globals.update(is_authenticated= is_authenticated)
    app.jinja_env.globals.update(get_id_sesion= get_id_sesion)
    app.jinja_env.globals.update(get_rol_sesion= get_rol_sesion)


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
        seeds_usuarios()
        seed_countries()
        seed_generos()
        seed_estados_civiles()

    return app