import math
import time

from FlightPlan import FlightPlan
import util
from PlaneMode import PlaneMode
from globalVars import FIXES
from Constants import DESCENT_RATE, HIGH_DESCENT_RATE, TURN_RATE, ACTIVE_CONTROLLERS

class Plane:
    def __init__(self, callsign: str, squawk: int, altitude: int, heading: int, speed: float, lat: float, lon: float, vertSpeed: float, mode: PlaneMode, flightPlan: FlightPlan):  # onGround?
        self.callsign = callsign
        self.squawk = squawk
        self.altitude = altitude  # feet
        self.heading = heading  # 001 - 360
        self.speed = speed  # knots
        self.lat = lat  # decimal degrees
        self.lon = lon  # decimal degrees
        self.vertSpeed = vertSpeed  # feet per minute
        self.mode: PlaneMode = mode
        self.flightPlan = flightPlan  # fpln


        self.targetSpeed = speed
        self.targetAltitude = altitude
        self.targetHeading = heading
        self.turnDir = None
        self.holdFix = None
        self.holdStartTime = None

        self.clearedILS = None
        


        self.lastTime = time.time()

        # BOT stuff
        self.instructions = 0
        self.left_rma = False
        self.intercept_dist = None
        self.altitude_at_intercept = None
        self.close_calls = 0
        self.dist_from_behind = None
        self.distance_travelled = 0
        self.climbed = False
        self.sped_up = False
        self.vectored_out_rma = False # was it given ints outside the rma
        self.prev_lat,self.prev_lon = None,None
        self.start_distance = None
        self.maxd = None
        self.d_clappd = None


    def calculatePosition(self):
        self.prev_lat,self.prev_lon = self.lat,self.lon
        deltaT = 5
        

        tas = self.speed * (1 + (self.altitude / 1000) * 0.02)  # true airspeed

        


        if self.targetSpeed != self.speed and (self.mode == PlaneMode.HEADING or self.mode == PlaneMode.FLIGHTPLAN):
            if self.altitude < 2000 and self.vertSpeed > 0:  # below 2000ft, prioritise climbing over accelerating
                self.altitude += self.vertSpeed * (deltaT / 60)
                self.altitude = round(self.altitude, 0)
            elif 1.5 * deltaT > abs(self.targetSpeed - self.speed):  # otherwise, speed logic
                self.speed = self.targetSpeed
            elif self.targetSpeed > self.speed:
                self.speed += 1.5 * deltaT  # 0.5kts / sec
                self.altitude += (self.vertSpeed * (deltaT / 60)) / 2  # 1/2 climb rate
                self.altitude = round(self.altitude, 0)
            elif self.targetSpeed < self.speed:
                self.speed -= 1.5 * deltaT
                self.altitude += (self.vertSpeed * (deltaT / 60)) / 2  # 1/2 climb rate
                self.altitude = round(self.altitude, 0)

            self.speed = round(self.speed, 0)

        else:  # can only fully change altitude if speed is constant (somewhat bad energy conservation model but whatever)
            self.altitude += self.vertSpeed * (deltaT / 60)
            self.altitude = round(self.altitude, 0)

        if self.altitude < 10000 and self.vertSpeed == HIGH_DESCENT_RATE:
            self.vertSpeed = DESCENT_RATE

        if self.vertSpeed > 0 and self.altitude >= self.targetAltitude:
            self.vertSpeed = 0
            self.altitude = self.targetAltitude
        elif self.vertSpeed < 0 and self.altitude <= self.targetAltitude:
            self.vertSpeed = 0
            self.altitude = self.targetAltitude


        tas = self.speed * (1 + (self.altitude / 1000) * 0.02)  # true airspeed - recalculate

        if self.mode == PlaneMode.ILS:
            deltaLat, deltaLon = util.deltaLatLonCalc(self.lat, tas, self.heading, deltaT)

            distanceOut = util.haversine(self.lat, self.lon, self.clearedILS[1][0], self.clearedILS[1][1]) / 1.852  # nautical miles
            if self.intercept_dist == None:
                self.intercept_dist = distanceOut
            requiredAltitude = math.tan(math.radians(3)) * distanceOut * 6076  # feet
            if self.altitude_at_intercept == None:
                self.altitude_at_intercept = self.altitude

            if distanceOut < 4:
                if self.speed > 125:
                    self.speed -= 0.75 * deltaT
                if self.speed < 125:
                    self.speed = 125 
                
                self.speed = round(self.speed, 0)

            if self.altitude > requiredAltitude:
                if self.altitude - requiredAltitude > 1000:  # Joined ILS too high
                    print("GOAROUND")  # TODO
                self.altitude = requiredAltitude

            self.lat += deltaLat
            self.lat = round(self.lat, 5)
            self.lon += deltaLon
            self.lon = round(self.lon, 5)
        elif self.mode == PlaneMode.HEADING:
            if self.holdStartTime is not None:
                # NEW LOGIC: JUST ORBIT!
                if self.turnDir == "L":
                    self.heading -= TURN_RATE * deltaT
                else:
                    self.heading += TURN_RATE * deltaT
                self.targetHeading = self.heading
                # if time.time() - self.holdStartTime >= 30:  # 30 sec hold legs
                #     self.holdStartTime = time.time()
                #     self.targetHeading += 180
                #     self.targetHeading = self.targetHeading % 360
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

            deltaLat, deltaLon = util.deltaLatLonCalc(self.lat, tas, self.heading, deltaT)

            if self.clearedILS is not None:
                hdgToRunway = util.headingFromTo((self.lat, self.lon), self.clearedILS[1])
                newHdgToRunway = util.headingFromTo((self.lat + deltaLat, self.lon + deltaLon), self.clearedILS[1])
                if (hdgToRunway < self.clearedILS[0] < newHdgToRunway) or (hdgToRunway > self.clearedILS[0] > newHdgToRunway):
                    self.mode = PlaneMode.ILS
                    self.heading = self.clearedILS[0]

            self.lat += deltaLat
            self.lat = round(self.lat, 5)
            self.lon += deltaLon
            self.lon = round(self.lon, 5)

           
        elif self.mode == PlaneMode.FLIGHTPLAN:
            distanceToTravel = tas * (deltaT / 3600)
            try:
                nextFixCoords = FIXES[self.flightPlan[0]]
            except IndexError:
                self.mode = PlaneMode.HEADING
            distanceToFix = util.haversine(self.lat, self.lon, nextFixCoords[0], nextFixCoords[1]) / 1.852  # nautical miles

            if distanceToFix <= distanceToTravel:
                distanceFrac = 1 - (distanceToFix / distanceToTravel)
                deltaT *= distanceFrac  # so later lerp is still correct
                self.lat = nextFixCoords[0]
                self.lon = nextFixCoords[1]
                self.flightPlan.pop(0)

                try:
                    nextFixCoords = FIXES[self.flightPlan[0]]
                except IndexError:
                    self.mode = PlaneMode.HEADING
                    return
            elif distanceToFix < 1.2 and self.holdFix is None:  # don't TP but do mark fix as passed
                self.flightPlan.pop(0)
                
                try:
                    nextFixCoords = FIXES[self.flightPlan[0]]
                except IndexError:
                    self.mode = PlaneMode.HEADING
                    return

            self.targetHeading = util.headingFromTo((self.lat, self.lon), nextFixCoords)  # always recalculate heading

            if self.targetHeading != self.heading:  # HDG logic
                if TURN_RATE * deltaT > abs(self.targetHeading - self.heading):
                    self.heading = self.targetHeading
                    if self.holdStartTime is not None:
                        self.holdStartTime = time.time()
                elif 360 - (self.heading - self.targetHeading) % 360 < 180:  # hopefully my sketchy maths works!
                    self.heading += TURN_RATE * deltaT
                else:
                    self.heading -= TURN_RATE * deltaT

                self.heading = (self.heading + 360) % 360

            deltaLat, deltaLon = util.deltaLatLonCalc(self.lat, tas, self.heading, deltaT)

            self.lat += deltaLat
            self.lat = round(self.lat, 5)
            self.lon += deltaLon
            self.lon = round(self.lon, 5)


        self.distance_travelled += abs(util.haversine(self.lat,self.lon,self.prev_lat,self.prev_lon)/1.852)
            
