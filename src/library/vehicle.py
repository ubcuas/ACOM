import json
import threading
import time

import requests
from flask import current_app
from pymavlink import mavutil
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

import src.library.telemetry
from src.library.arduinoconnector import ArduinoConnector
from src.library.location import Location
from src.library.util import get_distance_metres, get_point_further_away, get_degrees_needed_to_turn
from src.library.waypoints import Waypoints

with open('config.json', 'r') as f:
    config = json.load(f)

GCOM_TELEMETRY_ENDPOINT = config["setup"]["GCOMEndpoint"]

"""
Winch status
0 - Disconnected
1 - Standby
2 - In Progress
3 - Error
4 - Complete
5 - Emergency Reel
"""


class Vehicle:
    def __init__(self):
        self.waypoints = None
        self.reroute_thread = None
        self.mavlink_connection = None
        self.telemetry = None
        self.waypoint_loader = None
        self.connecting = False
        self.winch_enabled = config["winch"]["winchEnable"]

        # Rover status to make sure drop is completed before rtl
        self.winch_status = 0

        # locks to prevent race conditions between post_to_gcom thread and winch_automation changing winch_status
        self.lock = threading.Lock()

    # Threaded: Continuously post telemetry data to GCOM-X
    def post_to_gcom(self):
        while True:
            try:
                location = vehicle.get_location()

                http = requests.Session()
                retry = Retry(total=None, backoff_factor=1)
                adapter = HTTPAdapter(max_retries=retry)
                http.mount('http://', adapter)

                self.lock.acquire()
                json_data = json.dumps({
                    "latitude_dege7":  location["lat"]*10**7,
                    "longitude_dege7": location["lng"]*10**7,
                    "altitude_msl_m":  location["alt"],
                    "heading_deg":     vehicle.get_heading(),
                    "groundspeed_m_s": vehicle.get_speed(),
                    "chan3_raw":       vehicle.get_rc_channel(),
                    "winch_status":    self.winch_status
                })

                gcom_telemetry_post = http.post(
                    GCOM_TELEMETRY_ENDPOINT,
                    headers={'content-type': 'application/json',
                             'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X x.y; rv:42.0) Gecko/20100101 Firefox/42.0'},
                    data=json_data,
                    timeout=3
                )

                if gcom_telemetry_post.status_code == 200:
                    print("[OK]       GCOM-X Telemetry  POST")
                else:
                    print("[FAIL]     GCOM-X Telemetry  POST: " +
                          str(gcom_telemetry_post.status_code))

                self.lock.release()


            except Exception as e:
                print(
                    "[ERROR]    GCOM-X Telemetry  Exception encountered: " + str(e))

            time.sleep(0.1)

    # Threaded: Gets the target winch drop-off and initiates drop automatically when the drone reaches that position
    def winch_automation(self):
        if self.winch_enabled:
            arduino = None
            
            while arduino is None:
                try:
                    arduino = ArduinoConnector(self)
                    print("[ALERT]    Rover & Winch     Arduino initialized")
                    self.lock.acquire()
                    self.winch_status = 1
                    self.lock.acquire()
                except Exception as ex:
                    print("[ERROR]    Rover & Winch    ", ex)

                time.sleep(1)

            # Initialize target location
            target = Location(0, 0, 0)

            # Repeatedly look for target location in ACOM's waypoints, continue once found
            while target.lat == 0 and target.lng == 0 and target.alt == 0:
                target = Location(
                    self.waypoints.airdrop["lat"], self.waypoints.airdrop["lng"], self.waypoints.airdrop["alt"])
                print("[ALERT]    Rover & Winch     Waiting for target position")
                time.sleep(1)
            print("[ALERT]    Rover & Winch     Target position found!")

            # Radius acceptable from target location, change in config.json file
            allowed_radius = config["winch"]["allowedRadius"]

            while True:
                # See details in returning_home declaration above
                # Only exit if the drop has not yet started
                if self.winch_status == 1 or self.winch_status == 4:
                    return
                # If emergency reel status initiated then send command and change status
                if self.winch_status == 5:
                    arduino.sendCommandMessage("AIRDROPCANCEL1")
                    self.lock.acquire()
                    self.winch_status = 1
                    self.lock.release()
                # Get drone location
                try:
                    location = vehicle.get_location()
                except:
                    print("[ERROR]    Rover & Winch     Failed to get location")
                try:
                    # Compare current location to fetched drop location
                    curr_loc = Location(
                        location["lat"], location["lng"], location["alt"])
                    dist = get_distance_metres(target, curr_loc)
                    print("[OK]       Rover & Winch     Distance from target: ", round(
                        dist, 2), "m")
                    # Initiate commands if within the target drop location radius
                    if dist < allowed_radius:
                        # Loiter the drone
                        vehicle.set_loiter()
                        print(
                            "[ALERT]    Rover & Winch     In target distance; Loitering")

                        # Send “AIRDROPBEGIN1” to the winch
                        self.lock.acquire()
                        self.winch_status = 1
                        self.lock.release()

                        arduino.sendCommandMessage("AIRDROPBEGIN1")
                        print("[START]    Rover & Winch     Starting deployment")

                        # Wait for winch to return “AIRDROPCOMPLETE”
                        arduino.listenSuccessMessage()
                        print("[FINISH]   Rover & Winch     Task completed")

                        # Return to the mission in auto mode
                        vehicle.set_auto()
                        self.lock.acquire()
                        self.winch_status = 4
                        self.lock.release()

                        return
                except Exception as e:
                    print("[ERROR]    Rover & Winch     Function failure: ", e)
                time.sleep(0.1)
        else:
            print("[ALERT]    Rover & Winch     Winch disabled")
            return


    def setup_mavlink_connection(self, connection, address, port=None, baud=57600):
        if self.mavlink_connection is None or self.mavlink_connection.target_system < 1 and not self.connecting:
            self.connecting = True
            current_app.logger.info(
                "Mavlink connection is now being initialized")
            if connection == "tcp":
                self.mavlink_connection = mavutil.mavlink_connection(
                    connection + ':' + address + ':' + str(port))
            elif connection == "serial":
                self.mavlink_connection = mavutil.mavlink_connection(
                    address, baud=baud)
            else:
                raise Exception("Invalid connection type")
            self.mavlink_connection.wait_heartbeat(timeout=5)
            current_app.logger.info("Heartbeat from system (system %u component %u)" % (
                self.mavlink_connection.target_system, self.mavlink_connection.target_component))
            # init telemetry
            self.telemetry = src.library.telemetry.Telemetry(self)

            # init waypoints
            self.waypoints = Waypoints(self)

            # connection established, vehicle initialized
            # begin eternally posting telemetry to GCOM
            # via an eternal thread
            with current_app.app_context():
                post_to_gcom_thread = threading.Thread(
                    target=self.post_to_gcom, daemon=True)
                post_to_gcom_thread.start()
                winch_automation_thread = threading.Thread(
                    target=self.winch_automation, daemon=True)
                winch_automation_thread.start()

        if self.mavlink_connection.target_system < 1:
            raise Exception("Mavlink is not connected")

    def disconnect(self):
        if self.mavlink_connection is not None:
            self.mavlink_connection.close()

    def is_connected(self):
        return self.mavlink_connection is not None

    def arm(self):
        self.mavlink_connection.arducopter_arm()

    def disarm(self):
        self.mavlink_connection.arducopter_disarm()

    def set_guided(self):
        self.mavlink_connection.set_mode('GUIDED')

    def set_auto(self):
        self.mavlink_connection.set_mode('AUTO')

    def set_rtl(self):
        vehicle.mavlink_connection.set_mode('RTL')

    def set_loiter(self):
        vehicle.mavlink_connection.set_mode('LOITER')

    def set_pos_hold(self):
        vehicle.mavlink_connection.set_mode('POS_HOLD')

    def terminate(self):
        vehicle.mavlink_connection.mav.command_long_send(
            vehicle.mavlink_connection.target_system,
            vehicle.mavlink_connection.target_component,
            mavutil.mavlink.MAV_CMD_DO_FLIGHTTERMINATION,
            0,
            1,
            0,
            0,
            0,
            0,
            0,
            0,
        )

    def reroute(self, points):
        self.reroute_thread = threading.Thread(
            target=self.start_reroute, args=[points], daemon=True)
        self.reroute_thread.start()

    def stop_reroute(self):
        self.reroute_thread.kill()

    def get_location(self):
        self.telemetry.wait('GPS_RAW_INT')
        self.telemetry.wait('GLOBAL_POSITION_INT')
        return Location(self.telemetry.lat,
                        self.telemetry.lng,
                        self.telemetry.alt).__dict__

    def get_speed(self):
        self.telemetry.wait('VFR_HUD')
        return self.telemetry.groundspeed

    def get_heading(self):
        self.telemetry.wait('GLOBAL_POSITION_INT')
        return self.telemetry.heading

    def get_rc_channel(self):
        self.telemetry.wait('RC_CHANNELS_RAW')
        return self.telemetry.chan3_raw

    def fly_to(self, lat, lng, alt):
        frame = mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT
        self.mavlink_connection.mav.mission_item_send(0, 0, 0, frame,
                                                      mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                                                      2,  # current wp - guided command
                                                      0,
                                                      0,
                                                      0,
                                                      0,
                                                      0,
                                                      lat,
                                                      lng,
                                                      alt
                                                      )

    def start_reroute(self, points):
        self.set_guided()
        for index, point in enumerate(points):
            # if a new reroute task has been started, exit this one
            if threading.get_ident() != self.reroute_thread.ident:
                print("Reroute task cancelled")
                return

            lat = point["lat"]
            lng = point["lng"]
            alt = point["alt"]

            gps_data = self.get_location()
            current_location = Location(
                gps_data['lat'], gps_data['lng'], gps_data['alt'])

            target_location = Location(lat, lng, alt)
            sharp_turn = get_degrees_needed_to_turn(
                self.get_heading(), current_location, target_location) > 80

            overShootLocation = get_point_further_away(
                current_location, target_location, 40)
            overshoot_lat = overShootLocation.lat
            overshoot_lng = overShootLocation.lng
            overshoot_alt = overShootLocation.alt

            print("Rerouting to : " + str(target_location))

            # if the current point is the last point or a sharpturn, fly to that location, otherwise overshoot
            # if index == len(points) - 1 or sharp_turn:
            #     self.fly_to(target_location.lat, target_location.lng, target_location.alt)
            # else:
            #     self.fly_to(overshoot_lat, overshoot_lng, overshoot_alt)

            self.fly_to(target_location.lat,
                        target_location.lng, target_location.alt)

            while True:  # !!! TO-DO Change True to while vehicle is in guided mode
                # if a new reroute task has been started, exit this one
                if threading.get_ident() != self.reroute_thread.ident:
                    print("Reroute task cancelled")
                    return

                self.telemetry.wait('GPS_RAW_INT')
                current_location = Location(
                    self.telemetry.lat, self.telemetry.lng, self.telemetry.alt)

                remainingDistance = get_distance_metres(
                    current_location, target_location)
                print("Distance to target: " + str(remainingDistance))
                if remainingDistance <= 1:  # Just below target, in case of undershoot.
                    print("Reached waypoint")
                    break
        self.set_auto()


vehicle = Vehicle()
