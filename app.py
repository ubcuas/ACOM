from flask import Flask
from routes.aircraft.controllers import aircraft
from auth.require_apikey import require_apikey

# Create app
app = Flask(__name__)

# Home route
@app.route('/')
@require_apikey
def index():
    return "This is the index route."

# Declare routes
app.register_blueprint(aircraft, url_prefix='/aircraft')

if __name__ == '__main__':
    app.run(host="0.0.0.0")
