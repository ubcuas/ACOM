from flask import current_app, abort
from datetime import datetime
import time
import json
from pymavlink import mavutil
import math
import threading

from src.library.util import get_distance_metres, get_point_further_away, get_degrees_needed_to_turn, empty_socket
import src.library.telemetry
from src.library.location import Location
from src.library.waypoints import Waypoints
from src.library.arduinoconnector import ArduinoConnector

from pytimedinput import timedInput
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Testing environment
# GCOM_TELEMETRY_ENDPOINT = "http://host.docker.internal:8080/api/interop/telemetry"

# Production environment
GCOM_TELEMETRY_ENDPOINT = "http://51.222.12.76:61633/api/interop/telemetry"

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
        self.reroute_thread = None
        self.mavlink_connection = None
        self.telemetry = None
        self.waypoint_loader = None
        self.connecting = False

        # For tracking when to pause logs (when input is required for battery_rtl)
        self.pause_logs = False
        # To store logs while they are paused
        self.store_important_logs = []

        # For exiting threads that don't need to keep running in the case of RTL from the battery
        self.returning_home = False
        # Rover status to make sure drop is completed before rtl
        self.winch_status = 0

    # Threaded: Continuously post telemetry data to GCOM-X
    def post_to_gcom(self):
        while True:
            try:
                location = vehicle.get_location()

                http = requests.Session()
                retry = Retry(total=None, backoff_factor=1)
                adapter = HTTPAdapter(max_retries=retry)
                http.mount('http://', adapter)

                gcom_telemetry_post = http.post(
                    GCOM_TELEMETRY_ENDPOINT,
                    headers={'content-type': 'application/json',
                             'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X x.y; rv:42.0) Gecko/20100101 Firefox/42.0'},
                    data=json.dumps({
                        "latitude_dege7":  location["lat"]*10**7,
                        "longitude_dege7": location["lng"]*10**7,
                        "altitude_msl_m":  location["alt"],
                        "heading_deg":     vehicle.get_heading(),
                        "groundspeed_m_s": vehicle.get_speed(),
                        "chan3_raw":       vehicle.get_rc_channel()
                    }),
                    timeout=3
                )

                if gcom_telemetry_post.status_code == 200:
                    if self.pause_logs == False:
                        print("[OK]       GCOM-X Telemetry  POST")
                else:
                    if self.pause_logs == False:
                        print("[FAIL]     GCOM-X Telemetry  POST: " +
                              str(gcom_telemetry_post.status_code))
                    else:
                        self.store_important_logs.append(
                            "[FAIL]     GCOM-X Telemetry  POST: " + str(gcom_telemetry_post.status_code))

            except Exception as e:
                if self.pause_logs == False:
                    print(
                        "[ERROR]    GCOM-X Telemetry  Exception encountered: " + str(e))
                else:
                    self.store_important_logs.append(
                        "[ERROR]    GCOM-X Telemetry  Exception encountered: " + str(e))

            time.sleep(0.1)

    # Threaded: For tracking RC connection and RTL when disconnected for 30s
    def rc_disconnect_monitor(self):
        disconnect_timer = False
        rc_threshold = 975
        rtl_time_limit = 30  # 30s buffer from rc disconnect
        kill_time_limit = 180 # 180s buffer (3 min)
        return_triggered = False

        while True:
            # See details in variable declaration above
            if self.returning_home:
                return

            # Get RC signal
            channel = vehicle.get_rc_channel()
            # Initiate an initial value if less than threshold
            if channel < rc_threshold and disconnect_timer == False:
                disconnect_timer = True
                orig_time = datetime.now()
                time.sleep(2)
                print("[ALERT]    RC Connection     Lost!")
            # Compare initial time to current if still disconnected
            elif channel < rc_threshold and disconnect_timer:
                curr_time = datetime.now()
                print("[ALERT]    RC Connection     Disconnected:", round(
                    (curr_time - orig_time).total_seconds(), 1), "s")
                # Drop out of the sky if RC disconnect for more than 180s (3 min)
                if (curr_time - orig_time).total_seconds() > kill_time_limit:
                    vehicle.terminate()
                    print("[ALERT]    RC Connection     FLIGHT TERMINATED!")
                # RTL if RC disconnect for more than 30s
                elif (curr_time - orig_time).total_seconds() > rtl_time_limit and return_triggered == False:
                    # Don't RTL while winch is in progress
                    if self.winch_status == 2 or self.winch_status == 3 or self.winch_status == 5:
                        # Indicate to Arduino function that we need to emergency reel
                        self.winch_status = 5
                    vehicle.set_rtl()
                    print(
                        "[EXPIRED]  RC Connection     Aircraft returning home to land!")
                    return_triggered = True
            else:
                # Reset timer if above threshold
                disconnect_timer = False
                # If in RTL mode from RC disconnect set to loiter
                if vehicle.mavlink_connection.flightmode == "RTL" and return_triggered:
                    return_triggered = False
                    vehicle.set_loiter()
                if self.pause_logs == False:
                    print("[OK]       RC Connection")
            time.sleep(0.5)

    # Threaded: For tracking flight time and RTL after 20 min (with the option to extend)
    def battery_rtl(self):
        takeoff_time = datetime.now()  # Initial time
        time_threshold = 1200  # 20 minutes in seconds

        while True:
            curr_time = datetime.now()  # Set current time
            time_delta = (curr_time - takeoff_time).total_seconds()
            if self.pause_logs == False:
                print("[OK]       Battery           Time since start: ", int(
                    time_delta // 60), "min", round(time_delta % 60), "s")

            # If flying for longer than the threshold then RTL
            if (curr_time - takeoff_time).total_seconds() > time_threshold:
                print("[CRITICAL] Battery           20 minute timer reached!")
                self.pause_logs = True  # Pause other logs to read terminal input
                print(
                    "-------------------------------------------------------------------------------")
                # Timed input entry https://pypi.org/project/pytimedinput/
                choice, timedOut = timedInput(
                    "[CRITICAL] Battery          Do you want to extend the flight by 2 min (y/n)? ", 60, False, 3)
                if timedOut == False and (choice.lower() == "y" or choice.lower() == "yes"):
                    time_threshold += 120
                    print(
                        "--------------------------------- STORED LOGS ---------------------------------")
                    for log in self.store_important_logs:
                        print(log)
                    self.store_important_logs.clear()
                    print(
                        "-------------------------------------------------------------------------------")
                    self.pause_logs = False
                else:
                    self.returning_home = True
                    while self.winch_status == 2 or self.winch_status == 3:
                        pass
                    vehicle.set_rtl()
                    print(
                        "-------------------------------------------------------------------------------")
                    print("[CRITICAL] Battery           Returning to land")
                    print(
                        "--------------------------------- STORED LOGS ---------------------------------")
                    for log in self.store_important_logs:
                        print(log)
                    self.store_important_logs.clear()
                    print(
                        "-------------------------------------------------------------------------------")
                    self.pause_logs = False
                    return
            time.sleep(1)

    # Threaded: Gets the target winch drop-off and initiates drop automatically when the drone reaches that position
    def winch_automation(self):
        arduino = None

        while arduino == None:
            try:
                arduino = ArduinoConnector(self)
                print("[ALERT]    Rover & Winch     Arduino initialized")
                self.winch_status = 1
            except Exception as ex:
                if self.pause_logs == False:
                    print("[ERROR]    Rover & Winch    ", ex)
                else:
                    self.store_important_logs.append(
                        "[ERROR]    Rover & Winch    " + str(ex))
            time.sleep(1)

        # Initialize target location
        target = Location(0, 0, 0)

        # Repeatedly look for target location in ACOM's waypoints, continue once found
        while target.lat == 0 and target.lng == 0 and target.alt == 0:
            target = Location(
                self.waypoints.airdrop["lat"], self.waypoints.airdrop["lng"], self.waypoints.airdrop["alt"])
            if self.pause_logs == False:
                print("[ALERT]    Rover & Winch     Waiting for target position")
            time.sleep(1)
        print("[ALERT]    Rover & Winch     Target position found!")

        allowed_radius = 4  # Radius acceptable from target location

        while True:
            # See details in returning_home declaration above
            # Only exit if the drop has not yet started
            if self.returning_home and (self.winch_status == 1 or self.winch_status == 4):
                return
            # If emergency reel status initiated then send command and change status
            if self.winch_status == 5:
                arduino.sendCommandMessage("AIRDROPCANCEL1")
                self.winch_status = 1
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
                if self.pause_logs == False:
                    print("[OK]       Rover & Winch     Distance from target: ", round(
                        dist, 2), "m")
                # Initiate commands if within the target drop location radius
                if dist < allowed_radius:
                    # Loiter the drone
                    vehicle.set_loiter()
                    print(
                        "[ALERT]    Rover & Winch     In target distance; Loitering")

                    # Send “AIRDROPBEGIN1” to the winch
                    self.winch_status == 1
                    arduino.sendCommandMessage("AIRDROPBEGIN1")
                    print("[START]    Rover & Winch     Starting deployment")

                    # Wait for winch to return “AIRDROPCOMPLETE”
                    arduino.listenSuccessMessage()
                    print("[FINISH]   Rover & Winch     Task completed")

                    # Return to the mission in auto mode
                    vehicle.set_auto()
                    self.winch_status == 4
                    return
            except Exception as e:
                print("[ERROR]    Rover & Winch     Function failure: ", e)
            time.sleep(0.1)

    def setup_mavlink_connection(self, connection, address, port=None, baud=57600):
        if self.mavlink_connection == None or self.mavlink_connection.target_system < 1 and not self.connecting:
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
                rc_disconnect_monitor_thread = threading.Thread(
                    target=self.rc_disconnect_monitor, daemon=True)
                rc_disconnect_monitor_thread.start()
                battery_rtl_thread = threading.Thread(
                    target=self.battery_rtl, daemon=True)
                battery_rtl_thread.start()
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
        self.reroute_thread

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
