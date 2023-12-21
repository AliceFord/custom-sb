import math
import time
import socket

from FlightPlan import FlightPlan
from Route import Route
import util
from sfparser import loadRunwayData
from globals import *

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
            if self.altitude < 2000 and self.vertSpeed > 0:  # below 2000ft, prioritise climbing over accelerating
                self.altitude += self.vertSpeed * (deltaT / 60)
                self.altitude = round(self.altitude, 0)
            elif 0.5 * deltaT > abs(self.targetSpeed - self.speed):  # otherwise, speed logic
                self.speed = self.targetSpeed
            elif self.targetSpeed > self.speed:
                self.speed += 0.5 * deltaT  # 0.5kts / sec
                self.altitude += (self.vertSpeed * (deltaT / 60)) // 4  # 1/4th of the climb rate
                self.altitude = round(self.altitude, 0)
            elif self.targetSpeed < self.speed:
                self.speed -= 0.5 * deltaT
                self.altitude += (self.vertSpeed * (deltaT / 60)) // 4  # 1/4th of the climb rate
                self.altitude = round(self.altitude, 0)

            self.speed = round(self.speed, 0)
        
        else:  # can only fully change altitude if speed is constant (somewhat bad energy conservation model but whatever)

            self.altitude += self.vertSpeed * (deltaT / 60)
            self.altitude = round(self.altitude, 0)

        if self.vertSpeed > 0 and self.altitude >= self.targetAltitude:
            self.vertSpeed = 0
            self.altitude = self.targetAltitude
        elif self.vertSpeed < 0 and self.altitude <= self.targetAltitude:
            self.vertSpeed = 0
            self.altitude = self.targetAltitude

        activateHoldMode = False

        tas = self.speed * (1 + (self.altitude / 1000) * 0.02)  # true airspeed

        if self.mode == "ILS":
            deltaLat = (tas * math.cos(math.radians(self.heading)) * (deltaT / 3600)) / 60 # (nautical miles travelled) / 60
            deltaLon = (1/math.cos(math.radians(self.lat))) * (tas * math.sin(math.radians(self.heading)) * (deltaT / 3600)) / 60  # (1/math.cos(math.radians(self.lat))) for longitude stretching

            distanceOut = util.haversine(self.lat, self.lon, self.clearedILS[1][0], self.clearedILS[1][1]) / 1.852  # nautical miles
            requiredAltitude = math.tan(math.radians(3)) * distanceOut * 6076  # feet

            if self.altitude > requiredAltitude:
                if self.altitude - requiredAltitude > 1000:
                    print("GOAROUND")
                self.altitude = requiredAltitude
                
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
                if TURN_RATE * deltaT > abs(self.targetHeading - self.heading):
                    self.heading = self.targetHeading
                    if self.holdStartTime is not None:
                        self.holdStartTime = time.time()
                elif self.turnDir == "L":
                    self.heading -= TURN_RATE * deltaT
                else:
                    self.heading += TURN_RATE * deltaT
                
                self.heading = (self.heading + 360) % 360

            deltaLat = (tas * math.cos(math.radians(self.heading)) * (deltaT / 3600)) / 60 # (nautical miles travelled) / 60
            deltaLon = (1/math.cos(math.radians(self.lat))) * (tas * math.sin(math.radians(self.heading)) * (deltaT / 3600)) / 60

            if self.clearedILS is not None:
                hdgToRunway = util.headingFromTo((self.lat, self.lon), self.clearedILS[1])
                newHdgToRunway = util.headingFromTo((self.lat + deltaLat, self.lon + deltaLon), self.clearedILS[1])
                if (hdgToRunway < self.clearedILS[0] < newHdgToRunway) or (hdgToRunway > self.clearedILS[0] > newHdgToRunway):
                    self.mode = "ILS"
                    self.heading = self.clearedILS[0]

            self.lat += deltaLat
            self.lat = round(self.lat, 5)
            self.lon += deltaLon
            self.lon = round(self.lon, 5)
        elif self.mode == "FPL":
            distanceToTravel = tas * (deltaT / 3600)
            nextFixCoords = FIXES[self.flightPlan.route.fixes[0]]
            distanceToFix = util.haversine(self.lat, self.lon, nextFixCoords[0], nextFixCoords[1]) / 1.852  # nautical miles

            if self.holdFix is not None and self.flightPlan.route.fixes[0] == self.holdFix and distanceToFix <= distanceToTravel:
                activateHoldMode = True
            else:
                if distanceToFix <= distanceToTravel:
                    distanceFrac = 1 - (distanceToFix / distanceToTravel)
                    deltaT *= distanceFrac  # so later lerp is still correct
                    self.lat = nextFixCoords[0]
                    self.lon = nextFixCoords[1]
                    self.flightPlan.route.removeFirstFix()

                    if self.currentlyWithData is not None:  # if we're on route to the release point, hand em off with some delay
                        if self.currentlyWithData[1] == self.flightPlan.route.fixes[0]:
                            util.DaemonTimer(11, self.masterSocketHandleData[0].sendall, args=[b'$HO' + self.masterSocketHandleData[1].encode("UTF-8") + b':' + ACTIVE_CONTROLLER.encode("UTF-8") + b':' + self.callsign.encode("UTF-8") + b'\r\n']).start()

                    nextFixCoords = FIXES[self.flightPlan.route.fixes[0]]
                    self.heading = util.headingFromTo((self.lat, self.lon), nextFixCoords)

                if self.flightPlan.route.initial:
                    self.flightPlan.route.initial = False
                    self.heading = util.headingFromTo((self.lat, self.lon), nextFixCoords)

                self.lat += (tas * math.cos(math.radians(self.heading)) * (deltaT / 3600)) / 60  # (nautical miles travelled) / 60
                self.lat = round(self.lat, 5)
                self.lon += (1/math.cos(math.radians(self.lat))) * (tas * math.sin(math.radians(self.heading)) * (deltaT / 3600)) / 60
                self.lon = round(self.lon, 5)

        if activateHoldMode:
            self.holdStartTime = time.time()
            self.targetHeading = 270
            self.mode = "HDG"
            self.turnDir = "L"


    def addPlaneText(self) -> bytes:
        return b'#AP' + self.callsign.encode("UTF-8") + b':SERVER:1646235:pass:1:9:1:Alice Ford\r\n'
    
    def positionUpdateText(self, calculatePosition=True) -> bytes:
        if calculatePosition:
            self.calculatePosition()
        return b'@N:' + self.callsign.encode("UTF-8") + b':' + str(self.squawk).encode("UTF-8") + b':1:' + str(self.lat).encode("UTF-8") + b':' + str(self.lon).encode("UTF-8") + b':' + str(self.altitude).encode("UTF-8") + b':' + str(self.speed).encode("UTF-8") + b':0:0\r\n'


    @staticmethod
    def requestFromFix(callsign: str, fix: str, squawk: int = 1234, altitude: int = 10000, heading: int = 0, speed: float = 0, vertSpeed: float = 0, flightPlan: FlightPlan = FlightPlan("I", "B738", 250, ACTIVE_AERODROME, 1130, 1130, 36000, "EDDF", Route("MIMFO Y312 DVR L9 KONAN L607 KOK UL607 SPI T180 UNOKO")), currentlyWithData: str = None):
        try:
            coords = FIXES[fix]
        except KeyError:
            print("Fix not found")
            coords = (51.15487, -0.16454)
        return Plane(callsign, squawk, altitude, heading, speed, coords[0], coords[1], vertSpeed, "FPL", flightPlan, currentlyWithData)
    
    @staticmethod
    def requestDeparture(callsign: str, airport: str, squawk: int = 1234, altitude: int = 600, heading: int = 0, speed: float = 150, vertSpeed: float = 2000, flightPlan: FlightPlan = FlightPlan("I", "B738", 250, ACTIVE_AERODROME, 1130, 1130, 36000, "EDDF", Route("MIMFO Y312 DVR L9 KONAN L607 KOK UL607 SPI T180 UNOKO"))):
        coords = loadRunwayData(airport)[ACTIVE_RUNWAY]
        return Plane(callsign, squawk, altitude, heading, speed, coords[1][0], coords[1][1], vertSpeed, "FPL", flightPlan, None)
