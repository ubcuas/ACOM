from functools import wraps
from flask import request, abort
from config.apikey import apikey

# The actual decorator function
def require_apikey(view_function):
    @wraps(view_function)
    # the new, post-decoration function. Note *args and **kwargs here.
    def decorated_function(*args, **kwargs):
        request.get_data()
        if request.values.get('apikey') and request.values.get('apikey') == apikey:
            return view_function(*args, **kwargs)
        else:
            abort(401)
    return decorated_function
