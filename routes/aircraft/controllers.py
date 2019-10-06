from flask import Blueprint, request, jsonify, abort, Response, current_app
from pymavlink import mavutil
import logging

aircraft = Blueprint('aircraft', __name__)
mavlink_connection = None

# Ensure mavlink connection is created before sending requests
@aircraft.before_request
def setup_mavlink_connection():
    global mavlink_connection
    if mavlink_connection == None or mavlink_connection.target_system < 1:
        current_app.logger.info("Mavlink connection is now being initialized")
        mavlink_connection = mavutil.mavlink_connection('tcp:172.18.0.3:5760')
        mavlink_connection.wait_heartbeat(timeout=3)
        current_app.logger.info("Heartbeat from system (system %u component %u)" % (mavlink_connection.target_system, mavlink_connection.target_system))
    if mavlink_connection.target_system < 1:
        abort(400, "Mavlink is not connected")

# Recieves an array of waypoints
# Interrupts aircraft auto mode, switches to guided, runs waypoints, then returns to auto
@aircraft.route('/reroute', methods=['POST'])
def aircraft_reroute():
    global mavlink_connection
    testRetr = mavlink_connection.recv_match()
    if testRetr != None:
        current_app.logger.info(testRetr.to_dict())
    # waypoints = request.data
    return request.data

# Changes the flight mode of the aircraft
@aircraft.route('/flightmode', methods=['POST'])
def aircraft_flightmode():
    return None

# Arms or disarms the aircraft
@aircraft.route('/arm', methods=['POST'])
def aircraft_arm():
    return None

# Manual control
@aircraft.route('/manual', methods=['POST'])
def aircraft_manual():
    return None

# Get data
@aircraft.route('/telemetry', methods=['GET'])
def aircraft_telemetry():
    return None