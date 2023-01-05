import pytest
import json
import time
from unittest.mock import patch, MagicMock
from src.library.vehicle import Vehicle

arm_endpoint = "/aircraft/arm"


@patch("src.routes.aircraft.controllers.vehicle")
def test_premature_action(vehicle: Vehicle, app):
    vehicle.is_connected.return_value = False

    response = app.put(arm_endpoint)

    # confirm failure - connection not established
    assert response.status_code == 400


@patch("src.routes.aircraft.controllers.vehicle")
def test_arm_endpoint_calls_vehicle_arm(vehicle: Vehicle, app):
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
    response = app.put(arm_endpoint)

    assert response.status_code == 201
    assert json.loads(response.data) == test_heartbeat

    vehicle.arm.assert_called_once()
