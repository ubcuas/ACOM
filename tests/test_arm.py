import pytest
import json
import time

arm_endpoint = '/aircraft/arm'


def testPrematureAction(app_unconnected):
    # upload wp set
    response = app_unconnected.put(arm_endpoint)

    # confirm failure - connection not established
    assert response.status_code == 400


def testArmSuccessfully(app):
    assert app.vehicle.telemetry.is_armed() == False

    response = app.put(arm_endpoint)

    assert response.status_code == 201
    assert app.vehicle.telemetry.is_armed() == True
