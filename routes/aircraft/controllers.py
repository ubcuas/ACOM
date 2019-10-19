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
@aircraft.route('/flightmode/<mav_mode>', methods=['POST'])
def aircraft_flightmode(mav_mode):
    global mavlink_connection
    mavlink_connection.mav.command_long_send(
        mavlink_connection.target_system,
        mavlink_connection.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_MODE,
        int(mav_mode),
        0, 0, 0, 0, 0, 0, 0  # unused parameters
    )
    return aircraft_telemetry('HEARTBEAT')

# Arms the aircraft
@aircraft.route('/arm', methods=['PUT'])
def aircraft_arm():
    global mavlink_connection
    mavlink_connection.mav.command_long_send(
        mavlink_connection.target_system,
        mavlink_connection.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0, # confirmation
        1, # arm
        0, 0, 0, 0, 0, 0  # unused parameters
    )
    return aircraft_telemetry('HEARTBEAT')

# Disarms the aircraft
@aircraft.route('/disarm', methods=['PUT'])
def aircraft_disarm():
    global mavlink_connection
    mavlink_connection.mav.command_long_send(
        mavlink_connection.target_system,
        mavlink_connection.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0, # confirmation
        0, # disarm
        0, 0, 0, 0, 0, 0 # unused parameters
    )
    return aircraft_telemetry('HEARTBEAT')

# RTL
@aircraft.route('/rtl', methods=['PUT'])
def aircraft_rtl():
    global mavlink_connection
    mavlink_connection.mav.command_long_send(
        mavlink_connection.target_system,
        mavlink_connection.target_component,
        mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH,
        0, 0, 0, 0, 0, 0, 0, 0 # unused parameters
    )
    return aircraft_telemetry('GPS_RAW_INT')

# Manual control / Fly-to
@aircraft.route('/manual', methods=['POST'])
def aircraft_manual():
    global mavlink_connection
    mavlink_connection.mav.command_long_send(
        mavlink_connection.target_system,
        mavlink_connection.target_component,
        mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
        request.json['hold'],
        request.json['accept_radius'],
        request.json['pass_radius'],
        request.json['yaw'],
        request.json['lat'],
        request.json['lon'],
        request.json['alt'],
        0
    )
    return aircraft_telemetry('GPS_RAW_INT')

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