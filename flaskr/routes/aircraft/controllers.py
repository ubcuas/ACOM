from flask import Blueprint, request, jsonify, abort, Response, current_app
from pymavlink import mavutil
from flaskr.library.util import parseRequest
import json
import logging

aircraft = Blueprint('aircraft', __name__)
mavlink_connection = None

# Ensure mavlink connection is created before sending requests
@aircraft.before_request
def setup_mavlink_connection():
    global mavlink_connection
    if 'development' not in current_app.config['MAVLINK_SETUP_DEBUG']:
        # TODO: Add a check to make sure connection is valid
        if mavlink_connection == None or mavlink_connection.target_system < 1:
            current_app.logger.info("Mavlink connection is now being initialized")
            mavlink_connection = mavutil.mavlink_connection('tcp:172.18.0.3:5760')
            mavlink_connection.wait_heartbeat(timeout=3)
            current_app.logger.info("Heartbeat from system (system %u component %u)" % (mavlink_connection.target_system, mavlink_connection.target_component))
            
            # request all data type streams
            mavlink_connection.mav.request_data_stream_send(mavlink_connection.target_system, mavlink_connection.target_component,
                                                    mavutil.mavlink.MAV_DATA_STREAM_ALL, 1, 1)
        if mavlink_connection.target_system < 1:
            abort(400, "Mavlink is not connected")

# Recieves an array of waypoints
# Interrupts aircraft auto mode, switches to guided, runs waypoints, then returns to auto
@aircraft.route('/reroute', methods=['POST'])
def aircraft_reroute():
    return request.data

# Arms the aircraft
@aircraft.route('/arm', methods=['PUT'])
def aircraft_arm():
    global mavlink_connection
    mavlink_connection.arducopter_arm()
    return aircraft_heartbeat()

# Disarms the aircraft
@aircraft.route('/disarm', methods=['PUT'])
def aircraft_disarm():
    global mavlink_connection
    mavlink_connection.arducopter_disarm()
    return aircraft_heartbeat()

# RTL
@aircraft.route('/rtl', methods=['PUT'])
def aircraft_rtl():
    global mavlink_connection
    mavlink_connection.set_mode_rtl()
    return aircraft_heartbeat()

# set mode manual
@aircraft.route('/manual', methods=['PUT'])
def aircraft_manual():
    global mavlink_connection
    mavlink_connection.set_mode_manual()
    return aircraft_heartbeat()

# set mode to auto
@aircraft.route('/auto', methods=['PUT'])
def aircraft_auto():
    global mavlink_connection
    mavlink_connection.set_mode_auto()
    return aircraft_heartbeat()

# set mode to guided
@aircraft.route('/guided', methods=['PUT'])
def aircraft_guided():
    global mavlink_connection
    mavlink_connection.set_mode('GUIDED')
    return aircraft_heartbeat()

# Request gps data
@aircraft.route('/telemetry/gps', methods=['GET'])
def aircraft_gps():
    global mavlink_connection
    location = mavlink_connection.location()
    return json.dumps(location.__dict__)

# Request heartbeat data
@aircraft.route('/telemetry/heartbeat', methods=['GET'])
def aircraft_heartbeat():
    global mavlink_connection
    hb = mavlink_connection.wait_heartbeat()
    hb_data = {}

    if not hb:
        return {'error': 'Failed to retrieve heartbeat'}
    if hb.get_type() == "BAD_DATA":
        return {'error': 'Bad data retrieved'}
    else:
        attributes = hb._fieldnames
        for attr in attributes:
            hb_data[attr] = getattr(hb, attr)

    # jsonify hb_data
    return json.dumps(hb_data)

# Guided control / Fly-to
@aircraft.route('/flyto', methods=['POST'])
def aircraft_flyto():
    global mavlink_connection
    frame = mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT
    mavlink_connection.mav.mission_item_send(0, 0, 0, frame,
        mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
        2, # current wp - guided command
        0, 
        0,
        0, 
        0, 
        0, 
        parseRequest(request, 'lat', 0),
        parseRequest(request, 'lng', 0),
        parseRequest(request, 'alt', 0)
    )
    return aircraft_heartbeat()

# Guided control / Take-off
@aircraft.route('/takeoff', methods=['POST'])
def aircraft_takeoff():
    global mavlink_connection
    mavlink_connection.mav.command_long_send(
        mavlink_connection.target_system,
        mavlink_connection.target_component,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0,
        parseRequest(request, 'pitch', 0),
        0,
        0,
        parseRequest(request, 'yaw', 0),
        parseRequest(request, 'lat', 0),
        parseRequest(request, 'lng', 0),
        request.json['alt']
    )
    return aircraft_heartbeat()

@aircraft.route('/home_position', methods=['GET'])
def aircraft_home_position():
    global mavlink_connection
    mavlink_connection.mav.command_long_send(
        mavlink_connection.target_system,
        mavlink_connection.target_component,
        mavutil.mavlink.MAV_CMD_GET_HOME_POSITION, 
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0
    )
    msg = mavlink_connection.recv_match(type='HOME_POSITION')
    msg_data = {}

    if not msg:
        return json.dumps({'error': 'Invalid message name'})
    if msg.get_type() == "BAD_DATA":
        return json.dumps({'error': 'Bad data retrieved'})
    else:
        attributes = msg._fieldnames
        for attr in attributes:
            msg_data[attr] = getattr(msg, attr)

    # jsonify msg_data
    return json.dumps(msg_data)
