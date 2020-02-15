import pytest
import json
from flaskr import create_app

endpoint = '/aircraft/mission'

@pytest.fixture()
def setUp():
    app = create_app().test_client()
    return app

def testUploadNull(setUp):
    global endpoint
    nullMission = None;

    # upload wp set
    response = setUp.post(endpoint, data=json.dumps(nullMission), content_type='application/json')
    responseData = json.loads(response.data)

    # confirm failure - invalid format
    assert response.status_code == 400

def testUploadEmpty(setUp):
    global endpoint
    emptyMission = {"wps": []};

    # upload wp set
    response = setUp.post(endpoint, data=json.dumps(emptyMission), content_type='application/json')
    responseData = json.loads(response.data)

    # confirm failure - no wps given
    assert response.status_code == 402

def testInvalidTakeOffAlt(setUp):
    global endpoint
    
    missionReqNegAlt = {
        "takeoffAlt": -12,
        "wps": [
        
            {
                "lat": 49.2572585,
                "lng": -123.2423108,       
                "alt": 77
            },
            {
                "lat": 49.255752, 
                "lng": -123.241613,       
                "alt": 10
            },
            {
                "lat": 49.255012, 
                "lng": -123.240912,       
                "alt": 33
            },
            {
                "lat": 49.255222, 
                "lng": -123.239137,       
                "alt": 55
            }
        ],
        "rtl": True
    };

    missionReqNoAlt = {
        "wps": [
        
            {
                "lat": 49.2572585,
                "lng": -123.2423108,       
                "alt": 77
            },
            {
                "lat": 49.255752, 
                "lng": -123.241613,       
                "alt": 10
            },
            {
                "lat": 49.255012, 
                "lng": -123.240912,       
                "alt": 33
            },
            {
                "lat": 49.255222, 
                "lng": -123.239137,       
                "alt": 55
            }
        ],
        "rtl": True
    };

    # upload wp set
    response = setUp.post(endpoint, data=json.dumps(missionReqNegAlt), content_type='application/json')
    responseData = json.loads(response.data)

    # confirm error
    assert response.status_code == 404

    # upload wp set
    response = setUp.post(endpoint, data=json.dumps(missionReqNoAlt), content_type='application/json')
    responseData = json.loads(response.data)

    # confirm error
    assert response.status_code == 403

def testUploadDownloadNonEmpty(setUp):
    global endpoint

    missionReq = {
        "takeoffAlt": 12,
        "wps": [
        
            {
                "lat": 49.2572585,
                "lng": -123.2423108,       
                "alt": 77
            },
            {
                "lat": 49.255752, 
                "lng": -123.241613,       
                "alt": 10
            },
            {
                "lat": 49.255012, 
                "lng": -123.240912,       
                "alt": 33
            },
            {
                "lat": 49.255222, 
                "lng": -123.239137,       
                "alt": 55
            }
        ],
        "rtl": True
    };

    # upload wp set
    response = setUp.post(endpoint, data=json.dumps(missionReq), content_type='application/json')
    responseData = json.loads(response.data)

    # confirm success and count is correct
    assert response.status_code == 201
    assert responseData['wps_uploaded'] == 4

    # download wp set
    response = setUp.get(endpoint, content_type='application/json')
    responseData = json.loads(response.data)
    
    # check the count for the downloaded wp's
    # we won't directly check the values since mavlink does rounding/modifications to the
        # first and last WPs
    assert response.status_code == 201
    assert len(responseData['wps']) == 4