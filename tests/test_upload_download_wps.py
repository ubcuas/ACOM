import pytest
import json
from unittest.mock import patch
from src.library.vehicle import vehicle

connect_endpoint = "/aircraft/connect"
mission_endpoint = "/aircraft/mission"


@patch("src.routes.aircraft.controllers.vehicle")
def testPrematureAction(vehicle, app):
    vehicle.is_connected.return_value = False

    global mission_endpoint
    nullMission = None

    # upload wp set
    response = app.post(
        mission_endpoint, data=json.dumps(nullMission), content_type="application/json"
    )

    # confirm failure - connection not established
    assert response.status_code == 400


def testUploadNull(app):
    global mission_endpoint
    nullMission = None

    # upload wp set
    response = app.post(
        mission_endpoint, data=json.dumps(nullMission), content_type="application/json"
    )
    responseData = json.loads(response.data)

    # confirm failure - invalid format
    assert response.status_code == 405


def testUploadEmpty(app):
    global mission_endpoint
    emptyMission = {"wps": []}

    # upload wp set
    response = app.post(
        mission_endpoint, data=json.dumps(emptyMission), content_type="application/json"
    )
    responseData = json.loads(response.data)

    # confirm failure - no wps given
    assert response.status_code == 402


def testInvalidTakeOffAlt(app):
    global mission_endpoint

    missionReqNegAlt = {
        "takeoffAlt": -12,
        "wps": [
            {"lat": 49.2572585, "lng": -123.2423108, "alt": 77},
            {"lat": 49.255752, "lng": -123.241613, "alt": 10},
            {"lat": 49.255012, "lng": -123.240912, "alt": 33},
            {"lat": 49.255222, "lng": -123.239137, "alt": 55},
        ],
        "rtl": True,
    }

    missionReqNoAlt = {
        "wps": [
            {"lat": 49.2572585, "lng": -123.2423108, "alt": 77},
            {"lat": 49.255752, "lng": -123.241613, "alt": 10},
            {"lat": 49.255012, "lng": -123.240912, "alt": 33},
            {"lat": 49.255222, "lng": -123.239137, "alt": 55},
        ],
        "rtl": True,
    }

    # upload wp set
    response = app.post(
        mission_endpoint,
        data=json.dumps(missionReqNegAlt),
        content_type="application/json",
    )
    responseData = json.loads(response.data)

    # confirm error
    assert response.status_code == 404

    # upload wp set
    response = app.post(
        mission_endpoint,
        data=json.dumps(missionReqNoAlt),
        content_type="application/json",
    )
    responseData = json.loads(response.data)

    # confirm error
    assert response.status_code == 403


def testUploadDownloadNonEmpty(app):
    global mission_endpoint

    # wait for a view rounds of telemetry to be set
    for i in range(5):
        vehicle.telemetry.wait("GLOBAL_POSITION_INT", timeout=1)

    missionReq = {
        "takeoffAlt": 12,
        "wps": [
            {"lat": 49.2572585, "lng": -123.2423108, "alt": 77},
            {"lat": 49.255752, "lng": -123.241613, "alt": 10},
            {"lat": 49.255012, "lng": -123.240912, "alt": 33},
            {"lat": 49.255222, "lng": -123.239137, "alt": 55},
        ],
        "rtl": True,
    }

    # upload wp set
    response = app.post(
        mission_endpoint, data=json.dumps(missionReq), content_type="application/json"
    )
    responseData = json.loads(response.data)

    # confirm success and count is correct
    assert response.status_code == 201
    assert responseData["wps_uploaded"] == 4

    # download wp set
    response = app.get(mission_endpoint, content_type="application/json")
    responseData = json.loads(response.data)

    # check the count for the downloaded wp's
    # we won't directly check the values since mavlink does rounding/modifications to the
    # first and last WPs
    assert response.status_code == 200
    assert len(responseData["wps"]) == 4
