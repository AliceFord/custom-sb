import math
import random
import string
import threading
import socket
import time
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
from Constants import OTHER_CONTROLLERS, INACTIVE_SECTORS, PORT

from PlaneMode import PlaneMode
from sfparser import loadSectorData, sfCoordsToNormalCoords


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
    from Constants import CCAMS_SQUAWKS
    from globalVars import allocatedSquawks
    squawk = random.choice(CCAMS_SQUAWKS)
    while squawk in allocatedSquawks:
        squawk = random.choice(CCAMS_SQUAWKS)

    allocatedSquawks.append(squawk)
    return squawk


def headingFromTo(fromCoord: tuple[float, float], toCoord: tuple[float, float]) -> int:
    return (math.degrees(math.atan2(toCoord[1] - fromCoord[1], (1 / math.cos(math.radians(fromCoord[0]))) * (toCoord[0] - fromCoord[0]))) + 360) % 360


def deltaLatLonCalc(lat: float, tas: float, heading: float, deltaT: float) -> tuple[float, float]:
    return ((tas * math.cos(math.radians(heading)) * (deltaT / 3600)) / 60, (1 / math.cos(math.radians(lat))) * (tas * math.sin(math.radians(heading)) * (deltaT / 3600)) / 60)


def modeConverter(mode: PlaneMode) -> str:
    match mode:
        case PlaneMode.GROUND_STATIONARY:
            return "Stationary"
        case PlaneMode.GROUND_READY:
            return "Ready"
        case PlaneMode.GROUND_TAXI:
            return "Taxiing"
        case PlaneMode.FLIGHTPLAN:
            return "Flightplan"
        case PlaneMode.HEADING:
            return "Heading"
        case PlaneMode.ILS:
            return "ILS"
        case PlaneMode.NONE:
            return "Error"
        case _:
            return str(mode)


def whichSector(lat: float, lon: float, alt: int) -> str:
    sectorData = loadSectorData()

    pos = Point(lat, lon)

    possibilities = []
    sectorOut = None

    for sectorName, sector in sectorData.items():
        polygon = Polygon(sector)
        if polygon.contains(pos):
            if sectorName in INACTIVE_SECTORS:
                continue
            possibilities.append(sectorName)
            if ("LTC" in sectorName or "STC" in sectorName or "MAN" in sectorName) and alt < 19500:  # TODO: WTF!
                sectorOut = sectorName
                break
            elif "LON" in sectorName:
                sectorOut = sectorName
    
    if sectorOut is None:
        if len(possibilities) >= 1:
            sectorOut = possibilities[0]  # TODO: :(
        
    return sectorOut


def otherControllerIndex(callsign: str) -> int:
    for i, controller in enumerate(OTHER_CONTROLLERS):
        if controller[0] == callsign:
            return i


class EsSocket(socket.socket):
    def esSend(self, *args):
        output = b':'.join([str(arg).encode("UTF-8") for arg in args]) + b'\r\n'
        self.sendall(output)


class ControllerSocket(EsSocket):
    @staticmethod
    def StartController(callsign: str) -> 'ControllerSocket':
        s = ControllerSocket()
        s.connect(("127.0.0.1", PORT))
        # Login controller:
        s.esSend("#AA" + callsign, "SERVER", "Alice Ford", "1646235", "pass", "7", "9", "1", "0", "51.14806", "-0.19028", "100")
        s.esSend("%" + callsign, "29430", "3", "100", "7", "51.14806", "-0.19028", "0")
        message = s.recv(1024)

        print(message)

        s.esSend("$CQ" + callsign, "SERVER", "ATC", callsign)
        s.esSend("$CQ" + callsign, "SERVER", "CAPS")
        s.esSend("$CQ" + callsign, "SERVER", "IP")

        infoResponse = s.recv(1024)

        print(infoResponse)

        return s


class PlaneSocket(EsSocket):
    @staticmethod
    def StartPlane(plane, masterCallsign: str, masterSock: ControllerSocket) -> 'PlaneSocket':
        s = PlaneSocket(socket.AF_INET, socket.SOCK_STREAM)

        plane.masterSocketHandleData = (masterSock, masterCallsign)

        s.connect(("127.0.0.1", PORT))
        s.esSend("#AP" + plane.callsign, "SERVER", "1646235", "pass", "1", "9", "1", "Alice Ford")
        s.sendall(plane.positionUpdateText(calculatePosition=False))
        s.sendall(b'$FP' + plane.callsign.encode("UTF-8") + str(plane.flightPlan).encode("UTF-8") + b'\r\n')  # TODO

        masterSock.esSend(f"$CQ{masterCallsign}", "SERVER", "FP", plane.callsign)
        masterSock.esSend(f"$CQ{masterCallsign}", "@94835", "WH", plane.callsign)
        masterSock.esSend(f"$CQ{masterCallsign}", plane.callsign, "CAPS")

        if plane.currentlyWithData is not None:
            PausableTimer(1, masterSock.esSend, args=["$CQ" + plane.currentlyWithData[0], "@94835", "IT", plane.callsign])  # Controller takes plane
            PausableTimer(1, masterSock.esSend, args=["$CQ" + plane.currentlyWithData[0], "@94835", "TA", plane.callsign, plane.altitude])  # Temp alt for arrivals
            # masterSock.sendall(b'$CQ' + plane.currentlyWithData[0].encode("UTF-8") + b':@94835:IT:' + plane.callsign.encode("UTF-8") + b'\r\n')

        PausableTimer(1, masterSock.esSend, args=["$CQ" + masterCallsign, "@94835", "BC", plane.callsign, plane.squawk])  # Assign squawk

        return s


class PausableTimer(threading.Thread):
    timers: list['PausableTimer'] = []

    def __init__(self, interval, function, args=[], kwargs={}):
        threading.Timer.__init__(self, interval, function, args, kwargs)
        self.delay = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs

        self.timeElapsed = 0
        self.cancel = False
        self.daemon = True
        self.startTime = time.time()

        PausableTimer.timers.append(self)
        self.start()

    def pause(self):
        self.cancel = True
        self.delay -= time.time() - self.startTime

    def restart(self):
        PausableTimer.timers.remove(self)
        self.__init__(self.delay, self.function, self.args, self.kwargs)

    def run(self) -> None:
        while self.timeElapsed < self.delay:
            if self.cancel:
                return
            self.timeElapsed = time.time() - self.startTime
            time.sleep(0.5)

        PausableTimer.timers.remove(self)
        try:
            self.function(*self.args, **self.kwargs)
        except Exception as e:
            print(e)


if __name__ == "__main__":
    print(whichSector(*sfCoordsToNormalCoords(*"N052.24.50.722:W001.15.26.594".split(":")), 5000))
