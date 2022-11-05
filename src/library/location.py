# took from dronekit LocationGlobal
# https://github.com/dronekit/dronekit-python/blob/master/dronekit/__init__.py
class Location(object):
    """
    A location object.
    The latitude and longitude are relative to the `WGS84 coordinate system <https://en.wikipedia.org/wiki/World_Geodetic_System>`_.
    The altitude is relative to mean sea-level (MSL).
    For example, a global location object with altitude 30 metres above sea level might be defined as:
    .. code:: python
       Location(-34.364114, 149.166022, 30)
    An object of this type is owned by :py:attr:`Vehicle.location`. See that class for information on
    reading and observing location in the global frame.
    :param lat: Latitude.
    :param lng: Longitude.
    :param alt: Altitude in meters relative to mean sea-level (MSL).
    """

    def __init__(self, lat, lng, alt):
        self.lat = lat
        self.lng = lng
        self.alt = alt

    def __str__(self):
        return "LocationGlobal:lat=%s,lng=%s,alt=%s" % (self.lat, self.lng, self.alt)
