from flask import Flask, request, abort, jsonify
from flaskr.routes.aircraft.controllers import aircraft
from functools import wraps
import os

# Create app
def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
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
        app.config.update(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
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
    @require_apikey
    def index():
        res = {'msg': 'This is the index route.' }
        return jsonify(res), 200

    # Declare routes
    with app.app_context():
        app.register_blueprint(aircraft, url_prefix='/aircraft')
        return app


