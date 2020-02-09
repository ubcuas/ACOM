import pytest
import json
from flaskr import create_app

@pytest.fixture()
def setUp():
    app = create_app().test_client()
    return app

def testUploadDownloadNull(setUp):
    nullMission = None;

    # upload wp set
    response = setUp.post('/aircraft/mission', data=json.dumps(nullMission), content_type='application/json')
    responseData = json.loads(response.data)

    # confirm failure - invalid format
    assert response.status_code == 400

def testUploadDownloadEmpty(setUp):
    emptyMission = {"wps": []};

    # upload wp set
    response = setUp.post('/aircraft/mission', data=json.dumps(emptyMission), content_type='application/json')
    responseData = json.loads(response.data)

    # confirm failure - no wps given
    assert response.status_code == 402

def testUploadDownloadNonEmpty(setUp):
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
    response = setUp.post('/aircraft/mission', data=json.dumps(missionReq), content_type='application/json')
    responseData = json.loads(response.data)

    # confirm success and count is correct
    assert response.status_code == 201
    assert responseData['wps_uploaded'] == 4

    # download wp set
    response = setUp.get('/aircraft/mission', content_type='application/json')
    responseData = json.loads(response.data)
    
    # check the count for the downloaded wp's
    # we won't directly check the values since mavlink does rounding/modifications to the
        # first and last WPs
    assert response.status_code == 201
    assert len(responseData['wps']) == 4