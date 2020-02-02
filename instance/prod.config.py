# Production configuration file
import os

# set secure api key string
APIKEY = 'jif3fioj32ifj3oi2jf2'

# set to 'development' to bypass apikey requirement
FLASK_ENV = "production"

# set to 'development' to disable initializing mavlink connection
MAVLINK_SETUP_DEBUG = "production"

# set to 1 to enable debug mode for flask
FLASK_DEBUG = 0