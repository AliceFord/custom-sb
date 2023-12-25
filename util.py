import math
import random
import string
import threading
import socket

from PlaneMode import PlaneMode


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


class EsSocket(socket.socket):
    def esSend(self, *args):
        output = b':'.join([str(arg).encode("UTF-8") for arg in args]) + b'\r\n'
        self.sendall(output)


class ControllerSocket(EsSocket):
    @staticmethod
    def StartController(callsign: str) -> 'ControllerSocket':
        s = ControllerSocket()
        s.connect(("127.0.0.1", 6809))
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

        s.connect(("127.0.0.1", 6809))
        s.esSend("#AP" + plane.callsign, "SERVER", "1646235", "pass", "1", "9", "1", "Alice Ford")
        s.sendall(plane.positionUpdateText(calculatePosition=False))
        s.sendall(b'$FP' + plane.callsign.encode("UTF-8") + str(plane.flightPlan).encode("UTF-8") + b'\r\n')  # TODO

        masterSock.esSend(f"$CQ{masterCallsign}", "SERVER", "FP", plane.callsign)
        masterSock.esSend(f"$CQ{masterCallsign}", "@94835", "WH", plane.callsign)
        masterSock.esSend(f"$CQ{masterCallsign}", plane.callsign, "CAPS")

        if plane.currentlyWithData is not None:
            DaemonTimer(1, masterSock.esSend, args=["$CQ" + plane.currentlyWithData[0], "@94835", "IT", plane.callsign]).start()  # Controller takes plane
            DaemonTimer(1, masterSock.esSend, args=["$CQ" + plane.currentlyWithData[0], "@94835", "TA", plane.callsign, plane.altitude]).start()  # Temp alt for arrivals
            # masterSock.sendall(b'$CQ' + plane.currentlyWithData[0].encode("UTF-8") + b':@94835:IT:' + plane.callsign.encode("UTF-8") + b'\r\n')

        DaemonTimer(1, masterSock.esSend, args=["$CQ" + masterCallsign, "@94835", "BC", plane.callsign, plane.squawk]).start()  # Assign squawk

        return s


class DaemonTimer(threading.Timer):
    def __init__(self, interval, function, args=[], kwargs={}):
        threading.Timer.__init__(self, interval, function, args, kwargs)
        self.daemon = True
