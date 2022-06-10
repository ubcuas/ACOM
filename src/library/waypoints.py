from pymavlink import mavwp, mavutil
from src.library.util import parseJson


class Waypoints:
    def __init__(self, vehicle):
        """
        Initializes waypoint loading/downloading

        Args:
            vehicle (vehicle): vehicle instance
        """
        self.vehicle = vehicle
        self.mavlink_connection = vehicle.mavlink_connection
        self.waypoint_loader = mavwp.MAVWPLoader(
            target_system=self.mavlink_connection.target_system,
            target_component=self.mavlink_connection.target_component,
        )

        self.airdrop = {"lat": 0, "lng": 0, "alt": 0}

    def download_mission_wps(self):
        """Downloads the current mission waypoints"""
        self.mavlink_connection.waypoint_request_list_send()

        count = None
        stored = None
        wps = []
        homePos = None
        takeoffAlt = None
        rtl = False

        airdrop = self.airdrop

        while True:
            if count is None:
                try:
                    count = self.vehicle.telemetry.wait(
                        "MISSION_COUNT", timeout=5
                    ).count
                except:
                    count = None
                    continue
                # print('Waypoint list request recieved waypoints', count)

                if count == 0:
                    # print('Waypoint request transaction complete, 0 waypoints found')
                    break
                self.mavlink_connection.waypoint_request_send(0)

            next_wp = self.vehicle.telemetry.wait("MISSION_ITEM", timeout=5)
            if next_wp is not None:
                # home position wp
                if (
                    next_wp.command == mavutil.mavlink.MAV_CMD_NAV_WAYPOINT
                    and next_wp.seq == 0
                ):
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
            self.mavlink_connection.waypoint_request_send(next_wp.seq + 1)

        return {"homePos": homePos, "rtl": rtl, "takeoffAlt": takeoffAlt, "airdrop": airdrop, "wps": wps}

    def upload_mission_wps(self, waypoints, takeoffAlt, rtl):
        """Uploads the mission waypoints to the flight controller"""
        frame = mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT
        seqNum = 0
        self.waypoint_loader.clear()
        wpType = 0
        lat = 0
        lng = 0
        alt = 0

        # stub home wp
        self.waypoint_loader.add(
            self.generate_mission_item(
                0, frame, mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0, 0, 0, 0, 0
            )
        )
        seqNum += 1

        # takeoff wp
        self.waypoint_loader.add(
            self.generate_mission_item(
                seqNum,
                frame,
                mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
                0,
                0,
                0,
                0,
                takeoffAlt,
            )
        )
        seqNum += 1

        # load in wps
        for waypoint in waypoints:
            if waypoint["wp_type"] == "airdrop":
                self.airdrop["lat"] = waypoint["lat"]
                self.airdrop["lng"] = waypoint["lng"]
                self.airdrop["alt"] = waypoint["alt"]
            self.waypoint_loader.add(
                self.generate_mission_item(
                    seqNum,
                    frame,
                    mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                    parseJson(waypoint, "hold", 0),
                    parseJson(waypoint, "radius", 0),
                    parseJson(waypoint, "lat", 0),
                    parseJson(waypoint, "lng", 0),
                    parseJson(waypoint, "alt", 0),
                )
            )
            seqNum += 1

        # is rtl enabled
        if rtl == True:
            self.waypoint_loader.add(
                self.generate_mission_item(
                    seqNum,
                    frame,
                    mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH,
                    0,
                    0,
                    0,
                    0,
                    0,
                )
            )
            seqNum += 1

        # mission wps loaded
        num_wps_loaded = self.waypoint_loader.count() - 2
        if rtl:
            num_wps_loaded -= 1

        # clear the current wps in the send queue and loads the new set
        self.mavlink_connection.waypoint_clear_all_send()
        self.mavlink_connection.waypoint_count_send(self.waypoint_loader.count())

        # send wps 1 by 1
        for i in range(self.waypoint_loader.count()):
            msg = self.vehicle.telemetry.wait("MISSION_REQUEST", timeout=5)
            self.mavlink_connection.mav.send(self.waypoint_loader.wp(msg.seq))
            # print('Sending waypoint %d', msg.seq)

        # get wp count received
        self.mavlink_connection.waypoint_request_list_send()
        count = int(self.vehicle.telemetry.wait("MISSION_COUNT", timeout=5).count)

        if count == self.waypoint_loader.count():
            return num_wps_loaded
        else:
            raise Exception("Waypoints failed to upload.")

    def generate_mission_item(self, seqNum, frame, wpType, hold, radius, lat, lng, alt):
        return mavutil.mavlink.MAVLink_mission_item_message(
            self.mavlink_connection.target_system,
            self.mavlink_connection.target_component,
            seqNum,
            frame,
            wpType,
            0,
            0,
            hold,
            radius,  # acceptance radius
            0,  # pass radius
            0,  # yaw
            lat,
            lng,
            alt,
        )
