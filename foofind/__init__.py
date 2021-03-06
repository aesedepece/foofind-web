# -*- coding: utf-8 -*-
"""
    Módulo principal de la aplicación
"""
from flask import Flask, g, request, session, render_template, redirect, abort
from flaskext.assets import Environment, Bundle
from flaskext.babel import get_translations, gettext as _
from flaskext.login import current_user
from foofind.user import User
from foofind.blueprints.index import index
from foofind.blueprints.page import page
from foofind.blueprints.user import user,init_oauth
from foofind.blueprints.files import files
from foofind.blueprints.control import control
from foofind.blueprints.api import api
from foofind.services import *
from foofind.templates import register_filters
from foofind.utils.webassets_filters import JsSlimmer, CssSlimmer
from foofind.utils import u
from babel import support, localedata
from raven.contrib.flask import Sentry
from raven.conf import setup_logging
from raven.handlers.logging import SentryHandler
from webassets.filter import register_filter
from slimmer import html_slimmer
from hashlib import md5
import os, os.path, logging, defaults

def create_app(config=None, debug=False):
    '''
    Inicializa la aplicación Flask. Carga los siguientes módulos:
     - index: página de inicio
     - page: páginas estáticas
     - user: gestión del usuario
     - files: búsqueda y obtención de ficheros
     - status: servicio de monitorización de la aplicación

    Y además, inicializa los siguientes servicios:
     - Configuración: carga valores por defecto y modifica con el @param config
     - Web Assets: compilación y compresión de recursos estáticos
     - i18n: detección de idioma en la URL y catálogos de mensajes
     - Cache y auth: Declarados en el módulo services
     - Files y users: Clases para acceso a datos
    '''
    app = Flask(__name__)
    app.config.from_object(defaults)
    app.debug = debug

    # Configuración
    if config:
        app.config.from_object(config)

    # Configuración dependiente de la versión del código
    revision_filename_path = os.path.join(os.path.dirname(app.root_path), "revision")
    if os.path.exists(revision_filename_path):
        f = open(revision_filename_path, "r")
        data = f.read()
        f.close()
        revisions = tuple(
            tuple(i.strip() for i in line.split("#")[0].split())
            for line in data.strip().split("\n")
            if line.strip() and not line.strip().startswith("#"))
        revision_hash = md5(data).hexdigest()
        app.config.update(
            CACHE_KEY_PREFIX = "%s%s/" % (
                app.config["CACHE_KEY_PREFIX"] if "CACHE_KEY_PREFIX" in app.config else "",
                revision_hash
                ),
            REVISION_HASH = revision_hash,
            REVISION = revisions
            )
    else:
        app.config.update(
            REVISION_HASH = None,
            REVISION = ()
            )

    # Gestión centralizada de errores
    sentry.init_app(app)
    logging.getLogger().setLevel(logging.DEBUG if debug else logging.INFO)
    setup_logging(SentryHandler(sentry.client))

    # Registra filtros de plantillas
    register_filters(app)

    # Oauth
    init_oauth(app)

    # Blueprints
    app.register_blueprint(index)
    app.register_blueprint(page)
    app.register_blueprint(user)
    app.register_blueprint(files)
    app.register_blueprint(control)
    app.register_blueprint(api)

    # Web Assets
    if not os.path.isdir(app.static_folder+"/gen"): os.mkdir(app.static_folder+"/gen")
    assets = Environment(app)
    assets.debug = app.debug

    register_filter(JsSlimmer)
    register_filter(CssSlimmer)

    assets.register('js_all', Bundle('js/jquery.js', 'js/jquery-ui.js', 'js/files.js', filters='rjsmin', output='gen/packed.js'))
    assets.register('css_all', Bundle('css/main.css', filters=('css_slimmer',), output='gen/packed.css'))
    assets.register('css_ie7', Bundle('css/ie7.css', filters=('css_slimmer',), output='gen/ie7.css'))

    assets.register('js_admin', Bundle('js/jquery.js', 'js/admin.js', filters='rjsmin', output='gen/admin_packed.js'))
    assets.register('css_admin', Bundle('css/admin.css', filters=('css_slimmer',), output='gen/admin_packed.css'))

    # Detección de idioma
    @app.url_defaults
    def add_language_code(endpoint, values):
        '''
        Añade el código de idioma a una URL que lo incluye.
        '''
        if 'lang' in values or not g.lang:
            return
        if app.url_map.is_endpoint_expecting(endpoint, 'lang'):
            values['lang'] = g.lang

    pull_lang_code_languages = tuple(
        (code,localedata.load(code)["languages"][code].capitalize(), code in app.config["BETA_LANGS"])
        for code in app.config["ALL_LANGS"])
    @app.url_value_preprocessor
    def pull_lang_code(endpoint, values):
        '''
        Carga el código de idioma en la variable global.
        '''
        # obtiene el idioma de la URL
        g.url_lang = None
        if values is not None:
            g.url_lang = values.pop('lang', None)

        # si esta lista de idiomas permitidos
        if g.url_lang and g.url_lang in app.config["ALL_LANGS"]:
            g.lang = g.url_lang
        # si el usuario esta logueado y tiene establecido el idioma se asigna ese
        elif "user" in session and "lang" in session["user"]:
            g.lang = session["user"]["lang"]
        # sino se coge el que mas convenga dependiendo del que tenga establecido en su navegador o el idioma por defecto
        elif request.accept_languages.values()!=[]:
            g.lang = request.accept_languages.best_match(app.config["ALL_LANGS"],app.config["LANGS"][0])
        # y sino se pone el idioma por defecto
        else:
            g.lang = app.config["LANGS"][0]

        # se carga la lista de idiomas como se dice en cada idioma
        g.languages = pull_lang_code_languages
        g.beta_lang = g.lang in app.config["BETA_LANGS"]

    # Traducciones
    babel.init_app(app)

    @babel.localeselector
    def get_locale():
        '''
        Devuelve el código del idioma activo.
        '''
        try: return g.lang
        except: return "en"

    # Cache
    cache.init_app(app)

    # Autenticación
    auth.setup_app(app)
    auth.login_view="user.login"
    auth.login_message="login_required"

    @auth.user_loader
    def load_user(userid):
        user = User(userid)
        if not user.has_data:
            data = usersdb.find_userid(userid)
            if data is None:
                return None
            user.set_data(data)
        return user

    # Mail
    mail.init_app(app)

    # Acceso a bases de datos
    filesdb.init_app(app)
    usersdb.init_app(app)
    pagesdb.init_app(app)
    feedbackdb.init_app(app)

    # Actualizador del contador de ficheros
    lastcount = [filesdb.count_files()]
    def countupdater():
        lastcount[0] = long(filesdb.count_files())
    eventmanager.interval(app.config["COUNT_UPDATE_INTERVAL"], countupdater)

    # Refresco de conexiones
    eventmanager.interval(app.config["FOOCONN_UPDATE_INTERVAL"], filesdb.load_servers_conn)

    profiler.init_app(app, feedbackdb)

    # Carga la traducción alternativa
    fallback_lang = support.Translations.load(os.path.join(app.root_path, 'translations'), ["en"])

    @app.before_request
    def before_request():
        # si el idioma de la URL es inválido, devuelve página no encontrada
        if g.url_lang and not g.url_lang in app.config["ALL_LANGS"]:
            abort(404)

        # quita todas las / finales de una URL
        if request.path != '/' and request.path.endswith('/'):
            return redirect(u(request.url).replace(u(request.path), u(request.path)[:-1]),301)

        # ignora peticiones sin blueprint
        if request.blueprint is None:
            return

        # si no es el idioma alternativo, lo añade por si no se encuentra el mensaje
        if g.lang!="en":
            get_translations().add_fallback(fallback_lang)

        # dominio de la web
        g.domain = request.url_root[7:-1] if "https" not in request.url_root else request.url_root[8:-1]
        # título de la página por defecto
        g.title = g.domain
        # contador de archivos totales
        g.count_files = lastcount[0]

    '''
    # TODO: Buscar una forma mejor de hacer esto
    @app.after_request
    def after_request(response):
        if response.mimetype == "text/html":
            response.data = html_slimmer(response.data)
        return response
    '''

    # Páginas de error
    @app.errorhandler(400)
    @app.errorhandler(401)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(405)
    @app.errorhandler(408)
    @app.errorhandler(409)
    @app.errorhandler(410)
    @app.errorhandler(411)
    @app.errorhandler(412)
    @app.errorhandler(413)
    @app.errorhandler(414)
    @app.errorhandler(415)
    @app.errorhandler(416)
    @app.errorhandler(417)
    @app.errorhandler(418)
    @app.errorhandler(500)
    @app.errorhandler(501)
    @app.errorhandler(502)
    @app.errorhandler(503)
    def all_errors(e):
        error=str(e.code)
        message=_("error_"+error+"_message")
        description=_("error_"+error+"_description")
        g.title=error+" "+message if message!="error_"+error+"_message" else e.message.replace("<p>","").replace("</p>","")
        g.count_files = lastcount[0]
        return render_template('error.html',
            zone="errorhandler",
            error=error,
            description=description if description!="error_"+error+"_description" else e.description.replace("<p>","").replace("</p>","")
        ), e.code

    return app


