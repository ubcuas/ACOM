import pytest
import json
import time
from unittest.mock import patch, MagicMock
from src.library.vehicle import Vehicle

disarm_endpoint = "/aircraft/disarm"


@patch("src.routes.aircraft.controllers.vehicle")
def test_premature_action(vehicle: Vehicle, app):
    vehicle.is_connected.return_value = False

    response = app.put(disarm_endpoint)

    # confirm failure - connection not established
    assert response.status_code == 400


@patch("src.routes.aircraft.controllers.vehicle")
def test_disarm_endpoint_calls_vehicle_disarm(vehicle: Vehicle, app):
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
    response = app.put(disarm_endpoint)

    assert response.status_code == 201
    assert json.loads(response.data) == test_heartbeat

    vehicle.disarm.assert_called_once()
