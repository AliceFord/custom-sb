import math
import shelve
import time
import random
from FlightPlan import FlightPlan
from Route import Route
import util
from sfparser import loadRunwayData
import taxiCoordGen
from PlaneMode import PlaneMode
from globalVars import FIXES, GROUND_POINTS, STANDS, otherControllerSocks, planes, planeSocks, window
from Constants import ACTIVE_AERODROMES, AUTO_ASSUME, DESCENT_RATE, HIGH_DESCENT_RATE, TURN_RATE, ACTIVE_CONTROLLERS, VREF_TABLE,AIRPORT_ELEVATIONS, AIRCRAFT_PERFORMACE, timeMultiplier
from shapely.geometry import LineString

class Plane:
    def __init__(self, callsign: str, squawk: int, altitude: int, heading: int, speed: float, lat: float, lon: float, vertSpeed: float, mode: PlaneMode, flightPlan: FlightPlan, currentlyWithData: tuple[str, str], firstController=None, stand=None):  # onGround?
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
        self.currentlyWithData = currentlyWithData  # (current controller, release point)

        self.firstController = firstController

        self.groundPosition = None
        self.groundRoute = None
        self.stand = stand
        self.firstGroundPosition = None

        self.targetSpeed = speed
        self.targetAltitude = altitude
        self.targetHeading = heading
        self.turnDir = None
        self.holdFix = None
        self.holdStartTime = None

        self.aircraftType = self.flightPlan.aircraftType
        self.vref = random.choice(list(VREF_TABLE[self.aircraftType]))
        self.oldAlt, self.oldHead = None, None

        self.masterSocketHandleData: tuple[util.EsSocket, str] = None
        self.clearedILS = None
        self.runwayHeading = None

        self.currentSector = util.whichSector(self.lat, self.lon, self.altitude)

        self.lastTime = time.time()

        self.dieOnReaching2K = False
        self.lvlCoords = None

        # if AUTO_ASSUME:
        #     if self.mode == PlaneMode.FLIGHTPLAN or self.mode == PlaneMode.HEADING:  # take aircraft
        #         index = util.otherControllerIndex(self.currentSector)
        #         if index is None:
        #             return
        #         controllerSock = otherControllerSocks[index]
        #         # 10 second delay 

        #         util.PausableTimer(11, controllerSock.esSend, args=["$CQ" + self.currentSector, "@94835", "IT", callsign])

    def calculatePosition(self):
        deltaT = (time.time() - self.lastTime) * timeMultiplier
        self.lastTime = time.time()

        tas = self.speed * (1 + (self.altitude / 1000) * 0.02)  # true airspeed

        # if self.altitude > 10000 and self.targetSpeed != 350:  # send it
        #     self.targetSpeed = 350
        
        # if self.altitude < 10000 and self.targetSpeed > 250:
        #     self.targetSpeed = 250
        if self.altitude != self.targetAltitude:
            sorted_alts = sorted(AIRCRAFT_PERFORMACE[self.aircraftType])
            for alt in sorted_alts: # TODO optimise
                if self.altitude < int(alt)*100:
                    break
            if self.targetAltitude > self.altitude: #climb
                self.vertSpeed = int(AIRCRAFT_PERFORMACE[self.aircraftType][alt][-2])
            elif self.targetAltitude < self.altitude: #desc
                self.vertSpeed = int(AIRCRAFT_PERFORMACE[self.aircraftType][alt][-1]) * -1


        if self.dieOnReaching2K and self.altitude <= 2000:  # time to die
            index = planes.index(self)
            planes.remove(self)
            sock = planeSocks.pop(index)
            sock.esSend("#DP" + self.callsign, "SERVER")
            sock.close()
            # window.aircraftTable.removeRow(index)
            return
        
        if self.lvlCoords is not None and self.mode == PlaneMode.FLIGHTPLAN:
            approxDistToLevel = util.haversine(self.lat, self.lon, self.lvlCoords[0], self.lvlCoords[1]) / 1.852  # nautical miles
            if approxDistToLevel < 1:
                self.lvlCoords = None
                self.altitude = self.targetAltitude
            
            deltaAlt = self.targetAltitude - self.altitude  # feet
            approxTime = (approxDistToLevel / tas) * 60  # mins
            approxVertSpeed = deltaAlt / approxTime
            self.altitude += approxVertSpeed * (deltaT / 60)
            self.altitude = round(self.altitude, 0)

            if 1.5 * deltaT > abs(self.targetSpeed - self.speed):  # otherwise, speed logic
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

        elif self.targetSpeed != self.speed and (self.mode == PlaneMode.HEADING or self.mode == PlaneMode.FLIGHTPLAN):
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


        if self.altitude < 11000 and self.targetAltitude < 10000 and self.targetSpeed > 250:
            self.targetSpeed = 250

        if 10000 <= self.altitude <= 10500 and self.targetAltitude >= 10000 and self.targetSpeed <= 350:
            self.targetSpeed = 350

        if self.vertSpeed > 0 and self.altitude >= self.targetAltitude:
            self.vertSpeed = 0
            self.altitude = self.targetAltitude
        elif self.vertSpeed < 0 and self.altitude <= self.targetAltitude:
            self.vertSpeed = 0
            self.altitude = self.targetAltitude

        activateHoldMode = False

        tas = self.speed * (1 + (self.altitude / 1000) * 0.02)  # true airspeed - recalculate

        if self.mode == PlaneMode.ILS:
            deltaLat, deltaLon = util.deltaLatLonCalc(self.lat, tas, self.heading, deltaT)

            distanceOut = util.haversine(self.lat, self.lon, self.clearedILS[1][0], self.clearedILS[1][1]) / 1.852  # nautical miles
            requiredAltitude = (math.tan(math.radians(3)) * distanceOut * 6076) + AIRPORT_ELEVATIONS[self.flightPlan.destination]  # feet

            if self.speed > self.targetSpeed:
                self.speed -= 1.5 * deltaT
                self.speed = round(self.speed, 0)

            if distanceOut < 4:
                if self.speed > self.vref:
                    self.speed -= 0.75 * deltaT
                if self.speed < self.vref:
                    self.speed = self.vref
                            

            if self.altitude > requiredAltitude:
                if self.altitude - requiredAltitude > 1000:  # Joined ILS too high
                    print("GOAROUND")
                    self.mode = PlaneMode.HEADING
                    self.clearedILS = None
                    self.targetAltitude = 3000
                    self.targetHeading = self.heading
                    self.targetSpeed = 220
                else:
                    self.altitude = requiredAltitude
            
            if self.targetHeading != self.oldHead:
                self.mode = PlaneMode.HEADING
                self.clearedILS = None
                self.targetAltitude = 3000
                self.targetSpeed = 220
            if self.targetAltitude != self.oldAlt: # manual g/a
                self.mode = PlaneMode.HEADING
                self.clearedILS = None
                self.targetHeading = self.heading
                self.targetSpeed = 220
            

            self.lat += deltaLat
            self.lat = round(self.lat, 5)
            self.lon += deltaLon
            self.lon = round(self.lon, 5)
        elif self.mode == PlaneMode.HEADING:
            if self.holdStartTime is not None:
                # JUST ORBIT LOGIC:
                # if self.turnDir == "L":
                #     self.heading -= TURN_RATE * deltaT
                # else:
                #     self.heading += TURN_RATE * deltaT
                # self.targetHeading = self.heading
                if self.heading != self.targetHeading:
                    self.holdStartTime = time.time()

                elif time.time() - self.holdStartTime >= 55:  # 60 sec hold legs
                    print("TURN!")
                    self.holdStartTime = time.time()

                    holdPos = FIXES[self.holdFix]

                    if util.haversine(self.lat, self.lon, holdPos[0], holdPos[1]) < 0.5:  # 0.5nm from fix
                        if self.holdFix == "BIG":  # please don't do this
                            self.heading = 302
                            self.turnDir = "R"
                        elif self.holdFix == "LAM":
                            self.heading = 262
                            self.turnDir = "L"
                        elif self.holdFix == "BNN":
                            self.heading = 116
                            self.turnDir = "R"
                        elif self.holdFix == "OCK":
                            self.heading = 328
                            self.turnDir = "R"
                        elif self.holdFix == "TIMBA":
                            self.heading = 307
                            self.turnDir = "R"
                        elif self.holdFix == "WILLO":
                            self.heading = 284
                            self.turnDir = "L"
                        elif self.holdFix == "JACKO":
                            self.heading = 264
                            self.turnDir = "L"
                        elif self.holdFix == "GODLU":
                            self.heading = 309
                            self.turnDir = "R"
                        elif self.holdFix == "DAYNE":
                            self.heading = 311
                            self.turnDir = "R"
                        elif self.holdFix == "ROSUN":
                            self.heading = 172
                            self.turnDir = "R"
                        elif self.holdFix == "MIRSI":
                            self.heading = 61
                            self.turnDir = "R"
                        elif self.holdFix == "TARTN":
                            self.heading = 15
                            self.turnDir = "L"
                        elif self.holdFix == "STIRA":
                            self.heading = 233
                            self.turnDir = "R"
                        else:
                            self.heading = 307
                            self.turnDir = "R"

                        self.targetHeading = self.heading

                        self.lat = holdPos[0]
                        self.lon = holdPos[1]
                    
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

            deltaLat, deltaLon = util.deltaLatLonCalc(self.lat, tas, self.heading, deltaT)
            snap = False
            if self.clearedILS is not None:
                hdgToRunway = util.headingFromTo((self.lat, self.lon), self.clearedILS[1])
                newHdgToRunway = util.headingFromTo((self.lat + deltaLat, self.lon + deltaLon), self.clearedILS[1])
                angleDiff = (self.runwayHeading - self.heading)%360
                print(f"{self.callsign}, angle diff {angleDiff}")
                if angleDiff >180:
                    angleDiff-=360
                angleToTurn = abs(angleDiff)
                timeToTurn = angleToTurn / TURN_RATE
                if self.speed != self.targetSpeed:
                    distanceToTurn = self.targetSpeed * (timeToTurn / 3600) # overshoot rather than undershoot
                else:
                    distanceToTurn = self.speed * (timeToTurn / 3600)
                print(distanceToTurn)
                headingLine = LineString([(self.lat,self.lon),util.pbd(self.lat,self.lon,self.heading,100)])
                runwayLine = LineString([self.clearedILS[1],util.pbd(self.clearedILS[1][0],self.clearedILS[1][1], (self.runwayHeading+180)%360,100)])
                if headingLine.intersects(runwayLine):
                    intersection_point = headingLine.intersection(runwayLine)
                    distToRun = util.haversine(self.lat,self.lon,intersection_point.y,intersection_point.x)/1.852
                    if distanceToTurn < distToRun:
                        disToMove = util.haversine(self.lat,self.lon,self.lat+deltaLat,self.lon+deltaLon)
                        if distToRun - disToMove < distanceToTurn:
                            if abs(angleDiff) > 20:
                                if angleDiff > 0:
                                    self.targetHeading = (self.runwayHeading + 20)%360
                                else:
                                    self.targetHeading = (self.runwayHeading - 20)%360
                            self.targetHeading = self.runwayHeading

                if (hdgToRunway < self.runwayHeading < newHdgToRunway) or (hdgToRunway > self.runwayHeading > newHdgToRunway):
                    new_dist_to_runway = abs(util.haversine(self.lat+deltaLat, self.lon+deltaLon, self.clearedILS[1][0],self.clearedILS[1][1]))  / 1.852 # in NM
                    itx_lat,itx_lon = util.pbd(self.clearedILS[1][0],self.clearedILS[1][1], (self.runwayHeading+180)%360,new_dist_to_runway)
                    diff = abs(util.haversine(self.lat+deltaLat, self.lon+deltaLon,itx_lat,itx_lon)) / 1.852
                    new_dist_to_runway -= diff

                    self.lat,self.lon = util.pbd(self.clearedILS[1][0],self.clearedILS[1][1], (self.runwayHeading+180)%360,new_dist_to_runway)
                    self.mode = PlaneMode.ILS
                    self.heading = self.runwayHeading
                    self.oldAlt = self.targetAltitude
                    self.oldHead = self.targetHeading
                    snap = True

            if not snap:
                self.lat += deltaLat
                self.lat = round(self.lat, 5)
                self.lon += deltaLon
                self.lon = round(self.lon, 5)

            nextSector = util.whichSector(self.lat, self.lon, self.altitude)
            # if AUTO_ASSUME:
            #     if nextSector != self.currentSector and nextSector is not None:
            #         index = util.otherControllerIndex(self.currentSector)
            #         if index is not None:
            #             controllerSock = otherControllerSocks[index]
            #             if nextSector not in ACTIVE_CONTROLLERS:
            #                 util.PausableTimer(11, controllerSock.esSend, args=["$CQ" + nextSector, "@94835", "IT", self.callsign])
            #             else:  # pass em over
            #                 util.PausableTimer(5, controllerSock.esSend, args=["$HO" + self.currentSector, ACTIVE_CONTROLLERS[0], self.callsign])
                        
            #             self.currentSector = nextSector
        elif self.mode == PlaneMode.FLIGHTPLAN:
            distanceToTravel = tas * (deltaT / 3600)
            try:
                nextFixCoords = FIXES[self.flightPlan.route.fixes[0]]
            except IndexError:
                self.mode = PlaneMode.HEADING
            distanceToFix = util.haversine(self.lat, self.lon, nextFixCoords[0], nextFixCoords[1]) / 1.852  # nautical miles

            if self.currentlyWithData is not None:  # if we're on close to release point, hand off
                if self.currentlyWithData[1] == self.flightPlan.route.fixes[0] and distanceToFix <= 20:
                    self.currentlyWithData = None
                    if self.firstController is not None:
                        util.PausableTimer(11, self.masterSocketHandleData[0].esSend, args=["$HO" + self.masterSocketHandleData[1], self.firstController, self.callsign])
                    else:
                        util.PausableTimer(11, self.masterSocketHandleData[0].esSend, args=["$HO" + self.masterSocketHandleData[1], ACTIVE_CONTROLLERS[0], self.callsign])

            if self.holdFix is not None and self.flightPlan.route.fixes[0] == self.holdFix and distanceToFix <= distanceToTravel:
                activateHoldMode = True
            else:
                if distanceToFix <= distanceToTravel:
                    distanceFrac = 1 - (distanceToFix / distanceToTravel)
                    deltaT *= distanceFrac  # so later lerp is still correct
                    self.lat = nextFixCoords[0]
                    self.lon = nextFixCoords[1]
                    self.flightPlan.route.removeFirstFix()

                    try:
                        nextFixCoords = FIXES[self.flightPlan.route.fixes[0]]
                    except IndexError:
                        self.mode = PlaneMode.HEADING
                        return
                elif distanceToFix < 1.2 and self.holdFix is None:  # don't TP but do mark fix as passed
                    self.flightPlan.route.removeFirstFix()
                    
                    try:
                        nextFixCoords = FIXES[self.flightPlan.route.fixes[0]]
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

                if self.flightPlan.route.initial:
                    self.flightPlan.route.initial = False
                    self.heading = util.headingFromTo((self.lat, self.lon), nextFixCoords)

                deltaLat, deltaLon = util.deltaLatLonCalc(self.lat, tas, self.heading, deltaT)

                self.lat += deltaLat
                self.lat = round(self.lat, 5)
                self.lon += deltaLon
                self.lon = round(self.lon, 5)

                nextSector = util.whichSector(self.lat, self.lon, self.altitude)
                # if AUTO_ASSUME:
                #     if nextSector != self.currentSector and nextSector is not None:
                #         index = util.otherControllerIndex(self.currentSector)
                #         if index is not None:
                #             controllerSock = otherControllerSocks[index]
                #             if nextSector not in ACTIVE_CONTROLLERS:
                #                 util.PausableTimer(11, controllerSock.esSend, args=["$CQ" + nextSector, "@94835", "IT", self.callsign])
                #             else:
                #                 util.PausableTimer(5, controllerSock.esSend, args=["$HO" + self.currentSector, ACTIVE_CONTROLLERS[0], self.callsign])
                            
                #             self.currentSector = nextSector
        elif self.mode == PlaneMode.GROUND_STATIONARY:
            pass
        elif self.mode == PlaneMode.GROUND_TAXI:
            if self.groundRoute is None:
                self.mode = PlaneMode.GROUND_STATIONARY
                return

            try:
                if len(self.groundRoute) == 1 and self.groundRoute[0].startswith("STAND"):
                    self.mode = PlaneMode.GROUND_STATIONARY
                    self.stand = self.groundRoute[0].replace("STAND", "")
                    return
                elif len(self.groundRoute) == 1 and self.groundRoute[0].startswith("PUSH"):
                    self.mode = PlaneMode.GROUND_READY
                    self.stand = None
                    self.firstGroundPosition = taxiCoordGen.standDataParser()[self.groundRoute[0].replace("PUSH", "")][0]
                    return
            except AttributeError:
                pass

            distanceToTravel = self.speed * (deltaT / 3600)
            while distanceToTravel > 0:
                distanceToNext = util.haversine(self.lat, self.lon, self.groundRoute[0][0], self.groundRoute[0][1]) / 1.852
                if distanceToNext <= distanceToTravel:
                    deltaT *= 1 - (distanceToNext / distanceToTravel)  # so later lerp is still correct

                    distanceToTravel -= distanceToNext
                    self.lat = self.groundRoute[0][0]
                    self.lon = self.groundRoute[0][1]
                    self.groundRoute.pop(0)
                    if len(self.groundRoute) == 0:
                        self.mode = PlaneMode.GROUND_STATIONARY
                        return

                    try:
                        if self.groundRoute[0].startswith("STAND"):  # arrived at stand
                            self.mode = PlaneMode.GROUND_STATIONARY
                            self.stand = self.groundRoute[0].replace("STAND", "")
                            self.heading += 180
                            self.heading %= 360  # for stand logic handler
                            return
                    except AttributeError:
                        pass

                    try:
                        if self.groundRoute[0].startswith("PUSH"):  # departed from stand
                            self.mode = PlaneMode.GROUND_READY
                            self.stand = None
                            self.firstGroundPosition = taxiCoordGen.standDataParser()[self.groundRoute[0].replace("PUSH", "")][0]
                            return
                    except AttributeError:
                        pass

                else:
                    self.heading = util.headingFromTo((self.lat, self.lon), self.groundRoute[0])
                    deltaLat, deltaLon = util.deltaLatLonCalc(self.lat, self.speed, self.heading, deltaT)

                    self.lat += deltaLat
                    self.lat = round(self.lat, 5)
                    self.lon += deltaLon
                    self.lon = round(self.lon, 5)
                    return

        if activateHoldMode:
            self.holdStartTime = time.time() - 60  # !!!! DODGY !!!
            self.heading = 307
            self.targetHeading = 307
            self.mode = PlaneMode.HEADING
            self.turnDir = "R"
            if self.holdFix == "BIG":  # LL holds are coded
                self.heading = 302
                self.turnDir = "R"
            elif self.holdFix == "LAM":
                self.heading = 262
                self.turnDir = "L"
            elif self.holdFix == "BNN":
                self.heading = 116
                self.turnDir = "R"
            elif self.holdFix == "OCK":
                self.heading = 328
                self.turnDir = "R"
            elif self.holdFix == "TIMBA":  # KK holds
                self.heading = 307
                self.turnDir = "R"
            elif self.holdFix == "WILLO":
                self.heading = 284
                self.turnDir = "L"
            elif self.holdFix == "JACKO":  # THAMES holds
                self.heading = 264
                self.turnDir = "L"
            elif self.holdFix == "GODLU":
                self.heading = 309
                self.turnDir = "R"
            elif self.holdFix == "DAYNE":
                self.heading = 311
                self.turnDir = "R"
            elif self.holdFix == "ROSUN":
                self.heading = 172
                self.turnDir = "R"
            elif self.holdFix == "MIRSI":
                self.heading = 61
                self.turnDir = "R"
            elif self.holdFix == "TARTN":
                self.heading = 15
                self.turnDir = "L"
            elif self.holdFix == "STIRA":
                self.heading = 233
                self.turnDir = "R"
            else:
                print("Hold fix not found", self.holdFix)

            self.targetHeading = self.heading


    def positionUpdateText(self, calculatePosition=True) -> bytes:
        if calculatePosition:
            self.calculatePosition()
        displayHeading = self.heading
        if self.stand is not None or self.mode == PlaneMode.GROUND_READY:  # if we're pushing, display heading is 180 degrees off
            displayHeading += 180
            displayHeading %= 360

        return b'@N:' + self.callsign.encode("UTF-8") + b':' + str(self.squawk).encode("UTF-8") + b':1:' + str(self.lat).encode("UTF-8") + b':' + str(self.lon).encode("UTF-8") + b':' + str(self.altitude).encode("UTF-8") + b':' + str(self.speed).encode("UTF-8") + b':' + str(int((100 / 9) * displayHeading)).encode("UTF-8") + b':0\r\n'

    @classmethod
    def requestFromFix(cls, callsign: str, fix: str, squawk: int = 1234, altitude: int = 10000, heading: int = 0, speed: float = 0, vertSpeed: float = 0, flightPlan: FlightPlan = FlightPlan("I", "B738", 250, ACTIVE_AERODROMES[0], 1130, 1130, 36000, "EDDF", Route("MIMFO Y312 DVR L9 KONAN L607 KOK UL607 SPI T180 UNOKO", ACTIVE_AERODROMES[0])), currentlyWithData: str = None, firstController: str = None):
        try:
            coords = FIXES[fix]
        except KeyError:
            print("Fix not found", fix)
            coords = (51.15487, -0.16454)
        
        return cls(callsign, squawk, altitude, heading, speed, coords[0], coords[1], vertSpeed, PlaneMode.FLIGHTPLAN, flightPlan, currentlyWithData, firstController=firstController)
    
    @classmethod
    def requestBeforeFix(cls, callsign: str, fix1: str, fix2: str, squawk: int = 1234, altitude: int = 10000, heading: int = 0, speed: float = 0, vertSpeed: float = 0, flightPlan: FlightPlan = FlightPlan("I", "B738", 250, ACTIVE_AERODROMES[0], 1130, 1130, 36000, "EDDF", Route("MIMFO Y312 DVR L9 KONAN L607 KOK UL607 SPI T180 UNOKO", ACTIVE_AERODROMES[0])), currentlyWithData: str = None, firstController: str = None):
        try:
            coords1 = FIXES[fix1]
            coords2 = FIXES[fix2]
            coords = util.lerpBetweenCoords(coords1, coords2, -20 / (util.haversine(coords1[0], coords1[1], coords2[0], coords2[1]) / 1.852))
        except KeyError:
            print("Fix not found", fix1, fix2)
            coords = (51.15487, -0.16454)
                
        return cls(callsign, squawk, altitude, heading, speed, coords[0], coords[1], vertSpeed, PlaneMode.FLIGHTPLAN, flightPlan, currentlyWithData, firstController=firstController)

    @classmethod
    def requestFromGroundPoint(cls, callsign: str, groundPoint: str, squawk: int = 1234, flightPlan: FlightPlan = FlightPlan("I", "B738", 250, ACTIVE_AERODROMES[0], 1130, 1130, 36000, "EDDF", Route("MIMFO Y312 DVR L9 KONAN L607 KOK UL607 SPI T180 UNOKO", ACTIVE_AERODROMES[0]))):
        coords = GROUND_POINTS[groundPoint]
        return cls(callsign, squawk, 0, 0, 0, coords[0], coords[1], 0, PlaneMode.GROUND_STATIONARY, flightPlan, None)

    @classmethod
    def requestFromStand(cls, callsign: str, stand: str, squawk: int = 1234, flightPlan: FlightPlan = FlightPlan("I", "B738", 250, ACTIVE_AERODROMES[0], 1130, 1130, 36000, "EDDF", Route("MIMFO Y312 DVR L9 KONAN L607 KOK UL607 SPI T180 UNOKO", ACTIVE_AERODROMES[0]))):
        coords = STANDS[stand][1]
        heading = util.headingFromTo(coords[0], coords[1])  # will be flipped by stand logic
        return cls(callsign, squawk, 0, heading, 0, coords[0][0], coords[0][1], 0, PlaneMode.GROUND_STATIONARY, flightPlan, None, stand)

    @classmethod
    def requestDeparture(cls, callsign: str, airport: str, squawk: int = 1234, altitude: int = 600, heading: int = 0, speed: float = 150, vertSpeed: float = 2000, flightPlan: FlightPlan = FlightPlan("I", "B738", 250, ACTIVE_AERODROMES[0], 1130, 1130, 36000, "EDDF", Route("MIMFO Y312 DVR L9 KONAN L607 KOK UL607 SPI T180 UNOKO", ACTIVE_AERODROMES[0]))):
        # coords = loadRunwayData(airport)[ACTIVE_RUNWAY]   # TODO: Dynamic
        coords = list(loadRunwayData(airport).values())[0]
        return cls(callsign, squawk, altitude, heading, speed, coords[1][0], coords[1][1], vertSpeed, PlaneMode.FLIGHTPLAN, flightPlan, None)


if __name__ == "__main__":
    plane = Plane.requestFromFix("TEST", "MIMFO")
    with shelve.open("planes") as planes:
        planes[plane.callsign] = plane
