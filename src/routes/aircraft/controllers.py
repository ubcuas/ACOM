from flask import Blueprint, request, jsonify, abort, Response, current_app
from pymavlink import mavutil, mavwp
from src.library.util import parseRequest, parseJson
import json
import logging
import time
from functools import wraps
from src.library.vehicle import vehicle
import traceback
import sys

aircraft = Blueprint("aircraft", __name__)


# decorator that checks if a mavlink connection has been established
def connection_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if vehicle.is_connected():
            return f(*args, **kwargs)
        else:
            return (
                jsonify({"error": "Aircraft connection has not been established"}),
                400,
            )

    return wrap


# sets and establishes a mavlink connection
@aircraft.route("/connect", methods=["POST"])
def aircraft_connect():
    connectionRequest = request.json

    if "ipAddress" not in connectionRequest:
        return jsonify({"error": "IP address was not specified"}), 401

    if "port" not in connectionRequest:
        return jsonify({"error": "Port was not specified"}), 402

    # set the ip address and port to the aircraft
    ip_address = connectionRequest["ipAddress"]
    port = connectionRequest["port"]

    # initialize the mavlink connection
    setup_mavlink_connection(ip_address, port)

    return jsonify({"msg": "Connected to the aircraft successfully"}), 201


# Receives an array of waypoints
# Interrupts aircraft auto mode, switches to guided, runs waypoints, then returns to auto
@aircraft.route("/reroute", methods=["POST"])
@connection_required
def aircraft_reroute():
    json = request.json
    points = json["waypoints"]
    vehicle.reroute(points)
    return aircraft_gps()


# Arms the aircraft
@aircraft.route("/arm", methods=["PUT"])
@connection_required
def aircraft_arm():
    vehicle.arm()
    return aircraft_heartbeat()[0], 201


# Disarms the aircraft
@aircraft.route("/disarm", methods=["PUT"])
@connection_required
def aircraft_disarm():
    vehicle.disarm()
    return aircraft_heartbeat()[0], 201


# Returns status of the aircraft
@aircraft.route("/arm", methods=["get"])
@connection_required
def aircraft_isarmed():
    return jsonify(vehicle.telemetry.is_armed()), 200


# RTL
@aircraft.route("/rtl", methods=["PUT"])
@connection_required
def aircraft_rtl():
    vehicle.mavlink_connection.set_mode_rtl()
    return aircraft_heartbeat()


# set mode manual
@aircraft.route("/manual", methods=["PUT"])
@connection_required
def aircraft_manual():
    vehicle.mavlink_connection.set_mode_manual()
    return aircraft_heartbeat()


# set mode to auto
@aircraft.route("/auto", methods=["PUT"])
@connection_required
def aircraft_auto():
    vehicle.mavlink_connection.set_mode_auto()
    return aircraft_heartbeat()


# set mode to guided
@aircraft.route("/guided", methods=["PUT"])
@connection_required
def aircraft_guided():
    vehicle.mavlink_connection.set_mode("GUIDED")
    return aircraft_heartbeat()


# set mode to loiter
@aircraft.route("/loiter", methods=["PUT"])
@connection_required
def aircraft_loiter():
    vehicle.mavlink_connection.set_mode_loiter()
    return aircraft_heartbeat()


# Request flight mode
@aircraft.route("/telemetry/flightmode", methods=["GET"])
@connection_required
def aircraft_flightmode():
    flightmode = vehicle.mavlink_connection.flightmode
    return jsonify({"flightmode": flightmode}), 200


# Request gps data
@aircraft.route("/telemetry/gps", methods=["GET"])
@connection_required
def aircraft_gps():
    location = vehicle.telemetry.get_location()
    return jsonify(location), 200


@aircraft.route("/telemetry/gps_with_timestamp", methods=["GET"])
@connection_required
def aircraft_gps_with_timestamp():
    location = vehicle.telemetry.get_location()
    # the timestamp is specifically for SkyPasta which requires a timestamp to be given along with the telemetry data
    location['timestamp'] = int(time.time())  # get the current unix timestamp
    return jsonify(location), 200


# Request heartbeat data
@aircraft.route("/telemetry/heartbeat", methods=["GET"])
@connection_required
def aircraft_heartbeat():
    vehicle.telemetry.wait("HEARTBEAT")
    return jsonify(vehicle.telemetry.heartbeat.to_dict()), 200


# Guided control / Fly-to
@aircraft.route("/flyto", methods=["POST"])
@connection_required
def aircraft_flyto(lat=0, lng=0, alt=0):
    lat = parseRequest(request, "lat", lat)
    lng = parseRequest(request, "lng", lng)
    alt = parseRequest(request, "alt", alt)
    vehicle.fly_to(lat, lng, alt)
    return aircraft_heartbeat()


# Guided control / Take-off
@aircraft.route("/takeoff", methods=["POST"])
@connection_required
def aircraft_takeoff():
    vehicle.mavlink_connection.mav.command_long_send(
        vehicle.mavlink_connection.target_system,
        vehicle.mavlink_connection.target_component,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
        0,
        parseRequest(request, "pitch", 0),
        0,
        0,
        parseRequest(request, "yaw", 0),
        parseRequest(request, "lat", 0),
        parseRequest(request, "lng", 0),
        parseRequest(request, "alt", 0),
    )
    return aircraft_heartbeat()


@aircraft.route("/home_position", methods=["GET"])
@connection_required
def aircraft_home_position():
    vehicle.mavlink_connection.mav.command_long_send(
        vehicle.mavlink_connection.target_system,
        vehicle.mavlink_connection.target_component,
        mavutil.mavlink.MAV_CMD_REQUEST_MESSAGE,
        242,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
    )
    msg = vehicle.telemetry.wait("HOME_POSITION")

    return jsonify(
        {
            "lat": msg.latitude,
            "lng": msg.longitude,
            "alt": msg.altitude,
            "x": msg.x,
            "y": msg.y,
            "z": msg.z,
            "q": msg.q,
            "approach_x": msg.approach_x,
            "approach_y": msg.approach_y,
            "approach_z": msg.approach_z,
        }
    ), 200


# upload mission waypoints
@aircraft.route("/mission", methods=["POST"])
@connection_required
def upload_mission_wps():
    missionRequest = request.json
    # error checking
    if missionRequest:
        if "wps" not in missionRequest or not missionRequest["wps"]:
            return jsonify({"error": "No waypoints were given"}), 402

        if "takeoffAlt" not in missionRequest:
            return jsonify({"error": "Takeoff altitude was not given"}), 403
        elif missionRequest["takeoffAlt"] <= 0:
            return jsonify({"error": "Takeoff altitude must be >0"}), 404
    else:
        return jsonify({"error": "Mission format is invalid"}), 405

    # checks the number of wps recieved vs the number sent
    try:
        num_wps_loaded = vehicle.waypoints.upload_mission_wps(
            missionRequest["wps"], missionRequest["takeoffAlt"], missionRequest["rtl"]
        )
        return (
            jsonify(
                {
                    "result": "Waypoints uploaded successfully!",
                    "wps_uploaded": num_wps_loaded,
                }
            ),
            201,
        )
    except Exception as e:
        traceback.print_exception(*sys.exc_info())
        return jsonify({"error": "Waypoints failed to upload."}), 401


# download mission waypoints
@aircraft.route("/mission", methods=["GET"])
@connection_required
def download_mission_wps():
    data = vehicle.waypoints.download_mission_wps()
    return jsonify(data), 200


# Ensure mavlink connection is created before sending requests
def setup_mavlink_connection(ip_address, port):
    if "development" not in current_app.config["MAVLINK_SETUP_DEBUG"]:
        try:
            vehicle.setup_mavlink_connection('tcp', ip_address, port)
        except Exception:
            abort(400, "Mavlink is not connected")


@aircraft.route("/winchstatus", methods=["GET"])
@connection_required
def get_winch_status():
    data = vehicle.winch_status
    return jsonify({"winch_status": data}), 200


@aircraft.route("/winch/command", methods=["POST"])
@connection_required
def send_winch_command():
    vehicle.winch_status = 5
    return jsonify({"command": 5}), 200
