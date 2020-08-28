# utility.py
from math import radians, cos, sin, asin, sqrt, pi, atan2, degrees
from src.library.location import Location
from geographiclib.geodesic import Geodesic
from functools import wraps

## returns request.json['key'] if the key exists
## else return given defaultValue
def parseRequest(request, key, defaultValue):
    if key in request.json:
        return request.json[key]
    else:
        return defaultValue

## returns object['key'] if the key exists
## else return given defaultValue
def parseJson(jsonObject, key, defaultValue):
    if key in jsonObject:
        return jsonObject[key]
    else:
        return defaultValue

def empty_socket(mavlink_connection):
    """
    empties all incoming data from the mavlink connection

    Args:
        mavlink_connections
    """
    while True:
        try:
            n = mavlink_connection.mav.bytes_needed()
            mavlink_connection.port.recv(n)
        except:
            break

# returns the distance in metres between two points using haversine formula
def get_distance_metres(point1, point2):
    lon1 = point1.lng
    lat1 = point1.lat
    lon2 = point2.lng
    lat2 = point2.lat
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371 * 1000
    return c * r

def get_bearing(point1, point2):
    lon1 = point1.lng
    lat1 = point1.lat
    lon2 = point2.lng
    lat2 = point2.lat

    brng = Geodesic.WGS84.Inverse(lat1, lon1, lat2, lon2)['azi1']
    return radians(brng)

def get_degrees_needed_to_turn(heading, currentLocation, targetLocation):
    lon1 = currentLocation.lng
    lat1 = currentLocation.lat
    lon2 = targetLocation.lng
    lat2 = targetLocation.lat

    degree = Geodesic.WGS84.Inverse(lat1, lon1, lat2, lon2)['azi1'] % 360
    turn_degree = heading - degree
    if turn_degree > 180:
        turn_degree = 360 - turn_degree
    return turn_degree

def get_point_further_away(point1, point2, d):
    lon1 = point1.lng
    lat1 = point1.lat
    alt1 = point1.alt
    lon2 = point2.lng
    lat2 = point2.lat
    alt2 = point2.alt

    brng = get_bearing(point1, point2)
    #print(degrees(brng))

    lon2 = radians(lon2)
    lat2 = radians(lat2)
    R = 6378.1 * 1000 #Radius of the Earth in m

    lat = asin( sin(lat2)*cos(d/R) +
        cos(lat2)*sin(d/R)*cos(brng))

    lon = lon2 + atan2(sin(brng)*sin(d/R)*cos(lat2),
                cos(d/R)-sin(lat2)*sin(lat))

    lat = degrees(lat)
    lon = degrees(lon)

    alt = alt2 * get_distance_metres(Location(lat, lon, 0), point1) / get_distance_metres(point1, point2)

    return Location(lat, lon, alt)
