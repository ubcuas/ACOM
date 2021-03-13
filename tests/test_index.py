import pytest
import json

def test_route_directory(app):
    response = app.get('/')
    assert response.status_code == 200