import random
import select
import socket
import time
import math
import threading
import sys
from PyQt6 import QtWidgets, uic
from PyQt6.QtWidgets import QTableWidgetItem
import string

from uiTest import MainWindow
from sfparser import loadRunwayData, loadSidAndFixData, loadStarAndFixData, parseFixes

# GENERAL STUFF

FIXES = parseFixes()


def haversine(lat1, lon1, lat2, lon2):  # from https://rosettacode.org/wiki/Haversine_formula#Python
    R = 6372.8  # Earth radius in kilometers

    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    a = math.sin(dLat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dLon / 2)**2
    c = 2 * math.asin(math.sqrt(a))

    return R * c


class Route:
    def __init__(self, route: str):
        self.route = route
        self.initial = True
        self.fixes = []
        self.initialiseFixesFromRoute()

    def initialiseFixesFromRoute(self):
        fixAirways = self.route.split(" ")

        if len(fixAirways) == 2:  # TODO: BUILD A BETTER PARSER!
            if fixAirways[1] == "AMDUT1G":
                self.fixes = ["AMDUT", "SFD", "WILLO"]
                return
            elif fixAirways[1] == "VASUX1G":
                self.fixes = ["VASUX", "TELTU", "HOLLY", "WILLO"]
                return
            elif fixAirways[1] == "SIRIC1G":
                self.fixes = ["SIRIC", "NIGIT", "MID", "TUFOZ", "HOLLY", "WILLO"]
                return
            elif fixAirways[1] == "TELTU1G":
                self.fixes = ["TELTU", "SFD", "TIMBA"]
                return
            elif fixAirways[1] == "ABSAV1G":
                self.fixes = ["ABSAV", "AVANT", "GWC", "HOLLY", "WILLO"]
                return
            elif fixAirways[1] == "KIDLI1G":
                self.fixes = ["KIDLI", "MID", "TUFOZ", "HOLLY", "WILLO"]
                return
            
        if fixAirways[0].endswith("/26L"):  # TODO: choose runway
            data = loadSidAndFixData("EGKK")  # TODO: choose airport
            sidName = fixAirways[0].split("/")[0]
            self.fixes = data[0][sidName]["26L"].split(" ")  # TODO: choose runway
            FIXES.update(data[1])
            fixAirways.pop(0)
        
        for i in range(0, len(fixAirways), 2):
            initialFix = fixAirways[i]
            # airway = fixAirways[i + 1]
            # finalFix = fixAirways[i + 2]

            self.fixes.append(initialFix)

            # TODO: add airway fixes for usable directs

    def removeFirstFix(self):
        self.fixes.pop(0)

    def __str__(self):
        return self.route
    
    @staticmethod
    def duplicate(route):
        return Route(route.route)


class FlightPlan:
    def __init__(self, flightRules: str, aircraftType: str, enrouteSpeed: int, departure: str, offBlockTime: int, 
                 enrouteTime: int, cruiseAltitude: int, destination: str, route: Route):
        self.flightRules = flightRules
        self.aircraftType = aircraftType
        self.enrouteSpeed = enrouteSpeed
        self.departure = departure
        self.offBlockTime = offBlockTime
        self.enrouteTime = enrouteTime
        self.cruiseAltitude = cruiseAltitude
        self.destination = destination
        self.route = route

    def __str__(self):
        return f":*A:{self.flightRules}:{self.aircraftType}:{self.enrouteSpeed}:{self.departure}:{self.offBlockTime}:{self.enrouteTime}:{self.cruiseAltitude}:{self.destination}:01:00:0:0::/v/:{self.route}"

    @staticmethod
    def duplicate(flightPlan):
        return FlightPlan(flightPlan.flightRules, flightPlan.aircraftType, flightPlan.enrouteSpeed, flightPlan.departure, flightPlan.offBlockTime, flightPlan.enrouteTime, flightPlan.cruiseAltitude, flightPlan.destination, Route.duplicate(flightPlan.route))

class Plane:
    def __init__(self, callsign: str, squawk: int, altitude: int, heading: int, speed: float, lat: float, lon: float, vertSpeed: float, mode: str, flightPlan: FlightPlan, currentlyWithData: tuple[str, str]):  # onGround?
        self.callsign = callsign
        self.squawk = squawk
        self.altitude = altitude  # feet
        self.heading = heading  # 001 - 360
        self.speed = speed  # knots
        self.lat = lat  # decimal degrees
        self.lon = lon  # decimal degrees
        self.vertSpeed = vertSpeed  # feet per minute
        self.mode = mode  # HDG, FPL, ILS
        self.flightPlan = flightPlan  # fpln
        self.currentlyWithData = currentlyWithData  # (current controller, release point)

        self.targetSpeed = speed
        self.targetAltitude = altitude
        self.targetHeading = heading
        self.turnDir = None
        self.holdFix = None
        self.holdStartTime = None

        self.masterSocketHandleData: tuple[socket.socket, str] = None
        self.clearedILS = None

        self.lastTime = time.time()

    def calculatePosition(self):
        global timeMultiplier
        deltaT = (time.time() - self.lastTime) * timeMultiplier
        self.lastTime = time.time()

        if self.targetSpeed != self.speed:
            if 0.5 * deltaT > abs(self.targetSpeed - self.speed):
                self.speed = self.targetSpeed
            elif self.targetSpeed > self.speed:
                self.speed += 0.5 * deltaT  # 0.5kts / sec
            elif self.targetSpeed < self.speed:
                self.speed -= 0.5 * deltaT

            self.speed = round(self.speed, 0)
        
        else:  # can only change altitude if speed is constant (somewhat bad energy conservation model but whatever)

            self.altitude += self.vertSpeed * (deltaT / 60)
            self.altitude = round(self.altitude, 0)

        if self.vertSpeed > 0 and self.altitude >= self.targetAltitude:
            self.vertSpeed = 0
            self.altitude = self.targetAltitude
        elif self.vertSpeed < 0 and self.altitude <= self.targetAltitude:
            self.vertSpeed = 0
            self.altitude = self.targetAltitude

        activateHoldMode = False

        if self.mode == "ILS":
            deltaLat = (self.speed * math.cos(math.radians(self.heading)) * (deltaT / 3600)) / 60 # (nautical miles travelled) / 60
            deltaLon = (1/math.cos(math.radians(self.lat))) * (self.speed * math.sin(math.radians(self.heading)) * (deltaT / 3600)) / 60  # (1/math.cos(math.radians(self.lat))) for longitude stretching

            self.lat += deltaLat
            self.lat = round(self.lat, 5)
            self.lon += deltaLon
            self.lon = round(self.lon, 5)
        elif self.mode == "HDG":
            if self.holdStartTime is not None:
                if time.time() - self.holdStartTime >= 60:  # 30 sec holds
                    self.holdStartTime = time.time()
                    self.targetHeading += 180
                    self.targetHeading = self.targetHeading % 360
            if self.targetHeading != self.heading:  # turns
                if 3 * deltaT > abs(self.targetHeading - self.heading):
                    self.heading = self.targetHeading
                    if self.holdStartTime is not None:
                        self.holdStartTime = time.time()
                elif self.turnDir == "L":
                    self.heading -= 3 * deltaT  # 3deg / sec
                else:
                    self.heading += 3 * deltaT
                
                self.heading = (self.heading + 360) % 360

            deltaLat = (self.speed * math.cos(math.radians(self.heading)) * (deltaT / 3600)) / 60 # (nautical miles travelled) / 60
            deltaLon = (1/math.cos(math.radians(self.lat))) * (self.speed * math.sin(math.radians(self.heading)) * (deltaT / 3600)) / 60

            if self.clearedILS is not None:
                hdgToRunway = (math.degrees(math.atan2(self.clearedILS[1][1] - self.lon, (1/math.cos(math.radians(self.lat))) * (self.clearedILS[1][0] - self.lat))) + 360) % 360
                newHdgToRunway = (math.degrees(math.atan2(self.clearedILS[1][1] - (self.lon + deltaLon), (1/math.cos(math.radians(self.lat))) * (self.clearedILS[1][0] - (self.lat + deltaLat)))) + 360) % 360
                if (hdgToRunway < self.clearedILS[0] < newHdgToRunway) or (hdgToRunway > self.clearedILS[0] > newHdgToRunway):
                    self.mode = "ILS"
                    self.heading = self.clearedILS[0]
                    self.clearedILS = None

            self.lat += deltaLat
            self.lat = round(self.lat, 5)
            self.lon += deltaLon
            self.lon = round(self.lon, 5)
        elif self.mode == "FPL":
            distanceToTravel = self.speed * (deltaT / 3600)
            nextFixCoords = FIXES[self.flightPlan.route.fixes[0]]
            distanceToFix = haversine(self.lat, self.lon, nextFixCoords[0], nextFixCoords[1]) / 1.852  # nautical miles

            if self.holdFix is not None and self.flightPlan.route.fixes[0] == self.holdFix and distanceToFix <= distanceToTravel:
                activateHoldMode = True
            else:
                if distanceToFix <= distanceToTravel:
                    distanceFrac = 1 - (distanceToFix / distanceToTravel)
                    deltaT *= distanceFrac  # so later lerp is still correct
                    self.lat = nextFixCoords[0]
                    self.lon = nextFixCoords[1]
                    self.flightPlan.route.removeFirstFix()

                    if self.currentlyWithData is not None:  # if we're on route to the release point, hand em off
                        if self.currentlyWithData[1] == self.flightPlan.route.fixes[0]:
                            self.masterSocketHandleData[0].sendall(b'$HO' + self.masterSocketHandleData[1].encode("UTF-8") + b':EGKK_APP:' + self.callsign.encode("UTF-8") + b'\r\n')  # TODO: choose correct controller

                    nextFixCoords = FIXES[self.flightPlan.route.fixes[0]]
                    self.heading = (math.degrees(math.atan2(nextFixCoords[1] - self.lon, (1/math.cos(math.radians(self.lat))) * (nextFixCoords[0] - self.lat))) + 360) % 360

                if self.flightPlan.route.initial:
                    self.flightPlan.route.initial = False
                    self.heading = (math.degrees(math.atan2(nextFixCoords[1] - self.lon, (1/math.cos(math.radians(self.lat))) * (nextFixCoords[0] - self.lat))) + 360) % 360

                self.lat += (self.speed * math.cos(math.radians(self.heading)) * (deltaT / 3600)) / 60  # (nautical miles travelled) / 60
                self.lat = round(self.lat, 5)
                self.lon += (1/math.cos(math.radians(self.lat))) * (self.speed * math.sin(math.radians(self.heading)) * (deltaT / 3600)) / 60
                self.lon = round(self.lon, 5)

        if activateHoldMode:
            self.holdStartTime = time.time()
            self.targetHeading = 279
            self.mode = "HDG"
            self.turnDir = "L"


    def addPlaneText(self) -> bytes:
        return b'#AP' + self.callsign.encode("UTF-8") + b':SERVER:1646235:pass:1:9:1:Alice Ford\r\n'
    
    def positionUpdateText(self) -> bytes:
        self.calculatePosition()
        return b'@N:' + self.callsign.encode("UTF-8") + b':' + str(self.squawk).encode("UTF-8") + b':1:' + str(self.lat).encode("UTF-8") + b':' + str(self.lon).encode("UTF-8") + b':' + str(self.altitude).encode("UTF-8") + b':' + str(self.speed).encode("UTF-8") + b':0:0\r\n'


    @staticmethod
    def requestFromFix(callsign: str, fix: str, squawk: int = 1234, altitude: int = 10000, heading: int = 0, speed: float = 0, vertSpeed: float = 0, flightPlan: FlightPlan = FlightPlan("I", "B738", 250, "EGKK", 1130, 1130, 36000, "EDDF", Route("MIMFO Y312 DVR L9 KONAN L607 KOK UL607 SPI T180 UNOKO")), currentlyWithData: str = None):
        try:
            coords = FIXES[fix]
        except KeyError:
            print("Fix not found")
            coords = (51.15487, -0.16454)
        return Plane(callsign, squawk, altitude, heading, speed, coords[0], coords[1], vertSpeed, "FPL", flightPlan, currentlyWithData)
    
    @staticmethod
    def requestDeparture(callsign: str, airport: str, squawk: int = 1234, altitude: int = 600, heading: int = 0, speed: float = 150, vertSpeed: float = 2000, flightPlan: FlightPlan = FlightPlan("I", "B738", 250, "EGKK", 1130, 1130, 36000, "EDDF", Route("MIMFO Y312 DVR L9 KONAN L607 KOK UL607 SPI T180 UNOKO"))):
        coords = loadRunwayData(airport)["26L"]  # TODO: choose runway
        return Plane(callsign, squawk, altitude, heading, speed, coords[1][0], coords[1][1], vertSpeed, "FPL", flightPlan, None)


# SOCKET STUFF

def startController(callsign: str) -> socket.socket:
    callsign = callsign.encode("UTF-8")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("127.0.0.1", 6809))
    # Login controller:
    s.sendall(b'#AA' + callsign + b':SERVER:Alice Ford:1646235:pass:7:9:1:0:51.14806:-0.19028:100\r\n')
    s.sendall(b'%' + callsign + b':29430:3:100:7:51.14806:-0.19028:0\r\n')
    message = s.recv(1024)

    print(message)

    s.sendall(b'$CQ' + callsign + b':SERVER:ATC:' + callsign + b'\r\n')
    s.sendall(b'$CQ' + callsign + b':SERVER:CAPS\r\n')
    s.sendall(b'$CQ' + callsign + b':SERVER:IP\r\n')

    infoResponse = s.recv(1024)

    print(infoResponse)

    return s

def startPlane(plane: Plane, masterCallsign: str, masterSock: socket.socket) -> socket.socket:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    plane.masterSocketHandleData = (masterSock, masterCallsign)

    masterCallsign = masterCallsign.encode("UTF-8")

    s.connect(("127.0.0.1", 6809))
    s.sendall(plane.addPlaneText())
    # s.sendall(plane.positionUpdateText())
    s.sendall(b'$FP' + plane.callsign.encode("UTF-8") + str(plane.flightPlan).encode("UTF-8") + b'\r\n') #TODO
    
    masterSock.sendall(b'$CQ' + masterCallsign + b':SERVER:FP:' + plane.callsign.encode("UTF-8") + b'\r\n')
    masterSock.sendall(b'$CQ' + masterCallsign + b':@94835:WH:' + plane.callsign.encode("UTF-8") + b'\r\n')
    masterSock.sendall(b'$CQ' + masterCallsign + b':' + plane.callsign.encode("UTF-8") + b':CAPS\r\n')

    if plane.currentlyWithData is not None:
        masterSock.sendall(b'$CQ' + plane.currentlyWithData[0].encode("UTF-8") + b'@94835:IT:' + plane.callsign.encode("UTF-8") + b'\r\n')
    
    return s

# COMMAND PARSING

class _MatchException(Exception): pass

def parseCommand():
    global FIXES
    # See command spec
    text = window.commandEntry.text()

    window.commandEntry.setText("")
    callsign = text.split(" ")[0]

    if callsign == "tm":  # time multiplier
        global timeMultiplier
        timeMultiplier = float(text.split(" ")[1])
        return

    for plane in planes:
        if plane.callsign == callsign:
            break
    else:
        print("Callsign not found")
        return

    baseCommand = text.split(" ")[1]

    errorText = ""

    try:
        match baseCommand:
            case "d":
                plane.targetAltitude = int(text.split(" ")[2]) * 100
                plane.vertSpeed = -2000
            case "c":
                plane.targetAltitude = int(text.split(" ")[2]) * 100
                plane.vertSpeed = 2000
            case "tl":
                if plane.holdStartTime is not None:  # end holding
                    plane.holdStartTime = None
                plane.mode = "HDG"
                plane.targetHeading = int(text.split(" ")[2]) % 360
                plane.turnDir = "L"
                # plane.heading = int(text.split(" ")[2])
            case "tr":
                if plane.holdStartTime is not None:  # end holding
                    plane.holdStartTime = None
                plane.mode = "HDG"
                plane.targetHeading = int(text.split(" ")[2]) % 360
                plane.turnDir = "R"
                # plane.heading = int(text.split(" ")[2])
            case "sp":
                plane.targetSpeed = int(text.split(" ")[2])
            case "rond":
                if plane.mode == "FPL":
                    errorText = "Already following a flightplan"
                    raise _MatchException()
                
                found = False
                for i, fix in enumerate(plane.flightPlan.route.fixes):
                    if fix == text.split(" ")[2]:
                        plane.flightPlan.route.fixes = plane.flightPlan.route.fixes[i:]
                        found = True
                        break

                if not found:
                    errorText = "Fix not found"
                    raise _MatchException()
                
                plane.mode = "FPL"
                plane.flightPlan.route.initial = True
            case "pd":
                if plane.mode == "HDG":
                    errorText = "Currently on headings"
                    raise _MatchException()

                found = False
                for i, fix in enumerate(plane.flightPlan.route.fixes):
                    if fix == text.split(" ")[2]:
                        plane.flightPlan.route.fixes = plane.flightPlan.route.fixes[i:]
                        found = True
                        break
                
                if not found:
                    errorText = "Fix not found"
                    raise _MatchException()

                plane.flightPlan.route.initial = True
            case "sq":
                plane.squawk = int(text.split(" ")[2])
            case "hold":
                plane.holdFix = text.split(" ")[2]
            case "star":
                starData, extraFixes = loadStarAndFixData(text.split(" ")[3])
                FIXES.update(extraFixes)
                plane.flightPlan.route.fixes.extend(starData[text.split(" ")[2]]["26L"].split(" "))  # TODO: choose runway
            case "ils":
                if plane.mode == "FPL":
                    errorText = "Need headings to intercept"
                    raise _MatchException()
                
                runwayData = loadRunwayData("EGKK")[text.split(" ")[2]]  # TODO: choose airport
                plane.clearedILS = runwayData
            case "ho":
                if text.split(" ")[2] == "KKT":  # TODO: choose airport
                    index = planes.index(plane)
                    planes.remove(plane)
                    planeSocks.pop(index).close()
                    window.aircraftTable.removeRow(index)
            case _:
                errorText = "Unknown command"
    except _MatchException:
        pass

    if errorText != "":
        window.errorLabel.setText(errorText)


def callsignGen():
    return "G" + random.choice(string.ascii_uppercase) + random.choice(string.ascii_uppercase) + random.choice(string.ascii_uppercase) + random.choice(string.ascii_uppercase)


def squawkGen():
    return random.randint(3750, 3761)


# PLANE SPAWNING

def spawnEveryNSeconds(nSeconds, masterCallsign, controllerSock, method, *args, **kwargs):
    global planes, planeSocks, window

    timeWiggle = 0
    if method == "FIX":
        timeWiggle = random.randint(-10, 15)

    t = threading.Timer(nSeconds + timeWiggle, spawnEveryNSeconds, args=(nSeconds, masterCallsign, controllerSock, method, *args), kwargs=kwargs)
    t.daemon = True
    t.start()

    fp = kwargs["flightPlan"]
    kwargs.pop("flightPlan")

    if method == "FIX":
        plane = Plane.requestFromFix(callsignGen(), *args, **kwargs, flightPlan=FlightPlan.duplicate(fp), squawk=squawkGen())
    elif method == "DEP":
        plane = Plane.requestDeparture(callsignGen(), *args, **kwargs, flightPlan=FlightPlan.duplicate(fp), squawk=squawkGen())
    kwargs["flightPlan"] = fp
    planes.append(plane)
    planeSocks.append(startPlane(plane, masterCallsign, controllerSock))

    window.aircraftTable.setRowCount(len(planes))

    for i, plane in enumerate(planes):
        window.aircraftTable.setItem(i, 0, QTableWidgetItem(plane.callsign))
        window.aircraftTable.setItem(i, 1, QTableWidgetItem(str(plane.squawk)))
        window.aircraftTable.setItem(i, 2, QTableWidgetItem(str(plane.altitude)))
        window.aircraftTable.setItem(i, 3, QTableWidgetItem(str(int(round(plane.heading, 0)))))
        window.aircraftTable.setItem(i, 4, QTableWidgetItem(str(plane.speed)))
        window.aircraftTable.setItem(i, 5, QTableWidgetItem(str(plane.vertSpeed)))
        window.aircraftTable.setItem(i, 6, QTableWidgetItem(str(plane.lat)))
        window.aircraftTable.setItem(i, 7, QTableWidgetItem(str(plane.lon)))
        window.aircraftTable.setItem(i, 8, QTableWidgetItem(plane.flightPlan.route.fixes[0]))

# MAIN LOOP

planes: list[Plane] = []
planeSocks: list[socket.socket] = []
window: MainWindow = None
timeMultiplier: float = 1

def positionLoop(controllerSock):
    global planes, planeSocks, window
    t = threading.Timer(5, positionLoop, args=[controllerSock])
    t.daemon = True
    t.start()

    controllerSock.sendall(b'%' + b'LON_S_CTR' + b':29430:3:100:7:51.14806:-0.19028:0\r\n')  # TODO: choose correct controller

    for i, plane in enumerate(planes):
        planeSocks[i].sendall(plane.positionUpdateText())  # position update
        
        window.aircraftTable.setItem(i, 0, QTableWidgetItem(plane.callsign))
        window.aircraftTable.setItem(i, 1, QTableWidgetItem(str(plane.squawk)))
        window.aircraftTable.setItem(i, 2, QTableWidgetItem(str(plane.altitude)))
        window.aircraftTable.setItem(i, 3, QTableWidgetItem(str(int(round(plane.heading, 0)))))
        window.aircraftTable.setItem(i, 4, QTableWidgetItem(str(plane.speed)))
        window.aircraftTable.setItem(i, 5, QTableWidgetItem(str(plane.vertSpeed)))
        window.aircraftTable.setItem(i, 6, QTableWidgetItem(str(plane.lat)))
        window.aircraftTable.setItem(i, 7, QTableWidgetItem(str(plane.lon)))
        window.aircraftTable.setItem(i, 8, QTableWidgetItem(plane.flightPlan.route.fixes[0]))


def messageMonitor(controllerSock: socket.socket):
    t = threading.Timer(5, messageMonitor, args=[controllerSock])
    t.daemon = True
    t.start()

    socketReady = select.select([controllerSock], [], [], 1)
    if socketReady[0]:
        messages = controllerSock.recv(1024)
        messages = messages.decode("UTF-8").split("\r\n")
        messages.pop()
        for message in messages:
            if message.startswith("$HO"):
                callsign = message.split(":")[2]
                controllerSock.sendall(b'$CQ' + b'LON_S_CTR:@94835:HT:' + callsign.encode("UTF-8") + b':EGKK_APP\r\n')  # TODO: choose correct controller
            else:
                print(message)

        print()


def cellClicked(row, _col):
    window.commandEntry.setText(window.aircraftTable.item(row, 0).text() + " ")
    window.commandEntry.setFocus()

def main():
    global planes, planeSocks, window
    # SETUP PLANES

    masterCallsign = "LON_S_CTR"
    
    planes.append(Plane.requestDeparture("GASNE", "EGKK", flightPlan=FlightPlan("I", "B738", 250, "EGKK", 1130, 1130, 36000, "LFPG", Route("HARDY1X/26L HARDY M605 XIDIL UM605 BIBAX"))))
    
    controllerSock: socket.socket = startController(masterCallsign)
    controllerSock.setblocking(False)

    for i, plane in enumerate(planes):
        planeSocks.append(startPlane(plane, masterCallsign, controllerSock))
    
    # SETUP UI

    app = QtWidgets.QApplication(sys.argv)

    window = MainWindow()

    # # GATTERS 1: 
    # # ARRIVALS
    # # 10ph AMDUT1G
    # # 10ph VASUX1G
    # # 5ph SIRIC1G
    # # 10ph TELTU1G
    # # 5ph GWC1G
    # # 0ph KIDLI1G
    # threading.Timer(random.randint(1, 60), spawnEveryNSeconds, args=(3600 // 10, masterCallsign, controllerSock, "FIX", "SFD"), kwargs={"speed": 250, "altitude": 7000, "flightPlan": FlightPlan("I", "B738", 250, "EDDF", 1130, 1130, 36000, "EGKK", Route("SFD DCT WILLO")), "currentlyWithData": (masterCallsign, "WILLO")}).start()
    # threading.Timer(random.randint(60, 120), spawnEveryNSeconds, args=(3600 // 10, masterCallsign, controllerSock, "FIX", "TELTU"), kwargs={"speed": 250, "altitude": 8000, "flightPlan": FlightPlan("I", "B738", 250, "EDDF", 1130, 1130, 36000, "EGKK", Route("TELTU DCT HOLLY DCT WILLO")), "currentlyWithData": (masterCallsign, "HOLLY")}).start()
    # threading.Timer(random.randint(120, 180), spawnEveryNSeconds, args=(3600 // 5, masterCallsign, controllerSock, "FIX", "MID"), kwargs={"speed": 250, "altitude": 7000, "flightPlan": FlightPlan("I", "B738", 250, "EDDF", 1130, 1130, 36000, "EGKK", Route("MID DCT HOLLY DCT WILLO")), "currentlyWithData": (masterCallsign, "HOLLY")}).start()
    # threading.Timer(random.randint(180, 240), spawnEveryNSeconds, args=(3600 // 10, masterCallsign, controllerSock, "FIX", "TELTU"), kwargs={"speed": 250, "altitude": 9000, "flightPlan": FlightPlan("I", "B738", 250, "EDDF", 1130, 1130, 36000, "EGKK", Route("TELTU DCT SFD DCT TIMBA")), "currentlyWithData": (masterCallsign, "SFD")}).start()
    # threading.Timer(random.randint(240, 300), spawnEveryNSeconds, args=(3600 // 5, masterCallsign, controllerSock, "FIX", "GWC"), kwargs={"speed": 250, "altitude": 7000, "flightPlan": FlightPlan("I", "B738", 250, "EDDF", 1130, 1130, 36000, "EGKK", Route("GWC DCT HOLLY DCT WILLO")), "currentlyWithData": (masterCallsign, "HOLLY")}).start()

    # # DEPARTURES
    # a = threading.Timer(1, spawnEveryNSeconds, args=(450, masterCallsign, controllerSock, "DEP", "EGKK"), kwargs={"flightPlan": FlightPlan("I", "B738", 250, "EGKK", 1130, 1130, 25000, "LFPG", Route("HARDY1X/26L HARDY M605 XIDIL UM605 BIBAX"))})
    # a.daemon = True
    # a.start()
    # b = threading.Timer(90, spawnEveryNSeconds, args=(450, masterCallsign, controllerSock, "DEP", "EGKK"), kwargs={"flightPlan": FlightPlan("I", "B738", 250, "EGKK", 1130, 1130, 26000, "EGCC", Route("LAM6M/26L LAM N57 WELIN T420 ELVOS"))})
    # b.daemon = True
    # b.start()
    # c = threading.Timer(180, spawnEveryNSeconds, args=(450, masterCallsign, controllerSock, "DEP", "EGKK"), kwargs={"flightPlan": FlightPlan("I", "B738", 250, "EGKK", 1130, 1130, 35000, "EDDF", Route("MIMFO1M/26L MIMFO Y312 DVR UL9 KONAN UL607 KOK SPI T180 UNOKO"))})
    # c.daemon = True
    # c.start()
    # d = threading.Timer(270, spawnEveryNSeconds, args=(450, masterCallsign, controllerSock, "DEP", "EGKK"), kwargs={"flightPlan": FlightPlan("I", "B738", 250, "EGKK", 1130, 1130, 27000, "EHAM", Route("FRANE1M/26L FRANE M604 GASBA M197 REDFA"))})
    # d.daemon = True
    # d.start()
    # e = threading.Timer(360, spawnEveryNSeconds, args=(450, masterCallsign, controllerSock, "DEP", "EGKK"), kwargs={"flightPlan": FlightPlan("I", "B738", 250, "EGKK", 1130, 1130, 18000, "EGGD", Route("NOVMA1X/26L NOVMA L620 NIBDA N14 HEKXA Q63 SAWPE"))})
    # e.daemon = True
    # e.start()

    # Start message monitor
    threading.Timer(5, messageMonitor, args=[controllerSock]).start()

    
    window.aircraftTable.setRowCount(len(planes))
    for i, plane in enumerate(planes):
        window.aircraftTable.setItem(i, 0, QTableWidgetItem(plane.callsign))
        window.aircraftTable.setItem(i, 1, QTableWidgetItem(str(plane.squawk)))
        window.aircraftTable.setItem(i, 2, QTableWidgetItem(str(plane.altitude)))
        window.aircraftTable.setItem(i, 3, QTableWidgetItem(str(int(round(plane.heading, 0)))))
        window.aircraftTable.setItem(i, 4, QTableWidgetItem(str(plane.speed)))
        window.aircraftTable.setItem(i, 5, QTableWidgetItem(str(plane.vertSpeed)))
        window.aircraftTable.setItem(i, 6, QTableWidgetItem(str(plane.lat)))
        window.aircraftTable.setItem(i, 7, QTableWidgetItem(str(plane.lon)))
        window.aircraftTable.setItem(i, 8, QTableWidgetItem(plane.flightPlan.route.fixes[0]))

    window.commandEntry.returnPressed.connect(parseCommand)  # TODO: autofill callsign in text box
    window.aircraftTable.cellClicked.connect(cellClicked)
    window.show()

    # START POSITION LOOP
    positionLoop(controllerSock)

    # START UI
    app.exec()

    # CLEANUP ONCE UI IS CLOSED
    for planeSock in planeSocks:
        planeSock.close()

    controllerSock.close()

if __name__ == "__main__":
    main()
