import pytest
import json
from unittest.mock import patch

flightmode_endpoint = "/aircraft/telemetry/flightmode"
gps_endpoint = "/aircraft/telemetry/gps"
heartbeat_endpoint = "/aircraft/telemetry/heartbeat"


telemetry_endpoints = [flightmode_endpoint, gps_endpoint, heartbeat_endpoint]


@patch("src.routes.aircraft.controllers.vehicle")
def test_premature_action(vehicle, app):
    vehicle.is_connected.return_value = False

    for telemetry_endpoint in telemetry_endpoints:
        response = app.get(telemetry_endpoint)

        # confirm failure - connection not established
        assert response.status_code == 400


@patch("src.routes.aircraft.controllers.vehicle")
def test_flightmode_returns_flightmode(vehicle, app):
    vehicle.mavlink_connection.flightmode = "GUIDED"

    response = app.get(flightmode_endpoint)

    assert response.status_code == 200
    assert json.loads(response.data) == {"flightmode": "GUIDED"}


@patch("src.routes.aircraft.controllers.vehicle")
def test_gps_calls_vehicle_get_location(vehicle, app):
    test_location = {
        "lat": 1,
        "lng": 2,
        "alt": 3,
        "heading": 4,
    }

    vehicle.telemetry.get_location.return_value = test_location

    response = app.get(gps_endpoint)

    assert response.status_code == 200
    assert json.loads(response.data) == test_location


@patch("src.routes.aircraft.controllers.vehicle")
def test_heartbeat_calls_vehicle_telemetry_heartbeat(vehicle, app):
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

    response = app.get(heartbeat_endpoint)

    assert response.status_code == 200
    assert json.loads(response.data) == test_heartbeat