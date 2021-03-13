import pytest
import json
from unittest.mock import patch

manual_endpoint = "/aircraft/manual"
auto_endpoint = "/aircraft/auto"
guided_endpoint = "/aircraft/guided"

mode_endpoints = [manual_endpoint, auto_endpoint, guided_endpoint]


@patch("src.routes.aircraft.controllers.vehicle")
def test_premature_action(vehicle, app):
    vehicle.is_connected.return_value = False

    for mode_endpoint in mode_endpoints:
        response = app.put(manual_endpoint)

        # confirm failure - connection not established
        assert response.status_code == 400


test_heartbeat = {
    "autopilot": 3,
    "base_mode": 217,
    "custom_mode": 4,
    "mavlink_version": 3,
    "mavpackettype": "HEARTBEAT",
    "system_status": 4,
    "type": 2,
}


@patch("src.routes.aircraft.controllers.vehicle")
def test_manual_endpoint_calls_set_mode_manual(vehicle, app):
    vehicle.telemetry.heartbeat.to_dict.return_value = test_heartbeat
    response = app.put(manual_endpoint)

    assert response.status_code == 200
    assert json.loads(response.data) == test_heartbeat

    vehicle.mavlink_connection.set_mode_manual.assert_called_once()


@patch("src.routes.aircraft.controllers.vehicle")
def test_auto_endpoint_calls_set_mode_auto(vehicle, app):
    vehicle.telemetry.heartbeat.to_dict.return_value = test_heartbeat
    response = app.put(auto_endpoint)

    assert response.status_code == 200
    assert json.loads(response.data) == test_heartbeat

    vehicle.mavlink_connection.set_mode_auto.assert_called_once()


@patch("src.routes.aircraft.controllers.vehicle")
def test_auto_endpoint_calls_set_mode_guided(vehicle, app):
    vehicle.telemetry.heartbeat.to_dict.return_value = test_heartbeat
    response = app.put(guided_endpoint)

    assert response.status_code == 200
    assert json.loads(response.data) == test_heartbeat

    vehicle.mavlink_connection.set_mode.assert_called_once_with("GUIDED")