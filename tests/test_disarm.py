import pytest
import json
import time
from unittest.mock import patch, MagicMock

disarm_endpoint = "/aircraft/disarm"


@patch("src.routes.aircraft.controllers.vehicle")
def test_premature_action(vehicle, app):
    vehicle.is_connected.return_value = False

    # upload wp set
    response = app.put(disarm_endpoint)

    # confirm failure - connection not established
    assert response.status_code == 400


@patch("src.routes.aircraft.controllers.vehicle")
def test_disarm_endpoint_calls_vehicle_disarm(vehicle, app):
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
