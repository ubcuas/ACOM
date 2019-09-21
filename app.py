from flask import Flask, request, jsonify, abort, Response
from pymavlink import mavutil
import logging

app = Flask(__name__)
mavlink_connection = None

@app.before_request
def setup_mavlink_connection():
    global mavlink_connection
    if mavlink_connection == None or mavlink_connection.target_system < 1:
        app.logger.info("Mavlink connection is now being initialized")
        mavlink_connection = mavutil.mavlink_connection('tcp:localhost:5760')
        mavlink_connection.wait_heartbeat(timeout=3)
        app.logger.info("Heartbeat from system (system %u component %u)" % (mavlink_connection.target_system, mavlink_connection.target_system))
    if mavlink_connection.target_system < 1:
        abort(400, "Mavlink is not connected")

# Recieves an array of waypoints
# Interrupts aircraft auto mode, switches to guided, runs waypoints, then returns to auto
@app.route('/aircraft/reroute', methods=['POST'])
def aircraft_reroute():
    global mavlink_connection
    app.logger.info(mavlink_connection.waypoint_current())
    waypoints = request.data

    return request.data
    
if __name__ == '__main__':
    app.run(host="0.0.0.0")
