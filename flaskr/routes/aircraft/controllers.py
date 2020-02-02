from flask import Blueprint, request, jsonify, abort, Response, current_app
from pymavlink import mavutil, mavwp
from flaskr.library.util import parseRequest, parseJson
import json
import logging
import time

aircraft = Blueprint('aircraft', __name__)
mavlink_connection = None
waypoint_loader = None

# Ensure mavlink connection is created before sending requests
@aircraft.before_request
def setup_mavlink_connection():
    global mavlink_connection
    global waypoint_loader
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
            
            # command data stream
            set_message_interval(24, 1) # gps
            set_message_interval(0, 1) # heartbeat

            # initialize waypointloader
            waypoint_loader = mavwp.MAVWPLoader(target_system=mavlink_connection.target_system, target_component=mavlink_connection.target_component)
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

# upload mission waypoints
@aircraft.route('/mission/upload', methods=['POST'])
def upload_mission_wps():
    global waypoint_loader
    global mavlink_connection
    frame = mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT

    seq = 0
    waypoint_loader.clear()
    wpType = 0

    for waypoint in request.json:   
        # load home waypoint
        if seq == 0:
            wpType = mavutil.mavlink.MAV_CMD_NAV_WAYPOINT
        elif seq == 1:
            # take off waypoint
            wpType = mavutil.mavlink.MAV_CMD_NAV_TAKEOFF
        elif seq == (len(request.json) - 1):
            # rtl last waypoint
            wpType = mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH
        else:
            # default mission waypoints
            wpType = mavutil.mavlink.MAV_CMD_NAV_WAYPOINT

        waypoint_loader.add(
            mavutil.mavlink.MAVLink_mission_item_message(
                mavlink_connection.target_system,
                mavlink_connection.target_component,
                seq,
                frame,
                wpType,
                0, 0, 
                parseJson(waypoint, 'hold', 0), 
                parseJson(waypoint, 'radius', 0), # accept radius
                0, # pass radius
                0, # yaw
                parseJson(waypoint, 'lat', 0),
                parseJson(waypoint, 'lng', 0),
                parseJson(waypoint, 'alt', 0)
            )
        )
        seq += 1                                                       

    mavlink_connection.waypoint_clear_all_send()                                     
    mavlink_connection.waypoint_count_send(waypoint_loader.count())                          

    for i in range(waypoint_loader.count()):               
        msg = mavlink_connection.recv_match(type=['MISSION_REQUEST'],blocking=True)             
        mavlink_connection.mav.send(waypoint_loader.wp(msg.seq))                                                                      
        # print('Sending waypoint %d', msg.seq)

    mavlink_connection.waypoint_request_list_send()
    count = int(mavlink_connection.recv_match(type=['MISSION_COUNT'],blocking=True).count)

    # count recieved == count sent
    if(count == waypoint_loader.count()):
        return jsonify({ "msg": "Waypoints uploaded successfully!", "wps_uploaded": waypoint_loader.count() }), 201
    else:
        return jsonify({ "msg": "Waypoints failed to upload." }), 401

# download mission waypoints
@aircraft.route('/mission/download', methods=['GET'])
def download_mission_wps():
    global waypoint_loader
    mavlink_connection.waypoint_request_list_send()

    count = None
    stored = None
    wps = []

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
            wp_json = {"lat": next_wp.x, "lng": next_wp.y, "alt": next_wp.z}
            print(wp_json)
            wps.append(wp_json)

        if stored is None or (next_wp and stored.seq != next_wp.seq):
            stored = next_wp

        count -= 1
        if count == 0:
            # print('Waypoint request transaction complete')
            break
        # print('getting next waypoint: ', next_wp.seq + 1)
        mavlink_connection.waypoint_request_send(next_wp.seq + 1)
    
    return jsonify({ "wps": wps}), 200

## Helpers
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