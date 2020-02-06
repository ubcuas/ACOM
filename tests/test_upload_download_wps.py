import pytest
import json
from flaskr import create_app

@pytest.fixture()
def setUp():
    app = create_app().test_client()
    return app

def testUploadDownloadEmpty(setUp):
    emptyWps = [];

    # upload wp set
    response = setUp.post('/aircraft/mission', data=json.dumps(emptyWps), content_type='application/json')
    responseData = json.loads(response.data)

    # confirm success and count is correct
    assert response.status_code == 201
    assert responseData['wps_uploaded'] == 0

    # download wp set
    response = setUp.get('/aircraft/mission', content_type='application/json')
    responseData = json.loads(response.data)
    
    # check the count for the downloaded wp's
    assert response.status_code == 201
    assert len(responseData['wps']) == 0

def testUploadDownloadNonEmpty(setUp):
    fourWps = [
        {
            "lat": 49.255752,
            "lng": -123.241613,       
            "alt": 22
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
    ];

    # upload wp set
    response = setUp.post('/aircraft/mission', data=json.dumps(fourWps), content_type='application/json')
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