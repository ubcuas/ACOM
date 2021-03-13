from observable import Observable
from pymavlink import mavutil
from threading import Thread
import time
import socket

from src.library.util import empty_socket


class Telemetry:
    def __init__(self, vehicle):
        """
        Initializes telemetry data streams, observers, and listens to every incoming
        message from the autopilot

        Args:
            vehicle (vehicle): vehicle instance
        """
        self.verbose = False  # prints all incoming messages

        self.vehicle = vehicle
        self.mavlink_connection = vehicle.mavlink_connection
        self.init_data_streams()

        # data
        self.lat = None
        self.lng = None
        self.alt = None
        self.heading = None

        self.heartbeat = None

        self.mav_type = None
        self.base_mode = None
        self.armed = False

        self.is_polling = False

        self.start_polling()  # this is to log & poll for all data coming from autopilot

    def get_location(self):
        return {
            "lat": self.lat,
            "lng": self.lng,
            "alt": self.alt,
            "heading": self.heading,
        }

    def is_armed(self):
        return self.armed

    def wait_armed(self, expected, timeout=None):
        start_time = time.time()
        while True:
            if timeout is not None:
                now = time.time()
                if now < start_time:
                    # If an external process rolls back system time, we should not spin forever.
                    start_time = now
                if start_time + timeout < time.time():
                    return
            if self.armed == expected:
                return

            time.sleep(0.05)

    def start_polling(self):
        print("Starting polling...")
        self.heartbeat_lastsent = time.monotonic()
        self.event = Observable()
        self.notifiers = Observable()
        self.init_observers()
        self.thread = Thread(target=self.poll_for_data, daemon=True)
        self.thread.start()
        self.is_polling = True

    def init_data_streams(self):
        """
        Initializes message requests at a specific frequency
        """
        self.set_message_interval(24, 10)  # gps
        self.set_message_interval(0, 10)  # heartbeat
        self.set_message_interval(74, 10)  # vfr_hud
        self.set_message_interval(33, 10)  # gps

    def wait(self, msg_type, timeout=None):
        """
        blocks until a specific msg_type is received, and returns it. if timeout
        is specified and is reached, returns None

        Args:
            msg_type (string): mavlink message
            timeout (number, optional): timeout in seconds. Defaults to None.
        """
        if self.is_polling:
            result = None

            def callback(msg):
                nonlocal result
                # ignore groundstations for heartbeat
                if (
                    msg.get_type() == "HEARTBEAT"
                    and msg.type == mavutil.mavlink.MAV_TYPE_GCS
                ):
                    self.notifiers.once(msg_type, callback)
                    return
                result = msg

            self.notifiers.once(msg_type, callback)

            start_time = time.time()
            while True:
                if timeout is not None:
                    now = time.time()
                    if now < start_time:
                        # If an external process rolls back system time, we should not spin forever.
                        start_time = now
                    if start_time + timeout < time.time():
                        return None
                if result is not None:
                    return result
                time.sleep(0.05)

        else:
            # not polling
            return self.mavlink_connection.recv_match(
                type=[msg_type], timeout=timeout, blocking=True
            )

    def init_observers(self):
        """
        Initializes observers. These functions are called when a message has been recieved.

        example:
        @self.event.on('GPS_RAW_INT')
        def listener(msg):
            print(msg)
        """

        @self.event.on("HEARTBEAT")
        def hb_listener(msg):
            # ignore groundstations
            if msg.type == mavutil.mavlink.MAV_TYPE_GCS:
                return

            self.heartbeat = msg

            self.mav_type = msg.type
            self.base_mode = msg.base_mode
            self.armed = (
                msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
            ) != 0

        @self.event.on("GLOBAL_POSITION_INT")
        def gpi_listener(msg):
            return

        @self.event.on("VFR_HUD")
        def vfr_listener(msg):
            self.alt = msg.alt
            self.heading = msg.heading

        @self.event.on("GPS_RAW_INT")
        def gps_kistener(msg):
            self.lat = msg.lat * 1.0e-7
            self.lng = msg.lon * 1.0e-7

    # set a message interval for a specific mavlink message
    def set_message_interval(self, messageid, interval):
        """
        requests message from autopilot at a specific interval (in hz)

        Args:
            messageid (number): mavlink message id
            interval (number): frequency of message in hz
        """
        milliseconds = 0
        if interval == -1:
            milliseconds = -1
        elif interval > 0:
            milliseconds = 1000000 / interval

        self.mavlink_connection.mav.command_long_send(
            self.mavlink_connection.target_system,
            self.mavlink_connection.target_component,
            mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL,
            0,
            messageid,  # message id
            int(milliseconds),  # interval in us
            0,
            0,
            0,
            0,
            0,
        )

    def poll_for_data(self):
        """
        polls for any data from the autopilot. when recieved, triggers an event that
        notifies all observers listening to that specific msg type

        Raises:
            Exception: various exceptions
        """
        try:
            while True:
                # send heartbeat to autopilot
                if time.monotonic() - self.heartbeat_lastsent > 1:
                    self.mavlink_connection.mav.heartbeat_send(
                        mavutil.mavlink.MAV_TYPE_GCS,
                        mavutil.mavlink.MAV_AUTOPILOT_INVALID,
                        0,
                        0,
                        0,
                    )
                    self.heartbeat_lastsent = time.monotonic()

                # Sleep
                self.mavlink_connection.select(0.05)

                while True:
                    try:
                        # try to get message
                        msg = self.mavlink_connection.recv_msg()
                    except socket.error as error:
                        raise
                    except mavutil.mavlink.MAVError as e:
                        # Avoid
                        #   invalid MAVLink prefix '73'
                        #   invalid MAVLink prefix '13'
                        print("mav recv error: %s" % str(e))
                        msg = None
                    except Exception as e:
                        # Log any other unexpected exception
                        print("Exception while receiving message: ")
                        print(e)
                        msg = None
                    if not msg:
                        # no message, restart polling loop
                        break

                    if self.verbose:
                        print(msg.get_type() + " recieved")
                    self.event.trigger(msg.get_type(), msg)
                    self.notifiers.trigger(msg.get_type(), msg)

        except Exception as e:
            print("Exception in MAVLink input loop")
            print(e)
            return
