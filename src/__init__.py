from flask import Flask, request, abort, jsonify
from src.routes.aircraft.controllers import aircraft
from functools import wraps
from src.library.vehicle import vehicle
import os

# Create app
def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.debug = True
    app.config.from_mapping(
        # a default secret that should be overridden by instance config
        APIKEY="123",
        FLASK_ENV="development",
        MAVLINK_SETUP_DEBUG="production",
        FLASK_DEBUG=1
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile("config.py", silent=True)
    else:
        # load the test config if passed in
        app.logger.info("test config")
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # if ip address and port are defined, connect automatically but only once
    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        with app.app_context():
            if "IP_ADDRESS" in app.config and "PORT" in app.config:  
                app.logger.info("Seting up TCP mavlink connection automatically from config variables")
                vehicle.setup_mavlink_connection('tcp', app.config['IP_ADDRESS'], app.config['PORT'])   
            elif "SERIAL_PORT" in app.config and "BAUD_RATE" in app.config:
                app.logger.info("Seting up serial mavlink connection automatically from config variables")
                vehicle.setup_mavlink_connection('serial', app.config['SERIAL_PORT'], baud=app.config['BAUD_RATE'])   

    # enforces apikey on eps
    def require_apikey(view_function):
        APIKEY = app.config['APIKEY']
        FLASK_ENV = app.config['FLASK_ENV']

        @wraps(view_function)
        # the new, post-decoration function. Note *args and **kwargs here.
        def decorated_function(*args, **kwargs):
            request.get_data()
            if ((request.values.get('apikey') and request.values.get('apikey') == APIKEY)
                or FLASK_ENV == 'development'):
                return view_function(*args, **kwargs)
            else:
                abort(401)
        return decorated_function

    # Home route
    @app.route('/')
    # @require_apikey
    def index():
        res = {'msg': 'This is the index route.' }
        return jsonify(res), 200

    # Declare routes
    with app.app_context():
        app.register_blueprint(aircraft, url_prefix='/aircraft')
        return app


