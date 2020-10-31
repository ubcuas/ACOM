import pytest
import json
from src import create_app

def get_app():
    return create_app({
        "APIKEY": 'jif3fioj32ifj3oi2jf2',
        "FLASK_ENV": "production",
        "MAVLINK_SETUP_DEBUG": "production",
    })

def get_connected_app():
    return create_app({
        "APIKEY": 'jif3fioj32ifj3oi2jf2',
        "FLASK_ENV": "production",
        "MAVLINK_SETUP_DEBUG": "production",
        "IP_ADDRESS": "164.2.0.3",
        "PORT": 5760
    })

@pytest.fixture()
def app_unconnected():
    # set up
    app_unconnected = get_app()

    test_client = app_unconnected.test_client()
    test_client.vehicle = app_unconnected.vehicle
    
    yield test_client # stop to run tests

    # clean up

@pytest.fixture()
def app():
    # set up
    app_connected = get_connected_app()

    test_client = app_connected.test_client()
    test_client.vehicle = app_connected.vehicle

    setup_connection(test_client)

    for i in range(5):
        test_client.vehicle.telemetry.wait("GLOBAL_POSITION_INT", timeout=10) # wait for several rounds of telemetry before running tests

    yield test_client # stop to run tests

    # clean up
    app_connected.vehicle.disconnect()

def setup_connection(app):
    response = app.post('/aircraft/connect', data=json.dumps({
        "ipAddress": "acom-sitl",
        "port": 5760
    }), content_type='application/json')

    print("\n", response.data, "\n")

    assert response.status_code == 201