import pytest
import json
from unittest.mock import patch
from src.library.vehicle import Vehicle

rtl_endpoint = '/aircraft/rtl'

@patch('src.routes.aircraft.controllers.vehicle')
def test_premature_action(vehicle: Vehicle, app):
    vehicle.is_connected.return_value = False
    
    response = app.put(rtl_endpoint)

    # confirm failure - connection not established
    assert response.status_code == 400

@patch('src.routes.aircraft.controllers.vehicle')
def test_rtl_endpoint_calls_vehicle_rtl(vehicle: Vehicle, app):
    test_heartbeat = {
        "autopilot": 3,
        "base_mode": 217,
        "custom_mode": 4,
        "mavlink_version": 3,
        "mavpackettype": "HEARTBEAT",
        "system_status": 4,
        "type": 2
    }

    vehicle.telemetry.heartbeat.to_dict.return_value = test_heartbeat
    response = app.put(rtl_endpoint)

    assert response.status_code == 200
    assert json.loads(response.data) == test_heartbeat

    vehicle.mavlink_connection.set_mode_rtl.assert_called_once()
