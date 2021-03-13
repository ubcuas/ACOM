import pytest
import json
from unittest.mock import patch
from pymavlink import mavutil


home_position_endpoint = "/aircraft/home_position"


@patch("src.routes.aircraft.controllers.vehicle")
def test_premature_action(vehicle, app):
    vehicle.is_connected.return_value = False

    response = app.get(home_position_endpoint)

    # confirm failure - connection not established
    assert response.status_code == 400


@patch("src.routes.aircraft.controllers.vehicle")
def test_home_position_calls_correct_mavlink_command_and_returns_home_position(
    vehicle, app
):
    test_home_position = {
        "lat": 1,
        "lng": 2,
        "alt": 3,
    }
    vehicle.telemetry.wait.return_value = test_home_position

    response = app.get(home_position_endpoint)

    vehicle.mavlink_connection.mav.command_long_send.assert_called_with(
        vehicle.mavlink_connection.target_system,
        vehicle.mavlink_connection.target_component,
        mavutil.mavlink.MAV_CMD_GET_HOME_POSITION,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
    )

    assert response.status_code == 200
    assert json.loads(response.data) == test_home_position