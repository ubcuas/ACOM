import pytest
import json
from unittest.mock import patch
from pymavlink import mavutil
from src.library.vehicle import Vehicle

home_position_endpoint = "/aircraft/home_position"


@patch("src.routes.aircraft.controllers.vehicle")
def test_premature_action(vehicle: Vehicle, app):
    vehicle.is_connected.return_value = False

    response = app.get(home_position_endpoint)

    # confirm failure - connection not established
    assert response.status_code == 400


@patch("src.routes.aircraft.controllers.vehicle")
def test_home_position_calls_correct_mavlink_command_and_returns_home_position(
    vehicle: Vehicle, app
):
    class MockHomePosition:
        def __init__(self):
            self.latitude = 1
            self.longitude = 2
            self.altitude = 3
            self.x = 0
            self.y = 0
            self.z = 0
            self.q = [0, 0, 0, 0]
            self.approach_x = 0
            self.approach_y = 0
            self.approach_z = 0

        def to_dict(self):
            return {
                "lat": self.latitude * 1.0e-7,
                "lng": self.longitude * 1.0e-7,
                "alt": self.altitude / 1000,
                "x": self.x,
                "y": self.y,
                "z": self.z,
                "q": self.q,
                "approach_x": self.approach_x,
                "approach_y": self.approach_y,
                "approach_z": self.approach_z,
            }

    test_home_position = MockHomePosition()
    vehicle.telemetry.wait.return_value = test_home_position

    response = app.get(home_position_endpoint)

    vehicle.mavlink_connection.mav.command_long_send.assert_called_with(
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

    assert response.status_code == 200
    assert json.loads(response.data) == test_home_position.to_dict()
