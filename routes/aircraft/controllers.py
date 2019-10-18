from flask import Blueprint, request, jsonify, abort, Response, current_app
from pymavlink import mavutil
from library import mavlink_messages
import json
import logging

aircraft = Blueprint('aircraft', __name__)
mavlink_connection = None
mavlink_msg_dict = mavlink_messages.MavlinkMessage()
debug = False # Set to True in order to bypass authentication and mavlink connection

# Ensure mavlink connection is created before sending requests
@aircraft.before_request
def setup_mavlink_connection():
    global mavlink_connection
    if not debug:
        # TODO: Add a check to make sure connection is valid
        if mavlink_connection == None or mavlink_connection.target_system < 1:
            current_app.logger.info("Mavlink connection is now being initialized")
            mavlink_connection = mavutil.mavlink_connection('udp:127.0.0.1:14550')
            mavlink_connection.wait_heartbeat(timeout=3)
            current_app.logger.info("Heartbeat from system (system %u component %u)" % (mavlink_connection.target_system, mavlink_connection.target_system))
        if mavlink_connection.target_system < 1:
            abort(400, "Mavlink is not connected")

# Recieves an array of waypoints
# Interrupts aircraft auto mode, switches to guided, runs waypoints, then returns to auto
@aircraft.route('/reroute', methods=['POST'])
def aircraft_reroute():
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

# Request telemetry data based on mavlink message names
# Example: /aircraft/telemetry/GPS_RAW_INT
@aircraft.route('/telemetry/<message_name>', methods=['GET'])
def aircraft_telemetry(message_name):
    global mavlink_connection
    msg = mavlink_connection.recv_match(type=message_name)
    msg_data = {}

    if not msg:
        return {'error': 'Invalid message name'}
    if msg.get_type() == "BAD_DATA":
        return {'error': 'Bad data retrieved'}
    else:
        attributes = mavlink_msg_dict.get_message_attrs(message_name)
        for attr in attributes:
            msg_data[attr] = getattr(msg, attr)

    # jsonify msg_data
    return json.dumps(msg_data)