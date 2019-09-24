from flask import Flask
from routes.aircraft.controllers import aircraft

# Create app
app = Flask(__name__)

# Declare routes
app.register_blueprint(aircraft, url_prefix='/aircraft')

if __name__ == '__main__':
    app.run(host="0.0.0.0")
