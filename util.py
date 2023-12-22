import math
import random
import string
import threading
import socket

from globals import *

def haversine(lat1, lon1, lat2, lon2):  # from https://rosettacode.org/wiki/Haversine_formula#Python
    R = 6372.8  # Earth radius in kilometers

    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    a = math.sin(dLat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dLon / 2)**2
    c = 2 * math.asin(math.sqrt(a))

    return R * c

def callsignGen():
    callsign = ""
    callsign += random.choice(["EZY", "DLH", "BAW", "RYR"])
    callsign += random.choice(string.digits) + random.choice(string.digits) + random.choice(string.ascii_uppercase) + random.choice(string.ascii_uppercase)

    # TODO: ensure callsign is unique
    return callsign

def squawkGen():
    squawk = random.choice(CCAMS_SQUAWKS)
    while squawk in allocatedSquawks:
        squawk = random.choice(CCAMS_SQUAWKS)

    allocatedSquawks.append(squawk)
    return squawk

def headingFromTo(fromCoord: tuple[float, float], toCoord: tuple[float, float]) -> int:
    return (math.degrees(math.atan2(toCoord[1] - fromCoord[1], (1/math.cos(math.radians(fromCoord[0]))) * (toCoord[0] - fromCoord[0]))) + 360) % 360


def deltaLatLonCalc(lat: float, tas: float, heading: float, deltaT: float) -> tuple[float, float]:
    return ((tas * math.cos(math.radians(heading)) * (deltaT / 3600)) / 60, (1/math.cos(math.radians(lat))) * (tas * math.sin(math.radians(heading)) * (deltaT / 3600)) / 60)


class EsSocket(socket.socket):
    def esSend(self, *args):
        output = b':'.join([str(arg).encode("UTF-8") for arg in args]) + b'\r\n'
        self.sendall(output)


class DaemonTimer(threading.Timer):
    def __init__(self, interval, function, args=[], kwargs={}):
        threading.Timer.__init__(self, interval, function, args, kwargs)
        self.daemon = True
