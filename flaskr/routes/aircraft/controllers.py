from flask import Blueprint, request, jsonify, abort, Response, current_app
from pymavlink import mavutil, mavwp
from flaskr.library.util import parseRequest, parseJson
import json
import logging
import time
from functools import wraps

aircraft = Blueprint('aircraft', __name__)
mavlink_connection = None
waypoint_loader = None
ip_address = None
port = None

# decorator that checks if a mavlink connection has been established
def connection_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        global mavlink_connection, waypoint_loader
        
        if mavlink_connection is None or waypoint_loader is None:
            return jsonify({"error": "Aircraft connection has not been established"}), 400
        else:
            return f(*args, **kwargs)
   
    return wrap

# sets and establishes a mavlink connection
@aircraft.route('/connect', methods=['POST'])
def aircraft_connect():
    global ip_address, port

    connectionRequest = request.json

    if 'ipAddress' not in connectionRequest:
        return jsonify({"error": "IP address was not specified"}), 401
    
    if 'port' not in connectionRequest:
        return jsonify({"error": "Port was not specified"}), 402

    # set the ip address and port to the aircraft
    ip_address = connectionRequest['ipAddress']
    port = connectionRequest['port']

    # initialize the mavlink connection
    setup_mavlink_connection()

    return jsonify({"msg": "Connected to the aircraft successfully"}), 201

# Recieves an array of waypoints
# Interrupts aircraft auto mode, switches to guided, runs waypoints, then returns to auto
@aircraft.route('/reroute', methods=['POST'])
@connection_required
def aircraft_reroute():
    return request.data

# Arms the aircraft
@aircraft.route('/arm', methods=['PUT'])
@connection_required
def aircraft_arm():
    global mavlink_connection
    mavlink_connection.arducopter_arm()
    return aircraft_heartbeat()

# Disarms the aircraft
@aircraft.route('/disarm', methods=['PUT'])
@connection_required
def aircraft_disarm():
    global mavlink_connection
    mavlink_connection.arducopter_disarm()
    return aircraft_heartbeat()

# RTL
@aircraft.route('/rtl', methods=['PUT'])
@connection_required
def aircraft_rtl():
    global mavlink_connection
    mavlink_connection.set_mode_rtl()
    return aircraft_heartbeat()

# set mode manual
@aircraft.route('/manual', methods=['PUT'])
@connection_required
def aircraft_manual():
    global mavlink_connection
    mavlink_connection.set_mode_manual()
    return aircraft_heartbeat()

# set mode to auto
@aircraft.route('/auto', methods=['PUT'])
@connection_required
def aircraft_auto():
    global mavlink_connection
    mavlink_connection.set_mode_auto()
    return aircraft_heartbeat()

# set mode to guided
@aircraft.route('/guided', methods=['PUT'])
@connection_required
def aircraft_guided():
    global mavlink_connection
    mavlink_connection.set_mode('GUIDED')
    return aircraft_heartbeat()

# Request gps data
@aircraft.route('/telemetry/gps', methods=['GET'])
@connection_required
def aircraft_gps():
    global mavlink_connection
    location = mavlink_connection.location()
    return jsonify(location.__dict__), 201

# Request heartbeat data
@aircraft.route('/telemetry/heartbeat', methods=['GET'])
@connection_required
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
    return jsonify(hb_data), 201

# Guided control / Fly-to
@aircraft.route('/flyto', methods=['POST'])
@connection_required
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
@connection_required
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
@connection_required
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
        return jsonify({'error': 'Invalid message name'}), 401
    if msg.get_type() == "BAD_DATA":
        return jsonify({'error': 'Bad data retrieved'}), 402
    else:
        attributes = msg._fieldnames
        for attr in attributes:
            msg_data[attr] = getattr(msg, attr)

    # jsonify msg_data
    return jsonify(msg_data), 201

# upload mission waypoints
@aircraft.route('/mission', methods=['POST'])
@connection_required
def upload_mission_wps():
    global waypoint_loader
    global mavlink_connection

    # wp variables
    frame = mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT
    seqNum = 0
    waypoint_loader.clear()
    wpType = 0
    lat = 0
    lng = 0
    alt = 0

    # req body
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

    # stub home wp
    waypoint_loader.add(
        generate_mission_item(0, frame, mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 
            0, 0, 0, 0, 0
        )
    )
    seqNum += 1

    # takeoff wp
    waypoint_loader.add(
        generate_mission_item(seqNum, frame, mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 
            0, 0, 0, 0, parseJson(missionRequest, 'takeoffAlt', 0)
        )
    )
    seqNum += 1

    # load in wps
    for waypoint in missionRequest['wps']:   
        waypoint_loader.add(
            generate_mission_item(seqNum, frame, 
                mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 
                parseJson(waypoint, 'hold', 0),
                parseJson(waypoint, 'radius', 0),
                parseJson(waypoint, 'lat', 0), 
                parseJson(waypoint, 'lng', 0), 
                parseJson(waypoint, 'alt', 0)
            )
        )
        seqNum += 1       

    # is rtl enabled
    if missionRequest['rtl'] == True:
        waypoint_loader.add(
            generate_mission_item(seqNum, frame, 
                mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH, 
                0, 0, 0, 0, 0
            )
        )
        seqNum += 1           

    # mission wps loaded
    num_wps_loaded = waypoint_loader.count() - 2;
    if missionRequest['rtl']:
        num_wps_loaded -= 1;       

    # clear the current wps in the send queue and loads the new set
    mavlink_connection.waypoint_clear_all_send()                                     
    mavlink_connection.waypoint_count_send(waypoint_loader.count())                          

    # send wps 1 by 1
    for i in range(waypoint_loader.count()):               
        msg = mavlink_connection.recv_match(type=['MISSION_REQUEST'],blocking=True)             
        mavlink_connection.mav.send(waypoint_loader.wp(msg.seq))                                                                      
        # print('Sending waypoint %d', msg.seq)

    # get wp count received
    mavlink_connection.waypoint_request_list_send()
    count = int(mavlink_connection.recv_match(type=['MISSION_COUNT'],blocking=True).count)

    # checks the number of wps recieved vs the number sent
    if(count == waypoint_loader.count()):
        return jsonify({ "result": "Waypoints uploaded successfully!", "wps_uploaded": num_wps_loaded }), 201
    else:
        return jsonify({ "error": "Waypoints failed to upload." }), 401

# download mission waypoints
@aircraft.route('/mission', methods=['GET'])
@connection_required
def download_mission_wps():
    global waypoint_loader
    mavlink_connection.waypoint_request_list_send()

    count = None
    stored = None
    wps = []
    homePos = None
    takeoffAlt = None
    rtl = False

    while True:
        if count is None:
            try:
                count = mavlink_connection.recv_match(type='MISSION_COUNT', blocking=True, timeout=5).count
            except:
                count = None
                continue
            # print('Waypoint list request recieved waypoints', count)

            if count == 0:
                # print('Waypoint request transaction complete, 0 waypoints found')
                break
            mavlink_connection.waypoint_request_send(0)

        next_wp = mavlink_connection.recv_match(type='MISSION_ITEM', blocking=True, timeout=15)
        if next_wp is not None:
            # home position wp
            if next_wp.command == mavutil.mavlink.MAV_CMD_NAV_WAYPOINT and next_wp.seq == 0:
                homePos = {"lat": next_wp.x, "lng": next_wp.y, "alt": next_wp.z}
            
            # take off wp
            elif next_wp.command == mavutil.mavlink.MAV_CMD_NAV_TAKEOFF:
                takeoffAlt = next_wp.z
            
            # mission wps
            elif next_wp.command == mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH:
                rtl = True
            else:
                wp_json = {"lat": next_wp.x, "lng": next_wp.y, "alt": next_wp.z}
                wps.append(wp_json)

        if stored is None or (next_wp and stored.seq != next_wp.seq):
            stored = next_wp

        count -= 1
        if count == 0:
            # print('Waypoint request transaction complete')
            break
        # print('getting next waypoint: ', next_wp.seq + 1)
        mavlink_connection.waypoint_request_send(next_wp.seq + 1)
    
    return jsonify({ "homePos": homePos, "rtl": rtl, "takeoffAlt": takeoffAlt, "wps": wps}), 201

## Helpers

# Ensure mavlink connection is created before sending requests
def setup_mavlink_connection():
    global mavlink_connection, waypoint_loader, ip_address, port
    
    if 'development' not in current_app.config['MAVLINK_SETUP_DEBUG']:
        if mavlink_connection == None or mavlink_connection.target_system < 1:
            current_app.logger.info("Mavlink connection is now being initialized")
            mavlink_connection = mavutil.mavlink_connection('tcp:' + ip_address + ':' + str(port))
            mavlink_connection.wait_heartbeat(timeout=3)
            current_app.logger.info("Heartbeat from system (system %u component %u)" % (mavlink_connection.target_system, mavlink_connection.target_component))
            
            # request all data type streams
            mavlink_connection.mav.request_data_stream_send(mavlink_connection.target_system, mavlink_connection.target_component,
                                                    mavutil.mavlink.MAV_DATA_STREAM_ALL, 1, 1)
            
            # command data stream
            set_message_interval(24, 1) # gps
            set_message_interval(0, 1) # heartbeat

            # initialize waypointloader
            waypoint_loader = mavwp.MAVWPLoader(target_system=mavlink_connection.target_system, target_component=mavlink_connection.target_component)
        if mavlink_connection.target_system < 1:
            abort(400, "Mavlink is not connected")

# set a message interval for a specific mavlink message
def set_message_interval(messageid, interval):
    mavlink_connection.mav.command_long_send(
        mavlink_connection.target_system,
        mavlink_connection.target_component,
        mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL, 0,
        messageid, # message id
        interval, # interval us
        0,
        0,
        0,
        0,
        0
    )

# constructs a mavlink mission item
# returns MAVLink_mission_item_message
def generate_mission_item(seqNum, frame, wpType, hold, radius, lat, lng, alt):
    return mavutil.mavlink.MAVLink_mission_item_message(
        mavlink_connection.target_system,
        mavlink_connection.target_component,
        seqNum,
        frame,
        wpType,
        0, 0, 
        hold, 
        radius, # acceptance radius
        0, # pass radius
        0, # yaw
        lat,
        lng,
        alt
    )