import math
import random
import string
import threading

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
    return "G" + random.choice(string.ascii_uppercase) + random.choice(string.ascii_uppercase) + random.choice(string.ascii_uppercase) + random.choice(string.ascii_uppercase)

def squawkGen():
    squawk = random.choice(CCAMS_SQUAWKS)
    while squawk in allocatedSquawks:
        squawk = random.choice(CCAMS_SQUAWKS)

    allocatedSquawks.append(squawk)
    return squawk

def headingFromTo(fromCoord: tuple[float, float], toCoord: tuple[float, float]) -> int:
    return (math.degrees(math.atan2(toCoord[1] - fromCoord[1], (1/math.cos(math.radians(fromCoord[0]))) * (toCoord[0] - fromCoord[0]))) + 360) % 360


class DaemonTimer(threading.Timer):
    def __init__(self, interval, function, args=[], kwargs={}):
        threading.Timer.__init__(self, interval, function, args, kwargs)
        self.daemon = True
