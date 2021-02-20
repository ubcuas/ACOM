import pytest
import json
from src import create_app
from src.library.vehicle import vehicle


def get_connected_app():
    return create_app(
        {
            "APIKEY": "jif3fioj32ifj3oi2jf2",
            "FLASK_ENV": "production",
            "MAVLINK_SETUP_DEBUG": "production",
            "IP_ADDRESS": "164.2.0.3",
            "PORT": 5760,
        }
    )


@pytest.fixture(scope="session")
def app():
    # set up
    app_connected = get_connected_app()

    test_client = app_connected.test_client()

    setup_connection(test_client)

    yield test_client  # stop to run tests

    # clean up
    vehicle.disconnect()


def setup_connection(app):
    response = app.post(
        "/aircraft/connect",
        data=json.dumps({"ipAddress": "acom-sitl", "port": 5760}),
        content_type="application/json",
    )

    assert response.status_code == 201
