from functools import wraps
from flask import request, abort
import os

APIKEY = os.getenv('APIKEY')
FLASK_ENV = os.getenv('FLASK_ENV')

# The actual decorator function
def require_apikey(view_function):
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
