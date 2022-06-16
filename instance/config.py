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
# IP_ADDRESS = "acom-sitl"
# PORT = 5760

# set optional default serial port & baud rate
SERIAL_PORT = "/dev/ttyACM0"
BAUD_RATE = 115200