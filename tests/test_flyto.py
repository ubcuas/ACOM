import pytest
import json
from unittest.mock import patch
from src.library.vehicle import Vehicle

flyto_endpoint = "/aircraft/flyto"


@patch("src.routes.aircraft.controllers.vehicle")
def test_premature_action(vehicle: Vehicle, app):
    vehicle.is_connected.return_value = False

    response = app.post(flyto_endpoint)

    # confirm failure - connection not established
    assert response.status_code == 400


@patch("src.routes.aircraft.controllers.vehicle")
def test_flyto_calls_vehicle_flyto_with_correct_parameters(vehicle: Vehicle, app):
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

    flyto_data = {
        "lat": 1,
        "lng": 2,
        "alt": 3,
    }

    response = app.post(
        flyto_endpoint,
        data=json.dumps(flyto_data),
        content_type="application/json",
    )

    vehicle.fly_to.assert_called_with(1, 2, 3)

    assert response.status_code == 200
    assert json.loads(response.data) == test_heartbeat
