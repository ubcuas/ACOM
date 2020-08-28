# Development configuration file
import os

# set secure api key string
APIKEY = '123'

# set to 'development' to bypass apikey requirement
FLASK_ENV = "development"

# set to 'development' to disable initializing mavlink connection
MAVLINK_SETUP_DEBUG = "production"

# set to 1 to enable debug mode for flask
FLASK_DEBUG = 1

# set optional default ip address & port
IP_ADDRESS = "164.2.0.3"
PORT = 5760