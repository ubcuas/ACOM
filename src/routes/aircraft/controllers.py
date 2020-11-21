from flask import Blueprint, request, jsonify, abort, Response, current_app
from pymavlink import mavutil, mavwp
from src.library.util import parseRequest, parseJson
import json
import logging
import time
from functools import wraps

aircraft = Blueprint('aircraft', __name__)

# decorator that checks if a mavlink connection has been established
def connection_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if current_app.vehicle.is_connected():
            return f(*args, **kwargs)
        else:
            return jsonify({"error": "Aircraft connection has not been established"}), 400

    return wrap

# sets and establishes a mavlink connection
@aircraft.route('/connect', methods=['POST'])
def aircraft_connect():
    connectionRequest = request.json

    if 'ipAddress' not in connectionRequest:
        return jsonify({"error": "IP address was not specified"}), 401

    if 'port' not in connectionRequest:
        return jsonify({"error": "Port was not specified"}), 402

    # set the ip address and port to the aircraft
    ip_address = connectionRequest['ipAddress']
    port = connectionRequest['port']

    # initialize the mavlink connection
    setup_mavlink_connection(ip_address, port)

    return jsonify({"msg": "Connected to the aircraft successfully"}), 201

# Recieves an array of waypoints
# Interrupts aircraft auto mode, switches to guided, runs waypoints, then returns to auto
@aircraft.route('/reroute', methods=['POST'])
@connection_required
def aircraft_reroute():
    json = request.json

    points = json['waypoints']

    current_app.vehicle.reroute(points)
    return aircraft_gps()

# Arms the aircraft
@aircraft.route('/arm', methods=['PUT'])
@connection_required
def aircraft_arm():
    current_app.vehicle.arm()
    return aircraft_heartbeat()

# Disarms the aircraft
@aircraft.route('/disarm', methods=['PUT'])
@connection_required
def aircraft_disarm():
    current_app.vehicle.disarm()
    return aircraft_heartbeat()

# RTL
@aircraft.route('/rtl', methods=['PUT'])
@connection_required
def aircraft_rtl():

    current_app.vehicle.mavlink_connection.set_mode_rtl()
    return aircraft_heartbeat()

# set mode manual
@aircraft.route('/manual', methods=['PUT'])
@connection_required
def aircraft_manual():
    global mavlink_connection
    current_app.vehicle.mavlink_connection.set_mode_manual()
    return aircraft_heartbeat()

# set mode to auto
@aircraft.route('/auto', methods=['PUT'])
@connection_required
def aircraft_auto():
    global mavlink_connection
    current_app.vehicle.mavlink_connection.set_mode_auto()
    return aircraft_heartbeat()

# set mode to guided
@aircraft.route('/guided', methods=['PUT'])
@connection_required
def aircraft_guided():
    global mavlink_connection
    current_app.vehicle.mavlink_connection.set_mode('GUIDED')
    return aircraft_heartbeat()

# Request latest msg
@aircraft.route('/telemetry/msg', methods=['GET'])
@connection_required
def aircraft_latest():
    msg = current_app.vehicle.mavlink_connection.recv_match(blocking=True)
    print(msg)
    return jsonify(msg.to_dict()), 200

# Request flight mode
@aircraft.route('/telemetry/flightmode', methods=['GET'])
@connection_required
def aircraft_flightmode():
    flightmode = current_app.vehicle.mavlink_connection.flightmode
    return flightmode, 200

# Request gps data
@aircraft.route('/telemetry/gps', methods=['GET'])
@connection_required
def aircraft_gps():
    location = current_app.vehicle.telemetry.get_location()
    return jsonify(location), 200

# Request heartbeat data
@aircraft.route('/telemetry/heartbeat', methods=['GET'])
@connection_required
def aircraft_heartbeat():
    current_app.vehicle.telemetry.wait("HEARTBEAT")
    return jsonify(current_app.vehicle.telemetry.heartbeat), 200
    # return jsonify(hb_data), 200

# Guided control / Fly-to
@aircraft.route('/flyto', methods=['POST'])
@connection_required
def aircraft_flyto(lat=0, lng=0, alt=0):
    lat = parseRequest(request, 'lat', lat)
    lng = parseRequest(request, 'lng', lng)
    alt = parseRequest(request, 'alt', alt)
    current_app.vehicle.fly_to(lat, lng, alt)
    return aircraft_heartbeat()

# Guided control / Take-off
@aircraft.route('/takeoff', methods=['POST'])
@connection_required
def aircraft_takeoff():
    current_app.vehicle.mavlink_connection.mav.command_long_send(
        current_app.vehicle.mavlink_connection.target_system,
        current_app.vehicle.mavlink_connection.target_component,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0,
        parseRequest(request, 'pitch', 0),
        0,
        0,
        parseRequest(request, 'yaw', 0),
        parseRequest(request, 'lat', 0),
        parseRequest(request, 'lng', 0),
        parseRequest(request, 'alt', 0),
    )
    return aircraft_heartbeat()

@aircraft.route('/home_position', methods=['GET'])
@connection_required
def aircraft_home_position():
    current_app.vehicle.mavlink_connection.mav.command_long_send(
        current_app.vehicle.mavlink_connection.target_system,
        current_app.vehicle.mavlink_connection.target_component,
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
    msg = current_app.vehicle.telemetry.wait("HOME_POSITION")

    return jsonify(msg), 200

# upload mission waypoints
@aircraft.route('/mission', methods=['POST'])
@connection_required
def upload_mission_wps():
    missionRequest = request.json
    # error checking
    if missionRequest:
        if 'wps' not in missionRequest or not missionRequest['wps']:
            return jsonify({ "error": "No waypoints were given" }), 402

        if 'takeoffAlt' not in missionRequest:
            return jsonify({ "error": "Takeoff altitude was not given" }), 403
        elif missionRequest['takeoffAlt'] <= 0:
            return jsonify({ "error": "Takeoff altitude must be >0" }), 404
    else:
        return jsonify({ "error": "Mission format is invalid" }), 405

    # checks the number of wps recieved vs the number sent
    try:
        num_wps_loaded = current_app.vehicle.waypoints.upload_mission_wps(missionRequest['wps'], missionRequest['takeoffAlt'], missionRequest['rtl'])
        return jsonify({ "result": "Waypoints uploaded successfully!", "wps_uploaded": num_wps_loaded }), 201
    except Exception as e:
        return jsonify({ "error": "Waypoints failed to upload." }), 401

# download mission waypoints
@aircraft.route('/mission', methods=['GET'])
@connection_required
def download_mission_wps():
    data = current_app.vehicle.waypoints.download_mission_wps()
    return jsonify(data), 200

# Ensure mavlink connection is created before sending requests
def setup_mavlink_connection(ip_address, port):
    if 'development' not in current_app.config['MAVLINK_SETUP_DEBUG']:
        try:
            current_app.vehicle.setup_mavlink_connection(ip_address, port)
        except Exception:
            abort(400, "Mavlink is not connected")