import pytest
import json
from unittest.mock import patch

reroute_endpoint = "/aircraft/reroute"


@patch("src.routes.aircraft.controllers.vehicle")
def test_premature_action(vehicle, app):
    vehicle.is_connected.return_value = False

    response = app.post(reroute_endpoint)

    # confirm failure - connection not established
    assert response.status_code == 400


@patch("src.routes.aircraft.controllers.vehicle")
def test_reroute_endpoint_calls_vehicle_reroute_with_waypoints(vehicle, app):
    gps_response = {
        "alt": 111.0,
        "heading": 131,
        "lat": 49.258873699999995,
        "lng": -123.24094339999999,
    }

    test_data = {
        "waypoints": [
            {"alt": 15, "lat": 49.258873699999995, "lng": -123.2409484},
            {"alt": 10, "lat": 49.258352, "lng": -123.239628},
            {"alt": 25, "lat": 49.258180, "lng": -123.241876},
        ]
    }

    vehicle.telemetry.get_location.return_value = gps_response

    response = app.post(reroute_endpoint, json=test_data)

    assert response.status_code == 200
    assert json.loads(response.data) == gps_response

    vehicle.reroute.assert_called_once_with(test_data["waypoints"])
