import pytest
import json
from unittest.mock import patch
from pymavlink import mavutil
from src.library.vehicle import Vehicle


takeoff_endpoint = "/aircraft/takeoff"


@patch("src.routes.aircraft.controllers.vehicle")
def test_premature_action(vehicle: Vehicle, app):
    vehicle.is_connected.return_value = False

    response = app.post(takeoff_endpoint)

    # confirm failure - connection not established
    assert response.status_code == 400


@patch("src.routes.aircraft.controllers.vehicle")
def test_takeoff_calls_mavlink_command_for_takeoff_with_correct_parameters(
    vehicle, app
):
    test_heartbeat = {
        "autopilot": 3,
        "base_mode": 217,
        "custom_mode": 4,
        "mavlink_version": 3,
        "mavpackettype": "HEARTBEAT",
        "system_status": 4,
        "type": 2,
    }
    vehicle.telemetry.heartbeat.to_dict.return_value = test_heartbeat

    takeoff_data = {
        "lat": 1,
        "lng": 2,
        "alt": 3,
        "pitch": 4,
        "yaw": 5,
    }

    response = app.post(
        takeoff_endpoint,
        data=json.dumps(takeoff_data),
        content_type="application/json",
    )

    vehicle.mavlink_connection.mav.command_long_send.assert_called_with(
        vehicle.mavlink_connection.target_system,
        vehicle.mavlink_connection.target_component,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
        0,
        takeoff_data["pitch"],
        0,
        0,
        takeoff_data["yaw"],
        takeoff_data["lat"],
        takeoff_data["lng"],
        takeoff_data["alt"],
    )

    assert response.status_code == 200
    assert json.loads(response.data) == test_heartbeat
