import pytest
from flaskr import create_app

@pytest.fixture()
def setUp():
    app = create_app().test_client()
    return app

def testRootDirectory(setUp):
    response = setUp.get('/')
    assert response.status_code == 200
