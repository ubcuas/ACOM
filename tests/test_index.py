import pytest
import json

def testRootDirectory(app):
    response = app.get('/')
    assert response.status_code == 200