import datetime
import json
import random
import select
import shelve
import threading
import sys
import time
import keyboard
from Route import Route
import re
from pynput.keyboard import Key, Listener
import pyttsx3

from sfparser import loadRunwayData, loadStarAndFixData
from FlightPlan import FlightPlan
from Plane import Plane
from PlaneMode import PlaneMode
from globalVars import FIXES, planes, planeSocks, otherControllerSocks, messagesToSpeak, currentSpeakingAC, saveNow
from Constants import ACTIVE_CONTROLLERS, ACTIVE_RUNWAYS, HIGH_DESCENT_RATE, KILL_ALL_ON_HANDOFF, MASTER_CONTROLLER, MASTER_CONTROLLER_FREQ, OTHER_CONTROLLERS, RADAR_UPDATE_RATE, TAXI_SPEED, PUSH_SPEED, CLIMB_RATE, DESCENT_RATE, TRANSITION_LEVEL, AIRCRAFT_PERFORMACE
import Constants
import util
import taxiCoordGen
import sessionparser


class _TTS:   # https://stackoverflow.com/questions/56032027/pyttsx3-runandwait-method-gets-stuck
    engine = None
    def __init__(self) -> None:
        self.engine = pyttsx3.init()
    
    def start(self, text):
        self.engine.say(text)
        self.engine.runAndWait()

# COMMAND PARSING


class CommandErrorException(Exception):
    def __init__(self, message):
        self.message = message


def parseCommand(command: str = None):
    global planes, currentSpeakingAC
    # See command spec

    text = command
    callsign = text.split(" ")[0]

    if callsign == "tm":  # time multiplier
        global RADAR_UPDATE_RATE
        Constants.timeMultiplier = float(text.split(" ")[1])
        RADAR_UPDATE_RATE = 5 / Constants.timeMultiplier
        print("Time Multiplier set to", Constants.timeMultiplier)
        return
    elif callsign == "pause":
        for timer in util.PausableTimer.timers:
            timer.pause()
        return
    elif callsign == "resume":
        for timer in util.PausableTimer.timers:
            timer.restart()

        for plane in planes:
            plane.lastTime = time.time()
        return

    for plane in planes:
        if plane.callsign == callsign:
            break
    else:
        print("Callsign not found")
        return

    baseCommand = text.split(" ")[1]

    currentSpeakingAC = callsign

    try:
        match baseCommand:
            case "d":
                if plane.mode in PlaneMode.GROUND_MODES:
                    raise CommandErrorException("Cannot descend while on the ground")
                plane.targetAltitude = int(text.split(" ")[2]) * 100
                plane.vertSpeed = DESCENT_RATE

                # if plane.targetAltitude >= TRANSITION_LEVEL:
                #     messagesToSpeak.append(f"Descend flight level {' '.join(list(str(plane.targetAltitude // 100)))}")
                # else:
                #     messagesToSpeak.append(f"Descend altitude {' '.join(list(str(plane.targetAltitude // 100)))}")
            case "c":
                if plane.mode in PlaneMode.GROUND_MODES:
                    raise CommandErrorException("Cannot climb while on the ground")
                plane.targetAltitude = int(text.split(" ")[2]) * 100
                plane.vertSpeed = CLIMB_RATE

                # if plane.targetAltitude >= TRANSITION_LEVEL:
                #     messagesToSpeak.append(f"Climb flight level {' '.join(list(str(plane.targetAltitude // 100)))}")
                # else:
                #     messagesToSpeak.append(f"Climb altitude {' '.join(list(str(plane.targetAltitude // 100)))}")
            case "tl":
                if plane.mode in PlaneMode.GROUND_MODES:
                    raise CommandErrorException("Cannot change heading while on the ground")
                if plane.holdStartTime is not None:  # end holding
                    plane.holdStartTime = None
                plane.mode = PlaneMode.HEADING
                plane.targetHeading = int(text.split(" ")[2]) % 360
                plane.turnDir = "L"
                # plane.heading = int(text.split(" ")[2])

                # messagesToSpeak.append(f"Turn left heading {' '.join(list(str(plane.targetHeading).zfill(3)))}")
            case "tr":
                if plane.mode in PlaneMode.GROUND_MODES:
                    raise CommandErrorException("Cannot change heading while on the ground")
                if plane.holdStartTime is not None:  # end holding
                    plane.holdStartTime = None
                plane.mode = PlaneMode.HEADING
                plane.targetHeading = int(text.split(" ")[2]) % 360
                plane.turnDir = "R"

                # messagesToSpeak.append(f"Turn right heading {' '.join(list(str(plane.targetHeading).zfill(3)))}")
            case "r":
                if plane.mode in PlaneMode.GROUND_MODES:
                    raise CommandErrorException("Cannot change heading while on the ground")
                if plane.holdStartTime is not None:  # end holding
                    plane.holdStartTime = None
                plane.mode = PlaneMode.HEADING
                plane.targetHeading = plane.heading + int(text.split(" ")[2]) % 360
                plane.targetHeading = plane.targetHeading % 360
                plane.turnDir = "R"

                # messagesToSpeak.append(f"Turn right by {int(text.split(' ')[2]) % 360} degrees")
            case "l":
                if plane.mode in PlaneMode.GROUND_MODES:
                    raise CommandErrorException("Cannot change heading while on the ground")
                if plane.holdStartTime is not None:  # end holding
                    plane.holdStartTime = None
                plane.mode = PlaneMode.HEADING
                plane.targetHeading = plane.heading - int(text.split(' ')[2]) % 360
                plane.targetHeading = plane.targetHeading % 360
                plane.turnDir = "L"

                # messagesToSpeak.append(f"Turn left by {int(text.split(' ')[2]) % 360} degrees")
            case "sp":
                if plane.mode in PlaneMode.GROUND_MODES:
                    raise CommandErrorException("Ground speed is fixed")
                plane.targetSpeed = int(text.split(" ")[2])

                # messagesToSpeak.append(f"Speed {' '.join(list(str(plane.targetSpeed)))}")
            case "rond":
                if plane.mode == PlaneMode.FLIGHTPLAN:
                    raise CommandErrorException("Already following a flightplan")
                if plane.mode in PlaneMode.GROUND_MODES:
                    raise CommandErrorException("Cannot proceed to fix while on the ground")

                found = False
                for i, fix in enumerate(plane.flightPlan.route.fixes):
                    if fix == text.split(" ")[2]:
                        plane.flightPlan.route.fixes = plane.flightPlan.route.fixes[i:]
                        found = True
                        break

                if not found:
                    raise CommandErrorException("Fix not found")

                plane.mode = PlaneMode.FLIGHTPLAN

                # messagesToSpeak.append(f"Resume own navigation direct {text.split(' ')[2]}")
            case "pd":
                if plane.mode == PlaneMode.HEADING:
                    raise CommandErrorException("Currently on headings")
                if plane.mode in PlaneMode.GROUND_MODES:
                    raise CommandErrorException("Cannot proceed to fix while on the ground")

                found = False
                for i, fix in enumerate(plane.flightPlan.route.fixes):
                    if fix == text.split(" ")[2]:
                        plane.flightPlan.route.fixes = plane.flightPlan.route.fixes[i:]
                        found = True
                        break

                if not found:
                    raise CommandErrorException("Fix not found")

                # plane.flightPlan.route.initial = True

                # messagesToSpeak.append(f"Proceed direct {text.split(' ')[2]}")
            case "sq":
                plane.squawk = int(text.split(" ")[2])

                # messagesToSpeak.append(f"Squawk {list(' '.join(str(plane.squawk).zfill(4)))}")
            case "hold":
                if plane.mode in PlaneMode.GROUND_MODES:
                    raise CommandErrorException("Cannot enter hold while on the ground")
                plane.holdFix = text.split(" ")[2]

                # messagesToSpeak.append(f"Hold at {text.split(' ')[2]}")
            case "star":
                if plane.mode in PlaneMode.GROUND_MODES:
                    raise CommandErrorException("Cannot assign STAR while on the ground")
                starData, extraFixes = loadStarAndFixData(plane.flightPlan.destination)
                FIXES.update(extraFixes)
                plane.flightPlan.route.fixes.extend(starData[text.split(" ")[2]][ACTIVE_RUNWAYS[plane.flightPlan.destination]].split(" "))

                # messagesToSpeak.append(f"{text.split(' ')[2]} arrival")
            case "ils":
                if plane.mode in PlaneMode.GROUND_MODES:
                    raise CommandErrorException("Cannot assign ILS approach while on the ground")
                if plane.mode == PlaneMode.FLIGHTPLAN:
                    raise CommandErrorException("Need headings to intercept")
                try:
                    runwayData = loadRunwayData(plane.flightPlan.destination)
                    runway = ACTIVE_RUNWAYS[plane.flightPlan.destination]
                    recip = str((int(runway[:2]) + 18) % 36)
                    if len(recip) == 1:
                        recip = "0" + recip
                    if len(runway) == 3:
                        side = "L" if runway[-1] == "R" else "R"
                        recip += side
                    recip = runwayData[recip]
                    plane.clearedILS = runwayData[ACTIVE_RUNWAYS[plane.flightPlan.destination]]
                    plane.runwayHeading = util.headingFromTo(plane.clearedILS[1], recip[1])

                    # messagesToSpeak.append(f"Cleared ILS runway {ACTIVE_RUNWAYS[plane.flightPlan.destination]}")

                except FileNotFoundError:
                    print("F")
                except KeyError:
                    print("K")
                except Exception as e:
                    print(e)
            case "lvl":
                lvlFix = text.split(" ")[2]
                plane.lvlCoords = FIXES[lvlFix]

                # messagesToSpeak.append(f"Be level {lvlFix}")
            case "ho":  # BIN EM
                index = planes.index(plane)
                planes.remove(plane)
                sock = planeSocks.pop(index)
                sock.esSend("#DP" + plane.callsign, "SERVER")
                sock.close()
            case "hoai":
                plane.mode = PlaneMode.HEADING
                plane.targetAltitude = plane.altitude
                plane.vertSpeed = 0
                # plane.dieOnReaching2K = True
            case "taxi":
                if plane.mode not in PlaneMode.GROUND_MODES:
                    raise CommandErrorException("Plane is not currently in a state to taxi")
                points = text.split(" ")
                if points[2].startswith("/"):
                    hp = points[2]
                    points = " ".join(points[3:])
                else:
                    hp = "_" + points[-1][points[-1].find("/") + 1:]
                    points[-1] = points[-1][:points[-1].find("/")]
                    points = " ".join(points[2:])
                if plane.mode == PlaneMode.GROUND_READY:
                    closestPoint = plane.firstGroundPosition
                elif plane.mode == PlaneMode.GROUND_TAXI:
                    closestPoint = taxiCoordGen.nameOfPoint(plane.groundRoute[0])
                else:
                    closestPoint = taxiCoordGen.closestPoint(plane.lat, plane.lon)

                route = taxiCoordGen.getTaxiRoute(closestPoint, points, points[-1] + hp)

                plane.mode = PlaneMode.GROUND_TAXI
                plane.groundRoute = route
                plane.speed = TAXI_SPEED
            case "stand":
                if not (plane.mode == PlaneMode.GROUND_STATIONARY or plane.mode == PlaneMode.GROUND_TAXI):
                    raise CommandErrorException("Plane is not currently in a state to taxi into stand")
                points = text.split(" ")
                stand = points[2]
                points = " ".join(points[3:])
                if plane.mode == PlaneMode.GROUND_TAXI:
                    closestPoint = taxiCoordGen.nameOfPoint(plane.groundRoute[0])
                else:
                    closestPoint = taxiCoordGen.closestPoint(plane.lat, plane.lon)

                route = taxiCoordGen.getStandRoute(closestPoint, points, stand)
                plane.mode = PlaneMode.GROUND_TAXI
                plane.groundRoute = route + ["STAND" + stand]
                plane.speed = TAXI_SPEED
            case "push":
                if plane.mode != PlaneMode.GROUND_STATIONARY:
                    raise CommandErrorException("Currently moving")
                if plane.stand is None:
                    raise CommandErrorException("Not on stand")

                plane.mode = PlaneMode.GROUND_TAXI
                plane.groundRoute = taxiCoordGen.getPushRoute(plane.stand) + ["PUSH" + plane.stand]
                plane.speed = PUSH_SPEED
            case _:
                raise CommandErrorException("Unknown Command")
    except CommandErrorException as e:
        print(e.message)


# PLANE SPAWNING

def spawnRandomEveryNSeconds(nSeconds, variance, data):
    choice = random.choice(data)
    util.PausableTimer(random.uniform(nSeconds * (1 - variance), nSeconds * (1 + variance)) * (1/Constants.timeMultiplier), spawnRandomEveryNSeconds, args=(nSeconds, variance, data))
    spawnEveryNSeconds(nSeconds, choice["masterCallsign"], choice["controllerSock"], choice["method"], *choice["args"], callsign=None, spawnOne=True, **choice["kwargs"])


def spawnEveryNSeconds(nSeconds, masterCallsign, controllerSock, method, *args, callsign=None, spawnOne=False, **kwargs):
    global planes, planeSocks
    fp: FlightPlan = kwargs["flightPlan"]
    dest = fp.destination

    if callsign is None:
        callsign,aircraft_type = util.callsignGen(dest,[plane.callsign for plane in planes])
    else:
        for plane in planes:
            if plane.callsign == callsign:
                return  # nonono bug
    fp.aircraftType = aircraft_type
    timeWiggle = 0
    if method == "ARR" or method == "OVF":
        timeWiggle = random.randint(-30, 30)

    if not spawnOne:
        util.PausableTimer((nSeconds + timeWiggle) * (1/Constants.timeMultiplier), spawnEveryNSeconds, args=(nSeconds, masterCallsign, controllerSock, method, *args), kwargs=kwargs)

    kwargs.pop("flightPlan")

    hdg = -1
    if "hdg" in kwargs:
        hdg = kwargs["hdg"]
        kwargs.pop("hdg")

    if method == "ARR":
        plane = Plane.requestFromFix(callsign, *args, **kwargs, flightPlan=FlightPlan.duplicate(fp), squawk=util.squawkGen())
    elif method == "TR2":
        plane = Plane.requestBeforeFix(callsign, *args, **kwargs, flightPlan=FlightPlan.duplicate(fp), squawk=util.squawkGen())
    elif method == "OVF":
        plane = Plane.requestFromFix(callsign, *args, **kwargs, flightPlan=FlightPlan.duplicate(fp), squawk=util.squawkGen())
    elif method == "DEP":
        plane = Plane.requestDeparture(callsign, *args, **kwargs, flightPlan=FlightPlan.duplicate(fp), squawk=util.squawkGen())
        plane.targetAltitude = 5000  # climb it!
        plane.targetSpeed = 250
        plane.vertSpeed = CLIMB_RATE
        if hdg != -1:
            plane.heading = hdg
            plane.targetHeading = hdg
            plane.turnDir = "L"
            plane.mode = PlaneMode.HEADING
    elif method == "GPT":
        plane = Plane.requestFromGroundPoint(callsign, *args, **kwargs, flightPlan=FlightPlan.duplicate(fp), squawk=util.squawkGen())
    elif method == "STD":
        plane = Plane.requestFromStand(callsign, *args, **kwargs, flightPlan=FlightPlan.duplicate(fp), squawk=util.squawkGen())
    
    kwargs["flightPlan"] = fp
    planes.append(plane)
    sock = util.PlaneSocket.StartPlane(plane, masterCallsign, controllerSock)

    planeSocks.append(sock)

# MAIN LOOP


def positionLoop(controllerSock: util.ControllerSocket):
    global planes
    # util.PausableTimer(RADAR_UPDATE_RATE, positionLoop, args=[controllerSock])

    controllerSock.esSend("%" + MASTER_CONTROLLER, MASTER_CONTROLLER_FREQ, "3", "100", "7", "51.14806", "-0.19028", "0")

    for i, otherControllerSock in enumerate(otherControllerSocks):  # update controller pos
        otherControllerSock.esSend("%" + OTHER_CONTROLLERS[i][0], OTHER_CONTROLLERS[i][1], "3", "100", "7", "51.14806", "-0.19028", "0")

    for i, plane in enumerate(planes):  # update plane pos
        try:
            planeSocks[i].sendall(plane.positionUpdateText())  # position update
        except OSError:
            pass  # probably means we've just killed them. If not then lol
        except IndexError:
            pass  # probably means we've just killed them. If not then lol


    print()

    messageMonitor(controllerSock)


def messageMonitor(controllerSock: util.ControllerSocket) -> None:
    global saveNow
    # t = threading.Timer(RADAR_UPDATE_RATE, messageMonitor, args=[controllerSock])  # regular timer as should never be paused
    # t.daemon = True
    # t.start()

    socketReady = select.select([controllerSock], [], [], 1)  # 1 second timeout
    if socketReady[0]:
        messages = controllerSock.recv(5246000)  # 1024
        messages = messages.decode("UTF-8").split("\r\n")
        messages.pop()  # delete empty last message
        for message in messages:
            for contr in ACTIVE_CONTROLLERS:
                if message.startswith("$HO"):  # handoff
                    fromController = message.split(":")[0][3:]
                    toController = message.split(":")[1]
                    callsign = message.split(":")[2]
                    if fromController not in ACTIVE_CONTROLLERS:  # this caused pain
                        continue
                    if toController in ACTIVE_CONTROLLERS:  # don't auto accept if they're a human!
                        continue
                    controllerSock.esSend("$CQ" + MASTER_CONTROLLER, "@94835", "HT", callsign, toController)
                    for plane in planes:
                        if plane.callsign == callsign:
                            if toController.endswith("APP") or KILL_ALL_ON_HANDOFF:  # just drift off forever at current alt
                                parseCommand(f"{callsign} hoai")
                            
                            plane.currentlyWithData = (MASTER_CONTROLLER, None)
                            break
                elif message.startswith("$HA"):  # accept handoff
                    callsign = message.split(":")[2]
                    for plane in planes:
                        if plane.callsign == callsign:
                            plane.currentlyWithData = None
                            break
                elif message.startswith("$AM"):
                    cs = message.split(":")[2]
                    fp = message.split(":")[-1]
                    star = fp.split(" ")[-1]
                    if re.match(r'[A-Z]+\d[A-Z]\/\d+[LRC]*', star):
                        star = star.split("/")[0]
                        
                        parseCommand(f"{cs} star {star}")
                elif (m := re.match(r'^\$CQ' + contr + r':@94835:SC:(.*?):H([0-9]+)$', message)):  # heading
                    cs = m.group(1)
                    tgtHdg = int(m.group(2))

                    currentHdg = 0

                    for plane in planes:
                        if plane.callsign == cs:
                            currentHdg = plane.heading
                            break

                    if 0 < tgtHdg - currentHdg < 180 or tgtHdg - currentHdg < -180:
                        turnDir = "r"
                    else:
                        turnDir = "l"
                    
                    parseCommand(f"{cs} t{turnDir} {tgtHdg}")
                elif (m := re.match(r'^\$CQ' + contr + r':@94835:SC:(.*?):S([0-9]+)$', message)):
                    cs = m.group(1)
                    sp = int(m.group(2))

                    parseCommand(f"{cs} sp {sp}")
                elif (m := re.match(r'^\$CQ' + contr + r':@94835:SC:(.*?):M([0-9]+)$', message)):
                    cs = m.group(1)
                    spMach = int(m.group(2))
                    sp = int((spMach / 100) * (450 / 0.7842))  # lol dodgy

                    parseCommand(f"{cs} sp {sp}")
                elif (m := re.match(r'^\$CQ' + contr + r':@94835:DR:(.*?)$', message)):  # kill em
                    cs = m.group(1)
                    parseCommand(f"{cs} ho")
                elif (m := re.match(r'^\$CQ' + contr + r':@94835:.*?:(.*?):([A-Z]+)$', message)):
                    cs = m.group(1)
                    pd = m.group(2)

                    if pd == "":
                        continue

                    if pd == "ILS":
                        parseCommand(f"{cs} ils")
                        continue

                    if pd == "HOLD":
                        for plane in planes:
                            if plane.callsign == cs:
                                try:
                                    parseCommand(f"{cs} hold {plane.flightPlan.route.fixes[-1]}")
                                except IndexError:
                                    pass
                                continue


                    if re.match(r"LVL([A-Z]{3,5})", pd):
                        parseCommand(f"{cs} lvl {pd[3:]}")
                        continue

                    mode = "pd"
                    for plane in planes:
                        if plane.callsign == cs:
                            if plane.mode == PlaneMode.HEADING:
                                mode = "rond"
                            else:
                                mode = "pd"
                        
                            break
                    
                    parseCommand(f"{cs} {mode} {pd}")
                elif (m := re.match(r'^\$CQ' + contr + r':@94835:TA:(.*?):([0-9]+)$', message)):  # climb / descend
                    cs = m.group(1)
                    tgtAlt = int(m.group(2))

                    currentAlt = 0
                    exitNow = False

                    for plane in planes:
                        if plane.callsign == cs:
                            currentAlt = plane.altitude
                            if tgtAlt == 0:
                                tgtAlt = int(plane.flightPlan.cruiseAltitude)
                            if tgtAlt == 1:
                                parseCommand(f"{cs} ils")
                                exitNow = True
                            break

                    if exitNow:
                        continue

                    if currentAlt == tgtAlt:
                        continue
                    elif tgtAlt > currentAlt:
                        cd = "c"
                    else:
                        cd = "d"

                    parseCommand(f"{cs} {cd} {tgtAlt // 100}")
                elif (m := re.match(r'^\$CQ' + contr + r':@94835:BC:(.*?):([0-9]{4})$', message)):  # set squawk
                    cs = m.group(1)
                    sq = m.group(2)

                    if sq == "7000":
                        continue

                    parseCommand(f"{cs} sq {sq}")
                elif message.startswith("#TM"):
                    cs = message.split(":")[2]
                    save = ""
                    try:
                        save = cs.split(", ")[1]
                    except IndexError:
                        pass

                    if save == "save":
                        saveNow = True
                    elif save.startswith("tm"):
                        parseCommand(save)
                    else:
                        for plane in planes:
                            if plane.callsign == cs:
                                parseCommand(f"{cs} c 30")
                else:
                    pass


def stdArrival(masterCallsign, controllerSock, ad, delay, planLvlData, variance=0, withMaster=True):
    parsedData = []
    for currentData in planLvlData:
        route, lvl, ctrl = currentData

        spd = 250
        if lvl > 30000:
            spd = 450
        elif lvl > 10000:
            spd = 350
        elif lvl < 5000:
            spd = 220

        if withMaster:
            parsedData.append({"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": [route.split(" ")[0]], "kwargs": {"speed": spd, "altitude": lvl, "flightPlan": FlightPlan.arrivalPlan(ad, route,"A20N"), "currentlyWithData": (masterCallsign, route.split(" ")[2]), "firstController": ctrl}})
        else:
            parsedData.append({"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": [route.split(" ")[0]], "kwargs": {"speed": spd, "altitude": lvl, "flightPlan": FlightPlan.arrivalPlan(ad, route,"A20N"), "firstController": ctrl}})
    util.PausableTimer(random.uniform(0, delay), spawnRandomEveryNSeconds, args=(delay, variance, parsedData))
    
    #         parsedData.append({"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": [route.split(" ")[0]], "kwargs": {"speed": spd, "altitude": lvl, "flightPlan": FlightPlan.arrivalPlan(ad, route), "firstController": ctrl}})
    # util.PausableTimer(random.uniform(0, delay) * (1/Constants.timeMultiplier), spawnRandomEveryNSeconds, args=(delay, variance, parsedData))

def stdDeparture(masterCallsign, controllerSock, ad, delay, planLvlData):
    parsedData = []
    for currentData in planLvlData:
        route, arrAd = currentData
        
        cruiseLvl = 25000
        if not arrAd.startswith("EG"):
            cruiseLvl = 36000
        parsedData.append({"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "DEP", "args": [ad], "kwargs": {"flightPlan": FlightPlan("I", "B738", 250, ad, 1130, 1130, cruiseLvl, arrAd, Route(route, ad))}})
    util.PausableTimer(random.uniform(0, delay) * (1/Constants.timeMultiplier), spawnRandomEveryNSeconds, args=(delay, 0, parsedData))


def stdTransit(masterCallsign, controllerSock, delay, data, withMaster=True):
    parsedData = []
    for currentData in data:
        depAd, arrAd, inLvl, filedLvl, route, ctrl = currentData
        spd = 250
        if inLvl > 30000:
            spd = 450
        elif inLvl > 10000:
            spd = 350

        if withMaster:
            parsedData.append({"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": [route.split(" ")[0]], "kwargs": {"speed": spd, "altitude": inLvl, "flightPlan": FlightPlan("I", "B738", 250, depAd, 1130, 1130, filedLvl, arrAd, Route(route, depAd, arrAd)), "currentlyWithData": (masterCallsign, route.split(" ")[2]), "firstController": ctrl}})
        else:
            parsedData.append({"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": [route.split(" ")[0]], "kwargs": {"speed": spd, "altitude": inLvl, "flightPlan": FlightPlan("I", "B738", 250, depAd, 1130, 1130, filedLvl, arrAd, Route(route, depAd, arrAd)), "firstController": ctrl}})

    util.PausableTimer(random.uniform(0, delay) * (1/Constants.timeMultiplier), spawnRandomEveryNSeconds, args=(delay, 0, parsedData))

def stdTransit2(masterCallsign, controllerSock, delay, data, withMaster=True):
    parsedData = []
    for currentData in data:
        depAd, arrAd, inLvl, filedLvl, route, ctrl = currentData
        spd = 250
        if inLvl > 30000:
            spd = 450
        elif inLvl > 10000:
            spd = 350

        if withMaster:
            parsedData.append({"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "TR2", "args": [route.split(" ")[0], route.split(" ")[2]], "kwargs": {"speed": spd, "altitude": inLvl, "flightPlan": FlightPlan("I", "B738", 250, depAd, 1130, 1130, filedLvl, arrAd, Route(route, depAd, arrAd)), "currentlyWithData": (masterCallsign, route.split(" ")[0]), "firstController": ctrl}})
        else:
            parsedData.append({"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "TR2", "args": [route.split(" ")[0], route.split(" ")[2]], "kwargs": {"speed": spd, "altitude": inLvl, "flightPlan": FlightPlan("I", "B738", 250, depAd, 1130, 1130, filedLvl, arrAd, Route(route, depAd, arrAd)), "firstController": ctrl}})

    util.PausableTimer(random.uniform(0, delay) * (1/Constants.timeMultiplier), spawnRandomEveryNSeconds, args=(delay, 0, parsedData))

def stdOverflight(masterCallsign, controllerSock, delay, data, withMaster=True):
    parsedData = []
    for currentData in data:
        depAd, arrAd, inLvl, filedLvl, route, ctrl = currentData
        spd = 250
        if inLvl > 30000:
            spd = 450
        elif inLvl > 10000:
            spd = 350

        if withMaster:
            parsedData.append({"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "OVF", "args": [route.split(" ")[0]], "kwargs": {"speed": spd, "altitude": inLvl, "flightPlan": FlightPlan("I", "B738", 250, depAd, 1130, 1130, filedLvl, arrAd, Route(route, depAd, arrAd)), "currentlyWithData": (masterCallsign, route.split(" ")[2]), "firstController": ctrl}})
        else:
            parsedData.append({"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "OVF", "args": [route.split(" ")[0]], "kwargs": {"speed": spd, "altitude": inLvl, "flightPlan": FlightPlan("I", "B738", 250, depAd, 1130, 1130, filedLvl, arrAd, Route(route, depAd, arrAd)), "firstController": ctrl}})

    util.PausableTimer(random.uniform(0, delay) * (1/Constants.timeMultiplier), spawnRandomEveryNSeconds, args=(delay, 0, parsedData))


def keyboardHandler():
    global messagesToSpeak, currentSpeakingAC
    while True:
        evt = keyboard.read_event()
        if evt.event_type == keyboard.KEY_UP and evt.name == "alt":
            time.sleep(5)  # LOLZ PILOTS ARE SLOW EH
            try:
                tts = _TTS()
                tts.start(" ".join(messagesToSpeak) + " " + currentSpeakingAC)
                del(tts)

                currentSpeakingAC = ""
                messagesToSpeak = []
            except NameError as e:
                print(e)
        

def main():
    global planes, planeSocks, ACTIVE_RUNWAYS, saveNow, ACTIVE_CONTROLLERS, OTHER_CONTROLLERS
    # SETUP PLANES

    masterCallsign = MASTER_CONTROLLER

    # shelving savestates\2024-06-04_21-05-55.242111.bak
    # with shelve.open("savestates/2024-06-25_20-30-19.355626") as f:
    # with shelve.open("savestates/2024-06-04_21-05-55.242111") as f:
    #     for plane in f.values():
    #         plane.lastTime = time.time()
    #         planes.append(plane)

    # planes.append(Plane.requestFromFix("EZY1", "SAM", squawk=util.squawkGen(), speed=250, altitude=5000, flightPlan=FlightPlan("I", "B738", 250, "EGHI", 1130, 1130, 37000, "EGBB", Route("SAM DCT NORRY Q41 SILVA"))))

    # planes.append(Plane.requestFromStand("EZY45", "2", flightPlan=FlightPlan("I", "B738", 250, "EGSS", 1130, 1130, 37000, "EHAM", Route("CLN P44 RATLO M197 REDFA"))))
    # planes.append(Plane.requestFromStand("DLH20W", "23", flightPlan=FlightPlan("I", "B738", 250, "EGSS", 1130, 1130, 37000, "EHAM", Route("CLN P44 RATLO M197 REDFA"))))
    # planes.append(Plane.requestFromStand("BAW22E", "12", flightPlan=FlightPlan("I", "B738", 250, "EGSS", 1130, 1130, 37000, "EHAM", Route("CLN P44 RATLO M197 REDFA"))))
    # planes.append(Plane.requestFromStand("TRA90P", "14", flightPlan=FlightPlan("I", "B738", 250, "EGSS", 1130, 1130, 37000, "EHAM", Route("CLN P44 RATLO M197 REDFA"))))

    # planes.append(Plane.requestFromGroundPoint("GASNE", "L/L3", flightPlan=FlightPlan("I", "B738", 250, "EHAM", 1130, 1130, 36000, "EGSS", Route("CLN"))))
    # planes.append(Plane.requestFromStand("GETCC", "2", flightPlan=FlightPlan("I", "B738", 250, "EGSS", 1130, 1130, 36000, "EHAM", Route("CLN P44 RATLO M197 REDFA"))))
    # planes.append(Plane.requestFromGroundPoint("GBMIV", "V/V1", flightPlan=FlightPlan("I", "B738", 250, "EGLL", 1130, 1130, 36000, "EIDW", Route("CPT L9 NICXI M17 VATRY"))))

    ## STANNERS !!!!!

    # for planeDef in sessionparser.parseFile("sessions/OBS_SS_PT2_Lesson2.txt"):  # TODO: move somewhere better
    #     pos = (planeDef[2], planeDef[3])
    #     closest = -1
    #     closestDist = 100000000
    #     for standNum, standPush in STANDS.items():
    #         coords = standPush[1][0]
    #         dist = util.haversine(float(pos[0]), float(pos[1]), coords[0], coords[1])
    #         if dist < closestDist:
    #             closestDist = dist
    #             closest = standNum

    #     plane = Plane.requestFromStand(planeDef[0], str(closest), flightPlan=FlightPlan(planeDef[5], planeDef[6], 420, planeDef[7], 1130, 1130, int(planeDef[8]), planeDef[9], Route(planeDef[10])))
    #     plane.heading = (int(int(planeDef[4]) * 9 / 100) + 180) % 360
    #     planes.append(plane)


    # GATTERS IN THE HOLD
    # llHoldFixes = ["TIMBA", "WILLO"]

    # for holdFix in llHoldFixes:
    #     for alt in range(8000, 8000 + 3 * 1000, 1000):
    #         plane = Plane.requestFromFix(util.callsignGen(), holdFix, squawk=util.squawkGen(), speed=220, altitude=alt, flightPlan=FlightPlan.arrivalPlan("EGKK", holdFix), currentlyWithData=(masterCallsign, holdFix))
    #         plane.holdFix = holdFix
    #         planes.append(plane)

    # HEATHROW IN THE HOLD

    # llHoldFixes = ["BIG", "OCK", "BNN", "LAM"]

    # for holdFix in llHoldFixes:
    #     for alt in range(8000, 10000 + 1 * 1000, 1000):
    #         cs,ac = util.callsignGen("EGLL",[plane.callsign for plane in planes])
    #         plane = Plane.requestFromFix(cs, holdFix, squawk=util.squawkGen(), speed=220, altitude=alt, flightPlan=FlightPlan.arrivalPlan("EGLL", holdFix,ac), currentlyWithData=(masterCallsign, holdFix))
    #         plane.holdFix = holdFix
    #         planes.append(plane)

    # llHoldFixes = ["ROSUN", "MIRSI", "DAYNE"]

    # for holdFix in llHoldFixes:
    #     for alt in range(7000, 9000 + 1 * 1000, 1000):
    #         callsign,ac_type = util.callsignGen("EGCC",[plane.callsign for plane in planes])
    #         plane = Plane.requestFromFix(callsign, holdFix, squawk=util.squawkGen(), speed=220, altitude=alt, flightPlan=FlightPlan.arrivalPlan("EGCC", holdFix), currentlyWithData=(masterCallsign, holdFix))
    # llHoldFixes = ["ABBOT"]

    # for holdFix in llHoldFixes:
    #     for alt in range(7000, 11000 + 1 * 1000, 1000):
    #         plane = Plane.requestFromFix(util.callsignGen(), holdFix, squawk=util.squawkGen(), speed=220, altitude=alt, flightPlan=FlightPlan.arrivalPlan("EGSS", holdFix))
    #         plane.holdFix = holdFix
    #         planes.append(plane)

    # LC IN THE HOLD

    # llHoldFixes = ["ROSUN", "MIRSI", "DAYNE"]

    # for holdFix in llHoldFixes:
    #     for alt in range(7000, 9000 + 1 * 1000, 1000):
    #         cs,ac_type = util.callsignGen("EGCC",[plane.callsign for plane in planes])
    #         plane = Plane.requestFromFix(cs, holdFix, squawk=util.squawkGen(), speed=220, altitude=alt, flightPlan=FlightPlan.arrivalPlan("EGCC", holdFix,ac_type), currentlyWithData=(masterCallsign, holdFix))
    #         plane.holdFix = holdFix
    #         planes.append(plane)

    # llHoldFixes = ["TARTN", "STIRA"]

    # for holdFix in llHoldFixes:
    #     for alt in range(7000, 9000 + 1 * 1000, 1000):
    #         cs,ac_type = util.callsignGen("EGPH",[plane.callsign for plane in planes])
    #         plane = Plane.requestFromFix(cs, holdFix, squawk=util.squawkGen(), speed=220, altitude=alt, flightPlan=FlightPlan.arrivalPlan("EGPH", holdFix,ac_type), currentlyWithData=(masterCallsign, holdFix))
    #         plane.holdFix = holdFix
    #         planes.append(plane)

    # llHoldFixes = ["PIGOT", "ROKUP"]
    # llHoldFixes = ["MIRSI", "DAYNE", "ROSUN"]

    # for holdFix in llHoldFixes:
    #     for alt in range(8000, 9000 + 1 * 1000, 1000):
    #         plane = Plane.requestFromFix(util.callsignGen(), holdFix, squawk=util.squawkGen(), speed=220, altitude=alt, flightPlan=FlightPlan.arrivalPlan("EGCC", holdFix))
    #         plane.holdFix = holdFix
    #         planes.append(plane)

    controllerSock: util.ControllerSocket = util.ControllerSocket.StartController(masterCallsign)
    controllerSock.setblocking(False)

    for plane in planes:
        planeSocks.append(util.PlaneSocket.StartPlane(plane, masterCallsign, controllerSock))

    # # DEPARTURES
    # util.PausableTimer(1, spawnEveryNSeconds, args=(540, masterCallsign, controllerSock, "DEP", "EGKK"), kwargs={"flightPlan": FlightPlan("I", "B738", 250, "EGKK", 1130, 1130, 25000, "LFPG", Route("HARDY1X/26L HARDY M605 XIDIL UM605 BIBAX"))})
    # util.PausableTimer(90, spawnEveryNSeconds, args=(540, masterCallsign, controllerSock, "DEP", "EGKK"), kwargs={"flightPlan": FlightPlan("I", "B738", 250, "EGKK", 1130, 1130, 26000, "EGCC", Route("LAM6M/26L LAM N57 WELIN T420 ELVOS"))})
    # util.PausableTimer(180, spawnEveryNSeconds, args=(540, masterCallsign, controllerSock, "DEP", "EGKK"), kwargs={"flightPlan": FlightPlan("I", "B738", 250, "EGKK", 1130, 1130, 18000, "EGGD", Route("NOVMA1X/26L NOVMA L620 NIBDA N14 HEKXA Q63 SAWPE"))})
    # util.PausableTimer(270, spawnEveryNSeconds, args=(540, masterCallsign, controllerSock, "DEP", "EGKK"), kwargs={"flightPlan": FlightPlan("I", "B738", 250, "EGKK", 1130, 1130, 35000, "EDDF", Route("MIMFO1M/26L MIMFO Y312 DVR UL9 KONAN UL607 KOK SPI T180 UNOKO"))})
    # util.PausableTimer(360, spawnEveryNSeconds, args=(540, masterCallsign, controllerSock, "DEP", "EGKK"), kwargs={"flightPlan": FlightPlan("I", "B738", 250, "EGKK", 1130, 1130, 27000, "LFAB", Route("BOGNA1X/26L BOGNA L612 BENBO UL612 XAMAB"))})
    # util.PausableTimer(450, spawnEveryNSeconds, args=(540, masterCallsign, controllerSock, "DEP", "EGKK"), kwargs={"flightPlan": FlightPlan("I", "B738", 250, "EGKK", 1130, 1130, 27000, "EHAM", Route("FRANE1M/26L FRANE M604 GASBA M197 REDFA"))})

    # GATTERS INT
    # util.PausableTimer(random.randint(1, 5), spawnEveryNSeconds, args=(60 * 5, masterCallsign, controllerSock, "ARR", "BOGNA"), kwargs={"speed": 250, "altitude": 13000, "flightPlan": FlightPlan.arrivalPlan("BOGNA DCT WILLO"), "currentlyWithData": (masterCallsign, "WILLO")})
    # util.PausableTimer(random.randint(120, 168), spawnEveryNSeconds, args=(60 * 5, masterCallsign, controllerSock, "ARR", "LYD"), kwargs={"speed": 250, "altitude": 13000, "flightPlan": FlightPlan.arrivalPlan("LYD DCT TIMBA"), "currentlyWithData": (masterCallsign, "TIMBA")})

    # stdArrival(masterCallsign, controllerSock, "EGKK", 90, [
    #     ["BOGNA DCT WILLO", 11000, "EGKK_APP"],
    #     ["LYD DCT TIMBA", 11000, "EGKK_APP"]
    # ])

    # stdArrival(masterCallsign, controllerSock, "EGKK", 75, [  # KK arrivals
    #     ["BOGNA DCT WILLO", 9000, "EGKK_APP"],
    #     ["LYD DCT TIMBA", 9000, "EGKK_APP"]
    # ], withMaster=False)

    # stdDeparture(masterCallsign, controllerSock, "EGKK", 130, [
    #     ["SFD4Z/08R SFD M605 XIDIL", "LFPG"]
    # ])

     # HEATHROW INT
    # stdArrival(masterCallsign, controllerSock, "EGLL", 75, [
    #     ["NOVMA DCT OCK", 11000, "EGLL_N_APP"],
    #     ["ODVIK DCT BIG", 11000, "EGLL_N_APP"],
    # HEATHROW INT
    # stdArrival(masterCallsign, controllerSock, "EGLL", 85, [
    #     ["NOVMA DCT OCK", 11000, "EGLL_S_APP"],
    #     ["ODVIK DCT BIG", 11000, "EGLL_S_APP"],
    #     ["BRAIN DCT LAM", 11000, "EGLL_N_APP"],
    #     ["COWLY DCT BNN", 11000, "EGLL_N_APP"],
    # ])


    # AA INT
    # timeBetween = 180  # s
    # N = 6
    # util.PausableTimer(random.randint(1, 5), spawnEveryNSeconds, args=(timeBetween * N, masterCallsign, controllerSock, "ARR", "PEPEG"), kwargs={"speed": 250, "altitude": 10000, "flightPlan": FlightPlan.arrivalPlan("PEPEG DCT ROBOP DCT IPSET DCT BELZU"), "currentlyWithData": (masterCallsign, "ROBOP")})
    # util.PausableTimer(random.randint(timeBetween - 20, timeBetween + 20), spawnEveryNSeconds, args=(timeBetween * N, masterCallsign, controllerSock, "ARR", "NOPKI"), kwargs={"speed": 250, "altitude": 10000, "flightPlan": FlightPlan.arrivalPlan("NOPKI DCT MATUT DCT ROBOP DCT IPSET DCT BELZU"), "currentlyWithData": (masterCallsign, "ROBOP")})
    # util.PausableTimer(random.randint(timeBetween * 2 - 20, timeBetween * 2 + 20), spawnEveryNSeconds, args=(timeBetween * N, masterCallsign, controllerSock, "ARR", "IOM"), kwargs={"speed": 250, "altitude": 10000, "flightPlan": FlightPlan.arrivalPlan("IOM DCT NELBO DCT BELZU"), "currentlyWithData": (masterCallsign, "NELBO")})
    # util.PausableTimer(random.randint(timeBetween * 3 - 20, timeBetween * 3 + 20), spawnEveryNSeconds, args=(timeBetween * N, masterCallsign, controllerSock, "ARR", "REMSI"), kwargs={"speed": 250, "altitude": 10000, "flightPlan": FlightPlan.arrivalPlan("REMSI DCT MASOP DCT NELBO DCT BELZU"), "currentlyWithData": (masterCallsign, "NELBO")})
    # util.PausableTimer(random.randint(timeBetween * 4 - 20, timeBetween * 4 + 20), spawnEveryNSeconds, args=(timeBetween * N, masterCallsign, controllerSock, "ARR", "NEVRI"), kwargs={"speed": 250, "altitude": 10000, "flightPlan": FlightPlan.arrivalPlan("NEVRI DCT ABSUN DCT BELZU"), "currentlyWithData": (masterCallsign, "ABSUN")})
    # util.PausableTimer(random.randint(timeBetween * 5 - 20, timeBetween * 5 + 20), spawnEveryNSeconds, args=(timeBetween * N, masterCallsign, controllerSock, "ARR", "TUNSO"), kwargs={"speed": 250, "altitude": 10000, "flightPlan": FlightPlan.arrivalPlan("TUNSO DCT BLACA DCT BELZU"), "currentlyWithData": (masterCallsign, "BLACA")})

    # util.PausableTimer(5, spawnRandomEveryNSeconds, args=(150, [
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["PEPEG"], "kwargs": {"speed": 250, "altitude": 10000, "flightPlan": FlightPlan.arrivalPlan("PEPEG DCT ROBOP DCT IPSET DCT BELZU"), "currentlyWithData": (masterCallsign, "ROBOP")}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["NOPKI"], "kwargs": {"speed": 250, "altitude": 10000, "flightPlan": FlightPlan.arrivalPlan("NOPKI DCT MATUT DCT ROBOP DCT IPSET DCT BELZU"), "currentlyWithData": (masterCallsign, "ROBOP")}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["IOM"], "kwargs": {"speed": 250, "altitude": 10000, "flightPlan": FlightPlan.arrivalPlan("IOM DCT NELBO DCT BELZU"), "currentlyWithData": (masterCallsign, "NELBO")}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["REMSI"], "kwargs": {"speed": 250, "altitude": 10000, "flightPlan": FlightPlan.arrivalPlan("REMSI DCT MASOP DCT NELBO DCT BELZU"), "currentlyWithData": (masterCallsign, "NELBO")}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["NEVRI"], "kwargs": {"speed": 250, "altitude": 10000, "flightPlan": FlightPlan.arrivalPlan("NEVRI DCT ABSUN DCT BELZU"), "currentlyWithData": (masterCallsign, "ABSUN")}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["TUNSO"], "kwargs": {"speed": 250, "altitude": 10000, "flightPlan": FlightPlan.arrivalPlan("TUNSO DCT BLACA DCT BELZU"), "currentlyWithData": (masterCallsign, "BLACA")}}
    # ]))

    # util.PausableTimer(5, spawnRandomEveryNSeconds, args=(120, [
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "DEP", "args": [ACTIVE_AERODROME], "kwargs": {"hdg": 250, "flightPlan": FlightPlan("I", "B738", 250, ACTIVE_AERODROME, 1130, 1130, 25000, "EHAM", Route("LISBO L603 PEPOD L15 HON L10 DTY L608 ADMIS M183 REDFA"))}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "DEP", "args": [ACTIVE_AERODROME], "kwargs": {"hdg": 250, "flightPlan": FlightPlan("I", "B738", 250, ACTIVE_AERODROME, 1130, 1130, 25000, "EHAM", Route("LISBO L603 PEPOD L15 HON L10 DTY L608 ADMIS M183 REDFA"))}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "DEP", "args": [ACTIVE_AERODROME], "kwargs": {"hdg": 250, "flightPlan": FlightPlan("I", "B738", 250, ACTIVE_AERODROME, 1130, 1130, 25000, "EHAM", Route("LISBO L603 PEPOD L15 HON L10 DTY L608 ADMIS M183 REDFA"))}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "DEP", "args": [ACTIVE_AERODROME], "kwargs": {"hdg": 250, "flightPlan": FlightPlan("I", "B738", 250, ACTIVE_AERODROME, 1130, 1130, 25000, "EIDW", Route("BELZU DCT NUMPI P620 NIMAT"))}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "DEP", "args": [ACTIVE_AERODROME], "kwargs": {"hdg": 250, "flightPlan": FlightPlan("I", "B738", 250, ACTIVE_AERODROME, 1130, 1130, 25000, "EGPH", Route("BLACA P600 TUNSO"))}}
    # ]))

    # NM INT
    # util.PausableTimer(5, spawnRandomEveryNSeconds, args=(180, [
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["EVSON"], "kwargs": {"speed": 250, "altitude": 8000, "flightPlan": FlightPlan.arrivalPlan("EVSON DCT DENBY DCT LBA"), "currentlyWithData": (masterCallsign, "LBA")}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["GIPLO"], "kwargs": {"speed": 250, "altitude": 9000, "flightPlan": FlightPlan.arrivalPlan("GIPLO DCT GOLES DCT BATLI DCT LBA"), "currentlyWithData": (masterCallsign, "GOLES")}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["BARTN"], "kwargs": {"speed": 250, "altitude": 8000, "flightPlan": FlightPlan.arrivalPlan("BARTN DCT HALIF DCT LBA"), "currentlyWithData": (masterCallsign, "HALIF")}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["CALDA"], "kwargs": {"speed": 250, "altitude": 8000, "flightPlan": FlightPlan.arrivalPlan("CALDA DCT POL DCT IPSIR"), "currentlyWithData": (masterCallsign, "IPSIR")}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["UVAVU"], "kwargs": {"speed": 250, "altitude": 8000, "flightPlan": FlightPlan.arrivalPlan("UVAVU DCT GASKO DCT POL"), "currentlyWithData": (masterCallsign, "GASKO")}}
    # ]))

    # util.PausableTimer(5, spawnRandomEveryNSeconds, args=(120, [
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "DEP", "args": [ACTIVE_AERODROME], "kwargs": {"flightPlan": FlightPlan("I", "B738", 250, ACTIVE_AERODROME, 1130, 1130, 15000, "EHAM", Route("POL2X/14 POL Y70 KOLID L70 PENIL L10 KELLY"))}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "DEP", "args": [ACTIVE_AERODROME], "kwargs": {"flightPlan": FlightPlan("I", "B738", 250, ACTIVE_AERODROME, 1130, 1130, 27000, "EHAM", Route("LAMIX2X/14 LAMIX L603 LAMSO"))}},
    # ]))

    # stdArrival(masterCallsign, controllerSock, "EGNM", 100, [
    #     ["EVSON DCT DENBY DCT LBA", 8000, "EGNM_APP"],
    #     ["GIPLO DCT GOLES DCT BATLI DCT LBA", 9000, "EGNM_APP"],
    #     ["BARTN DCT HALIF DCT LBA", 8000, "EGNM_APP"],
    #     ["CALDA DCT POL DCT IPSIR", 8000, "EGNM_APP"],
    #     ["UVAVU DCT GASKO DCT POL", 8000, "EGNM_APP"],
    # ])

    # stdDeparture(masterCallsign, controllerSock, "EGNM", 120, [
    #     ["POL2X/14 POL Y70 KOLID L70 PENIL L10 KELLY", "EHAM"],
    #     ["LAMIX2X/14 LAMIX L603 LAMSO", "EHAM"]
    # ])
    
    # SOLENT
    # util.PausableTimer(5, spawnRandomEveryNSeconds, args=(120, [
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["CPT"], "kwargs": {"speed": 250, "altitude": 9000, "flightPlan": FlightPlan.arrivalPlan("CPT DCT PEPIS DCT SAM"), "currentlyWithData": (masterCallsign, "PEPIS")}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["NOTGI"], "kwargs": {"speed": 250, "altitude": 9000, "flightPlan": FlightPlan.arrivalPlan("NOTGI DCT EVEXU DCT GIVUN DCT RUDMO DCT MIVLA DCT SAM"), "currentlyWithData": (masterCallsign, "EVEXU")}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["DOMUT"], "kwargs": {"speed": 250, "altitude": 11000, "flightPlan": FlightPlan.arrivalPlan("DOMUT DCT THRED DCT NEDUL"), "currentlyWithData": (masterCallsign, "THRED")}}
    # ]))

    # util.PausableTimer(5, spawnRandomEveryNSeconds, args=(120, [
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "DEP", "args": [ACTIVE_AERODROME], "kwargs": {"hdg": 200, "flightPlan": FlightPlan("I", "B738", 250, ACTIVE_AERODROME, 1130, 1130, 15000, "EHAM", Route("PEPIS Q41 NORRY"))}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "DEP", "args": [ACTIVE_AERODROME], "kwargs": {"hdg": 200, "flightPlan": FlightPlan("I", "B738", 250, ACTIVE_AERODROME, 1130, 1130, 27000, "EHAM", Route("GWC"))}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "DEP", "args": [ACTIVE_AERODROME], "kwargs": {"hdg": 200, "flightPlan": FlightPlan("I", "B738", 250, ACTIVE_AERODROME, 1130, 1130, 27000, "EHAM", Route("NEDUL Q41 ORTAC"))}}
    # ]))

    # JERSEY
    # util.PausableTimer(5, spawnRandomEveryNSeconds, args=(60, [
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["MARUK"], "kwargs": {"speed": 250, "altitude": 20000, "flightPlan": FlightPlan.arrivalPlan("EGJJ", "MARUK DCT LELNA DCT ALD"), "currentlyWithData": (masterCallsign, "LELNA")}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["VEXEN"], "kwargs": {"speed": 250, "altitude": 18000, "flightPlan": FlightPlan.arrivalPlan("EGJJ", "VEXEN DCT ORTAC DCT ALD"), "currentlyWithData": (masterCallsign, "ORTAC")}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["ENHEL"], "kwargs": {"speed": 250, "altitude": 21000, "flightPlan": FlightPlan.arrivalPlan("EGJJ", "ENHEL DCT SKERY DCT GUR"), "currentlyWithData": (masterCallsign, "SKERY")}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["KLAKI"], "kwargs": {"speed": 250, "altitude": 21000, "flightPlan": FlightPlan.arrivalPlan("EGJJ", "KLAKI DCT BIGNO DCT GUR"), "currentlyWithData": (masterCallsign, "BIGNO")}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["MARUK"], "kwargs": {"speed": 250, "altitude": 18000, "flightPlan": FlightPlan.arrivalPlan("EGJB", "MARUK DCT LELNA DCT ALD"), "currentlyWithData": (masterCallsign, "LELNA")}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["VEXEN"], "kwargs": {"speed": 250, "altitude": 16000, "flightPlan": FlightPlan.arrivalPlan("EGJB", "VEXEN DCT ORTAC DCT ALD"), "currentlyWithData": (masterCallsign, "ORTAC")}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["ENHEL"], "kwargs": {"speed": 250, "altitude": 19000, "flightPlan": FlightPlan.arrivalPlan("EGJB", "ENHEL DCT SKERY DCT GUR"), "currentlyWithData": (masterCallsign, "SKERY")}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["KLAKI"], "kwargs": {"speed": 250, "altitude": 19000, "flightPlan": FlightPlan.arrivalPlan("EGJB", "KLAKI DCT BIGNO DCT GUR"), "currentlyWithData": (masterCallsign, "BIGNO")}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["MARUK"], "kwargs": {"speed": 250, "altitude": 14000, "flightPlan": FlightPlan.arrivalPlan("EGJA", "MARUK DCT LELNA DCT ALD"), "currentlyWithData": (masterCallsign, "LELNA")}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["VEXEN"], "kwargs": {"speed": 250, "altitude": 12000, "flightPlan": FlightPlan.arrivalPlan("EGJA", "VEXEN DCT ORTAC DCT ALD"), "currentlyWithData": (masterCallsign, "ORTAC")}},
    #     # {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["ENHEL"], "kwargs": {"speed": 250, "altitude": 15000, "flightPlan": FlightPlan.arrivalPlan("EGJA", "ENHEL DCT SKERY DCT GUR"), "currentlyWithData": (masterCallsign, "SKERY")}},
    #     # {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["KLAKI"], "kwargs": {"speed": 250, "altitude": 15000, "flightPlan": FlightPlan.arrivalPlan("EGJA", "KLAKI DCT BIGNO DCT GUR"), "currentlyWithData": (masterCallsign, "BIGNO")}}
    # ]))

    # util.PausableTimer(5, spawnRandomEveryNSeconds, args=(60, [
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "DEP", "args": ["EGJJ"], "kwargs": {"flightPlan": FlightPlan("I", "B738", 250, "EGJJ", 1130, 1130, 15000, "EGKK", Route("ORIST1D/08 ORIST L982 VASUX", "EGJJ"))}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "DEP", "args": ["EGJJ"], "kwargs": {"flightPlan": FlightPlan("I", "B738", 250, "EGJJ", 1130, 1130, 10000, "EGKK", Route("ORTAC2B/08 ORTAC Q41 SAM Y8 GWC", "EGJJ"))}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "DEP", "args": ["EGJJ"], "kwargs": {"flightPlan": FlightPlan("I", "B738", 250, "EGJJ", 1130, 1130, 15000, "EGTE", Route("SKERY2B/08 SKERY N864 DAWLY", "EGJJ"))}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "DEP", "args": ["EGJB"], "kwargs": {"flightPlan": FlightPlan("I", "B738", 250, "EGJB", 1130, 1130, 15000, "EGKK", Route("ORIST1F/09 ORIST L982 VASUX", "EGJB"))}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "DEP", "args": ["EGJB"], "kwargs": {"flightPlan": FlightPlan("I", "B738", 250, "EGJB", 1130, 1130, 10000, "EGKK", Route("ORTAC3E/08 ORTAC Q41 SAM Y8 GWC", "EGJB"))}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "DEP", "args": ["EGJB"], "kwargs": {"flightPlan": FlightPlan("I", "B738", 250, "EGJB", 1130, 1130, 15000, "EGTE", Route("SKERY3E/08 SKERY N864 DAWLY", "EGJB"))}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "DEP", "args": ["EGJA"], "kwargs": {"hdg": 80, "flightPlan": FlightPlan("I", "B738", 250, "EGJA", 1130, 1130, 15000, "EGKK", Route("ORIST L982 VASUX", "EGJA"))}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "DEP", "args": ["EGJA"], "kwargs": {"hdg": 80, "flightPlan": FlightPlan("I", "B738", 250, "EGJA", 1130, 1130, 10000, "EGKK", Route("ORTAC Q41 SAM Y8 GWC", "EGJA"))}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "DEP", "args": ["EGJA"], "kwargs": {"hdg": 80, "flightPlan": FlightPlan("I", "B738", 250, "EGJA", 1130, 1130, 15000, "EGTE", Route("SKERY N864 DAWLY", "EGJA"))}}
    # ]))

    # EDI
    # util.PausableTimer(5, spawnRandomEveryNSeconds, args=(120, [
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["HAVEN"], "kwargs": {"speed": 250, "altitude": 8000, "flightPlan": FlightPlan.arrivalPlan("EGPH", "HAVEN DCT TARTN","B738"), "currentlyWithData": (masterCallsign, "TARTN")}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["PTH"], "kwargs": {"speed": 250, "altitude": 8000, "flightPlan": FlightPlan.arrivalPlan("EGPH", "PTH DCT GRICE","B738"), "currentlyWithData": (masterCallsign, "GRICE")}}
    # ]))

    # PF
    # stdArrival(masterCallsign, controllerSock, "EGPF", 100, [
    #     ["TLA DCT LANAK", 8000, "EGPF_APP"],
    #     ["BRUCE DCT FYNER", 8000, "EGPF_APP"],
    #     ["ERSON DCT FOYLE", 8000, "EGPF_APP"],
    #     ["PTH DCT STIRA", 8000, "EGPF_APP"],
    # ])

    # STC

    # Arrivals
    # PH every  mins
    # stdArrival(masterCallsign, controllerSock, "EGPH", 100, [  # KK arrivals
    #     ["HAVEN DCT TARTN", 8000, "EGPH_APP"],
    #     ["ESKDO DCT TARTN", 8000, "EGPH_APP"],
    #     ["TLA DCT TARTN", 8000, "EGPH_APP"],  # !
    #     ["PTH DCT GRICE DCT STIRA", 8000, "EGPH_APP"],
    # # PH every  mins
    # stdArrival(masterCallsign, controllerSock, "EGPH", 75, [  # KK arrivals
    #     ["ABEVI DCT INPIP", 26000, "STC_CTR"],
    #     ["ABEVI DCT INPIP", 26000, "STC_CTR"],
    #     ["ABEVI DCT INPIP", 26000, "STC_CTR"],  # !
    #     ["DIGBI DCT AGPED", 26000, "STC_CTR"],
    #     ["BLACA DCT TUNSO", 17000, "STC_CTR"]
    # ])
    # # PF every 3 mins
    # stdArrival(masterCallsign, controllerSock, "EGPF", 75, [  # KK arrivals
    #     ["NELSA DCT RIBEL", 26000, "STC_CTR"],
    #     ["NELSA DCT RIBEL", 26000, "STC_CTR"],
    #     ["NELSA DCT RIBEL", 26000, "STC_CTR"],  # !
    #     ["DIGBI DCT AGPED", 26000, "STC_CTR"],
    #     ["BLACA DCT GIRVA", 17000, "STC_CTR"]
    # ])
    # # PK every 3 mins
    # stdArrival(masterCallsign, controllerSock, "EGPK", 75, [  # KK arrivals
    #     ["NELSA DCT RIBEL", 26000, "STC_CTR"],
    #     ["NELSA DCT RIBEL", 26000, "STC_CTR"],
    #     ["NELSA DCT RIBEL", 26000, "STC_CTR"],  # !
    #     ["NATEB Y96 TLA DCT TRN", 26000, "STC_CTR"],
    #     ["IPSET DCT BLACA", 10000, "STC_CTR"]
    # ])

    # Departures
    # # PH every 2 mins
    # stdDeparture(masterCallsign, controllerSock, "EGPH", 120, [  # SS departures
    #     ["GOSAM1C/24 GOSAM P600 FENIK L612 HON N859 KIDLI", "EGKK"],
    #     ["GOSAM1C/24 GOSAM P600 FENIK L612 HON N859 KIDLI", "EGKK"],
    #     ["GOSAM1C/24 GOSAM P600 BLACA DCT BELZU", "EGAA"],
    #     ["TLA6C/24 TLA Y96 NATEB N610 LONAM", "EHAM"]
    # ])
    # # PF every 3 mins
    # stdDeparture(masterCallsign, controllerSock, "EGPF", 120, [  # SS departures
    #     ["NORBO1H/23 NORBO T256 ROVLA UT256 DCS UN864 SUBUK DCT KEPAD L151 DISIT", "EGKK"],
    #     ["NORBO1H/23 NORBO T256 ROVLA UT256 DCS UN864 SUBUK DCT KEPAD L151 DISIT", "EGKK"],
    #     ["NORBO1H/23 NORBO L186 TRN P600 BLACA DCT BELZU", "EGAA"],
    #     ["NORBO1H/23 NORBO Y96 NATEB N610 LONAM", "EHAM"]
    # ])
    # # PK every 3 mins
    # stdDeparture(masterCallsign, controllerSock, "EGPK", 120, [  # SS departures
    #     ["SUDBY1L/12 SUDBY Z249 OSMEG T256 DCS L612 HON N859 KIDLI", "EGKK"],
    #     ["SUDBY1L/12 SUDBY Z249 OSMEG T256 DCS L612 HON N859 KIDLI", "EGKK"],
    #     ["TRN2L/12 P600 BLACA DCT BELZU", "EGAA"],
    #     ["SUMIN1L/12 SUMIN Z250 HAVEN Y96 NATEB N610 LONAM", "EHAM"]
    # ])

    # LTC-S
    # stdArrival(masterCallsign, controllerSock, "EGKK", 90, [  # KK arrivals
    #     ["KUNAV DCT AMDUT DCT SFD DCT WILLO", 16000, "LTC_CTR"],
    #     ["TEBRA DCT ABTUM DCT ARNUN DCT LARCK DCT TIMBA", 14000, "LTC_CTR"],
    #     ["KONAN DCT KONAN DCT ARNUN DCT LARCK DCT TIMBA", 12000, "LTC_CTR"],  # !
    #     ["AVANT DCT GWC DCT HOLLY DCT WILLO", 13000, "LTC_CTR"],
    #     ["CAWZE DCT SIRIC DCT NIGIT DCT MID DCT TUFOZ DCT HOLLY DCT WILLO", 14000, "LTC_CTR"],
    #     ["DISIT DCT KIDLI DCT MID DCT TUFOZ DCT HOLLY DCT WILLO", 15000, "LTC_CTR"]
    # ])

    # stdArrival(masterCallsign, controllerSock, "EGLL", 75, [  # LL arrivals
    #     ["ROTNO DCT ETVAX DCT TIGER DCT BIG", 18000, "LTC_SE_CTR"],
    #     ["ROTNO DCT ETVAX DCT TIGER DCT BIG", 18000, "LTC_SE_CTR"],
    #     ["BEGTO DCT HAZEL DCT OCK", 13000, "LTC_SW_CTR"],
    #     ["CAWZE DCT SIRIC DCT NIGIT DCT OCK", 14000, "LTC_SW_CTR"],
    # stdArrival(masterCallsign, controllerSock, "EGLL", 100, [  # LL arrivals
    #     ["ROTNO DCT ETVAX DCT TIGER DCT BIG", 18000, "LTC_CTR"],
    #     ["ROTNO DCT ETVAX DCT TIGER DCT BIG", 18000, "LTC_CTR"],
    #     ["BEGTO DCT HAZEL DCT OCK", 13000, "LTC_CTR"],
    #     ["CAWZE DCT SIRIC DCT NIGIT DCT OCK", 14000, "LTC_CTR"],

    #     ["SOPIT DCT WCO DCT BNN", 15000, "LTC_CTR"],
    #     ["SABER DCT BRASO DCT WESUL DCT LAM", 16000, "LTC_CTR"]
    # ])

    # stdArrival(masterCallsign, controllerSock, "EGSS", 100, [  # SS arrivals
    #     ["HAZEL DCT SILVA DCT BOMBO DCT BKY DCT BUSTA DCT LOREL", 13000, "LTC_CTR"],  # AVANT DCT 
    #     ["ROGBI DCT FINMA DCT BOMBO DCT BKY DCT BUSTA DCT LOREL", 15000, "LTC_CTR"],
    #     ["LOFFO DCT ABBOT", 9000, "LTC_CTR"],
    #     ["VATON DCT BPK DCT BKY DCT BUSTA DCT LOREL", 16000, "LTC_CTR"],
    # ])

    # stdArrival(masterCallsign, controllerSock, "EGGW", 75, [  # GW arrivals
    #     ["AVANT DCT HAZEL DCT SILVA DCT WOBUN DCT EDCOX DCT JUMZI DCT ZAGZO", 13000, "LTC_N_CTR"],
    #     ["ROGBI DCT FINMA DCT WOBUN DCT EDCOX DCT JUMZI DCT ZAGZO", 15000, "LTC_N_CTR"],
    #     ["VATON DCT OZZOT DCT BPK DCT ILLOC DCT OXDUF DCT COCCU DCT JUMZI DCT ZAGZO", 16000, "LTC_N_CTR"],
    #     ["MUCTE DCT OFJES DCT UDDIZ DCT COCCU DCT JUMZI DCT ZAGZO", 14000, "LTC_N_CTR"],
    #     ["CLN DCT ABBOT", 9000, "LTC_N_CTR"],
    # ])

    # stdDeparture(masterCallsign, controllerSock, "EGKK", 120, [  # KK departures
    #     ["HARDY1X/26L HARDY M605 XIDIL", "LFPG"],
    #     ["NOVMA1X/26L NOVMA L620 NIBDA N14 HEKXA Q63 SAWPE", "EGGD"],
    #     ["NOVMA1X/26L NOVMA L620 GIBSO", "EGTE"],
    #     ["MIMFO1M/26L MIMFO Y312 DVR L9 KONAN", "EHAM"],
    #     ["LAM6M/26L LAM UN57 WELIN T420 ELVOS", "EGCC"],
    #     ["FRANE1M/26L FRANE M604 GASBA M189 CLN DCT BANEM", "EGSH"]
    # ])

    # stdDeparture(masterCallsign, controllerSock, "EGLL", 120, [  # LL departures
    #     ["MAXIT1F/27R MAXIT Y803 MID L612 BOGNA DCT HARDY M605 XIDIL", "LFPG"],
    #     ["CPT3F/27R CPT Q63 SAWPE", "EGGD"],
    #     ["GOGSI2F/27R GOGSI N621 SAM DCT GIBSO", "EGTE"],
    #     ["DET2F/27R L6 DVR UL9 KONAN", "EHAM"],

    #     ["UMLAT1F/27R UMLAT T418 WELIN T420 ELVOS", "EGCC"],
    #     ["BPK7F/27R BPK Q295 BRAIN M197 REDFA", "EHAM"]
    # ])

    # stdDeparture(masterCallsign, controllerSock, "EGSS", 100, [  # SS departures
    #     ["NUGBO1R/22 NUGBO M183 SILVA P86 SAWPE", "EGGD"],
    #     ["UTAVA1R/22 Q75 BUZAD T420 TNT UN57 POL UN601 INPIP", "EGPH"]
    # ])
    # stdDeparture(masterCallsign, controllerSock, "EGSS", 120, [  # SS departures
    #     ["DET2R/22 DET M604 LYD M189 WAFFU UM605 XIDIL", "LFPG"],
    #     ["NUGBO1R/22 NUGBO M183 SILVA P86 SAWPE", "EGGD"]
    # ])

    # stdDeparture(masterCallsign, controllerSock, "EGGW", 100, [  # GW departures
    #     ["RODNI1B/25 RODNI N27 ICTAM", "EGGD"],
    # ])

    # #SS
    # stdArrival(masterCallsign, controllerSock, "EGSS", 85, [  # SS arrivals
    #     ["BOMBO DCT BKY DCT BUSTA DCT LOREL", 8000, "ESSEX_APP"],
    #     ["BKY DCT BUSTA DCT LOREL", 12000, "ESSEX_APP"],
    #     ["LOFFO DCT ABBOT", 8000, "ESSEX_APP"],
    #     ["CLN DCT ABBOT", 8000, "ESSEX_APP"],
    #     ["LAPRA DCT ABBOT", 8000, "ESSEX_APP"]
    # ])

    # stdArrival(masterCallsign, controllerSock, "EGGW", 85, [  # GW arrivals
    #     ["WOBUN DCT EDCOX JUMZI DCT ZAGZO", 11000, "ESSEX_APP"],
    #     ["LOFFO DCT ABBOT", 9000, "ESSEX_APP"],
    #     ["CLN DCT ABBOT", 9000, "ESSEX_APP"],
    # ])


    # TCN+TCE+SS+GW
    # stdArrival(masterCallsign, controllerSock, "EGSS", 200, [  # SS arrivals TCN
    #     ["HON DCT FINMA FINMA1L", 15000, "LTC_N_CTR"],
    #     ["MID DCT WOD M605 SILVA SILVA1L", 13000, "LTC_N_CTR"],
    #     ["MAY DCT VATON DCT BPK DCT BKY DCT BUSTA DCT LOREL", 16000, "LTC_N_CTR"],
    # ])
    # stdArrival(masterCallsign, controllerSock, "EGGW", 200, [  # GW arrivals TCN
    #     ["HON DCT FINMA FINMA1N", 15000, "LTC_N_CTR"],
    #     ["MID DCT WOD M605 SILVA SILVA1N", 13000, "LTC_N_CTR"],
    #     ["MAY DCT VATON DCT OZZOT DCT BPK DCT ILLOC DCT OXDUF DCT COCCU DCT JUMZI DCT ZAGZO", 16000, "LTC_N_CTR"],
    # ])

    # stdArrival(masterCallsign, controllerSock, "EGSS", 180, [  # SS arrivals TCE
    #     ["LUSOR DCT RINIS RINIS1A", 22000, "LTC_E_CTR"],
    #     ["AMRIV DCT XAMAN XAMAN1A", 22000, "LTC_E_CTR"],
    #     ["NAVPI DCT BARMI BARMI2A", 22000, "LTC_E_CTR"],
    # ])
    # stdArrival(masterCallsign, controllerSock, "EGGW", 180, [  # GW arrivals TCE
    #     ["LUSOR DCT RINIS RINIS1N", 22000, "LTC_E_CTR"],
    #     ["AMRIV DCT XAMAN XAMAN1N", 22000, "LTC_E_CTR"],
    #     ["NAVPI DCT BARMI BARMI2N", 22000, "LTC_E_CTR"],
    # ])

    # stdDeparture(masterCallsign, controllerSock, "EGSS", 120, [  # SS departures
    #     ["DET2R/22 DET M604 LYD M189 WAFFU UM605 XIDIL", "LFPG"],
    #     ["NUGBO1R/22 NUGBO M183 SILVA P86 SAWPE", "EGFF"],
    #     ["CLN2E/22 CLN P44 RATLO M197 REDFA", "EHAM"],
    #     ["CLN2E/22 CLN P44 SOMVA", "EHAM"],
    #     ["CLN2E/22 CLN P44 RATLO M197 REDFA", "EHAM"],
    #     ["CLN2E/22 CLN P44 SOMVA", "EHAM"],
    #     ["CLN2E/22 CLN DCT LEDBO M604 LARGA DCT INBOB", "ESSA"],
    #     ["CLN2E/22 CLN DCT LEDBO M604 LARGA DCT INBOB", "ESSA"],
    # ])

    # stdDeparture(masterCallsign, controllerSock, "EGGW", 120, [  # GW departures
    #     ["DET3Y/25 DET M604 LYD M189 WAFFU UM605 XIDIL", "LFPG"],
    #     ["RODNI1B/25 RODNI N27 ICTAM", "EGFF"],
    #     ["MATCH3Y/25 MATCH Q295 BRAIN M197 REDFA", "EHAM"],
    #     ["MATCH3Y/25 MATCH Q295 SOMVA", "EHAM"],
    #     ["MATCH3Y/25 MATCH Q295 BRAIN M197 REDFA", "EHAM"],
    #     ["MATCH3Y/25 MATCH Q295 SOMVA", "EHAM"],
    #     ["MATCH3Y/25 MATCH Q295 PAAVO M604 LARGA DCT INBOB", "ESSA"],
    #     ["MATCH3Y/25 MATCH Q295 PAAVO M604 LARGA DCT INBOB", "ESSA"],
    # ])

    # stdTransit(masterCallsign, controllerSock, 110, [  # TCNE traffic
    #     ["EGKK", "EHAM", 11000, 21000, "DET DCT FRANE M604 GASBA M197 REDFA", "LTC_N_CTR"],
    #     ["EGKK", "EHAM", 11000, 21000, "DET DCT FRANE M604 GASBA M197 REDFA", "LTC_N_CTR"],
    #     ["EGKK", "EHAM", 11000, 21000, "DET DCT FRANE M604 GASBA M197 REDFA", "LTC_N_CTR"],
    #     ["EGCC", "EGLL", 15000, 15000, "TOBID DCT SOPIT DCT WCO DCT BNN", "LTC_N_CTR"],
    # ], withMaster=False)

    # stdTransit(masterCallsign, controllerSock, 120, [  # TCNE traffic
    #     ["EGCC", "EGLL", 25000, 25000, "XAMAN DCT LOGAN DCT SABER DCT BRASO DCT WESUL DCT LAM", "LTC_E_CTR"],
    # ], withMaster=False)

    # NX
    # stdArrival(masterCallsign, controllerSock, "EGNX", 100, [
    #     ["WELIN DCT PIGOT", 9999, "EGNX_APP"],
    #     ["XAPOS DCT ROKUP", 8000, "EGNX_APP"]
    # ])

    # stdDeparture(masterCallsign, controllerSock, "EGNX", 100, [
    #     ["DTY4P/09 DTY", "EGKK"],
    #     ["POL2P/09 POL", "EGCC"],
    #     ["TNT3P/09 TNT", "EGCC"]
    # ])

    # LC
    # stdArrival(masterCallsign, controllerSock, "EGLC", 115, [
    #     ["RATLO DCT JACKO ODLEG1J/09", 9000, "THAMES_APP"],
    #     ["ERKEX DCT GODLU ODLEG1G/09", 9999, "THAMES_APP"]
    # ])

    # stdArrival(masterCallsign, controllerSock, "EGMC", 100, [
    #     ["SUMUM DCT LOGAN DCT JACKO DCT GEGMU", 9999, "THAMES_APP"],
    #     ["ABBOT DCT SABER", 4000, "EGMC_APP"]
    # ])

    # stdDeparture(masterCallsign, controllerSock, "EGLC", 110, [
    #     ["BPK1H/09 BPK", "EGCC"],
    #     ["ODUKU1H/09 ODUKU", "EGCC"],
    #     ["SOQQA1H/09 SOQQA", "EGCC"]
    # ])



    # TCM

    # stdArrival(masterCallsign, controllerSock, "EGNX", 110, [
    #     ["LAM DCT HEMEL DCT WELIN DCT VELAG DCT UPDUK DCT PIGOT", 22000, "LTC_M_CTR"],
    #     ["XAPOS DCT ROKUP", 8000, "EGNX_APP"]
    # ])

    # stdDeparture(masterCallsign, controllerSock, "EGNX", 120, [
    #     ["DTY4P/09 DTY DCT WCO DCT MID", "EGKK"],
    #     ["DTY4P/09 DTY DCT WCO DCT MID", "EGKK"],
    #     ["DTY4P/09 DTY DCT WCO DCT MID", "EGKK"],
    #     ["DTY4P/09 DTY L10 HON", "EGBB"]
    # ])

    # stdArrival(masterCallsign, controllerSock, "EGBB", 180, [
    #     ["LAM DCT HEMEL DCT WELIN DCT PUFAX DCT HON DCT OSKOT DCT GROVE", 22000, "LTC_M_CTR"],
    #     ["VEGAR DCT CHASE", 9000, "LTC_M_CTR"]
    # ])

    # stdDeparture(masterCallsign, controllerSock, "EGBB", 120, [
    #     ["ADMEX1M/33 ADMEX Y321 EMKUK L612 MID", "EGKK"],
    #     ["ADMEX1M/33 ADMEX Y321 EMKUK L612 MID", "EGKK"],
    #     ["ADMEX1M/33 ADMEX Y321 EMKUK L612 MID", "EGKK"],
    #     ["UNGAP1M/33 UNGAP DCT DTY", "EGNX"]
    # ])



    # ScAC E

    # stdArrival(masterCallsign, controllerSock, "EGPH", 540, [  # PH arrivals
    #     ["RENEQ Y96 AGPED", 34000, "SCO_E_CTR"],
    #     ["VALBO DCT AVRAL DCT ROBEM DCT AGPED", 34000, "SCO_E_CTR"],
    #     ["PETIL DCT SURAT DCT ROBEM DCT AGPED", 34000, "SCO_E_CTR"],
    #     ["GOREV DCT SURAT DCT ROBEM DCT AGPED", 34000, "SCO_E_CTR"],
    #     ["TINAC DCT ITSUX DCT ROBEM DCT AGPED", 34000, "SCO_E_CTR"],
    #     ["VAXIT DCT ELSAN DCT ADN P600 PTH", 34000, "SCO_E_CTR"],
    #     ["ALOTI DCT ADN P600 PTH", 34000, "SCO_E_CTR"],
    #     ["KLONN DCT ADN P600 PTH", 34000, "SCO_E_CTR"],
    #     ["RIGVU DCT ADN P600 PTH", 34000, "SCO_E_CTR"],
    #     ["BEREP DCT ADN P600 PTH", 34000, "SCO_E_CTR"],
    #     ["PEMOS DCT LAGAV N560 FOYLE DCT STIRA", 35000, "SCO_E_CTR"],
    #     ["OSBON DCT LAGAV N560 FOYLE DCT STIRA", 35000, "SCO_E_CTR"],
    #     ["NALAN DCT LAGAV N560 FOYLE DCT STIRA", 35000, "SCO_E_CTR"],
    #     ["MATIK DCT BESGA DCT LAGAV N560 FOYLE DCT STIRA", 35000, "SCO_E_CTR"],
    #     ["RATSU DCT BARKU DCT BRUCE L602 CLYDE DCT STIRA", 35000, "SCO_E_CTR"],
    #     ["ATSIX DCT AKIVO DCT BRUCE L602 CLYDE DCT STIRA", 35000, "SCO_E_CTR"],
    #     ["ORTAV DCT ODPEX DCT BRUCE L602 CLYDE DCT STIRA", 35000, "SCO_E_CTR"],
    # ], withMaster=False)

    # stdArrival(masterCallsign, controllerSock, "EGPF", 540, [  # PF arrivals
    #     ["RENEQ Y96 AGPED", 34000, "SCO_E_CTR"],
    #     ["VALBO DCT AVRAL DCT ROBEM DCT AGPED", 34000, "SCO_E_CTR"],
    #     ["PETIL DCT SURAT DCT ROBEM DCT AGPED", 34000, "SCO_E_CTR"],
    #     ["GOREV DCT SURAT DCT ROBEM DCT AGPED", 34000, "SCO_E_CTR"],
    #     ["TINAC DCT ITSUX DCT ROBEM DCT AGPED", 34000, "SCO_E_CTR"],
    #     ["VAXIT DCT ELSAN DCT ADN P600 PTH", 34000, "SCO_E_CTR"],
    #     ["ALOTI DCT ADN P600 PTH", 34000, "SCO_E_CTR"],
    #     ["KLONN DCT ADN P600 PTH", 34000, "SCO_E_CTR"],
    #     ["RIGVU DCT ADN P600 PTH", 34000, "SCO_E_CTR"],
    #     ["BEREP DCT ADN P600 PTH", 34000, "SCO_E_CTR"],
    #     ["PEMOS DCT NESDI N560 ERSON", 35000, "SCO_E_CTR"],
    #     ["OSBON DCT NESDI N560 ERSON", 35000, "SCO_E_CTR"],
    #     ["NALAN DCT NESDI N560 ERSON", 35000, "SCO_E_CTR"],
    #     ["MATIK DCT BESGA DCT NESDI N560 ERSON", 35000, "SCO_E_CTR"],
    #     ["RATSU DCT BARKU DCT NESDI N560 ERSON", 35000, "SCO_E_CTR"],
    #     ["ATSIX DCT AKIVO DCT NESDI N560 ERSON", 35000, "SCO_E_CTR"],
    #     ["ORTAV DCT ODPEX DCT NESDI N560 ERSON", 35000, "SCO_E_CTR"],
    # ], withMaster=False)

    # stdArrival(masterCallsign, controllerSock, "EGPK", 540, [  # PK arrivals
    #     ["RENEQ Y96 TLA DCT TRN", 34000, "SCO_E_CTR"],
    #     ["VALBO DCT AVRAL DCT ROBEM DCT AGPED Y96 TLA DCT TRN", 34000, "SCO_E_CTR"],
    #     ["PETIL DCT SURAT DCT ROBEM DCT AGPED Y96 TLA DCT TRN", 34000, "SCO_E_CTR"],
    #     ["GOREV DCT SURAT DCT ROBEM DCT AGPED Y96 TLA DCT TRN", 34000, "SCO_E_CTR"],
    #     ["TINAC DCT ITSUX DCT ROBEM DCT AGPED Y96 TLA DCT TRN", 34000, "SCO_E_CTR"],
    #     ["VAXIT DCT ELSAN DCT ADN P600 TRN", 34000, "SCO_E_CTR"],
    #     ["ALOTI DCT ADN P600 TRN", 34000, "SCO_E_CTR"],
    #     ["KLONN DCT ADN P600 TRN", 34000, "SCO_E_CTR"],
    #     ["RIGVU DCT ADN P600 TRN", 34000, "SCO_E_CTR"],
    #     ["BEREP DCT ADN P600 TRN", 34000, "SCO_E_CTR"],
    #     ["PEMOS DCT INBAS N560 GOW DCT TRN", 35000, "SCO_E_CTR"],
    #     ["OSBON DCT INBAS N560 GOW DCT TRN", 35000, "SCO_E_CTR"],
    #     ["NALAN DCT INBAS N560 GOW DCT TRN", 35000, "SCO_E_CTR"],
    #     ["MATIK DCT BESGA DCT INBAS N560 GOW DCT TRN", 35000, "SCO_E_CTR"],
    #     ["RATSU DCT BARKU DCT INBAS N560 GOW DCT TRN", 35000, "SCO_E_CTR"],
    #     ["ATSIX DCT AKIVO DCT INBAS N560 GOW DCT TRN", 35000, "SCO_E_CTR"],
    #     ["ORTAV DCT ODPEX DCT INBAS N560 GOW DCT TRN", 35000, "SCO_E_CTR"],
    # ], withMaster=False)

    # stdArrival(masterCallsign, controllerSock, "EGPD", 540, [  # PD arrivals
    #     ["RENEQ P38 ROBEM DCT FINDO P600 NAXIL", 34000, "SCO_E_CTR"],
    #     ["VALBO DCT AVRAL DCT OVDAN P600 ADN", 34000, "SCO_E_CTR"],
    #     ["PETIL DCT SURAT DCT FINDO P600 NAXIL", 34000, "SCO_E_CTR"],
    #     ["GOREV DCT SURAT DCT MADAD P18 RATPU", 34000, "SCO_E_CTR"],
    #     ["TINAC DCT ITSUX DCT OVDAN P600 ADN", 34000, "SCO_E_CTR"],
    #     ["VAXIT DCT REKNA DCT MADAD P18 RATPU", 34000, "SCO_E_CTR"],
    #     ["ALOTI DCT OVDAN P600 ADN", 34000, "SCO_E_CTR"],
    #     ["KLONN DCT OVDAN P600 LESNI DCT ADN", 34000, "SCO_E_CTR"],
    #     ["RIGVU DCT OVDAN P600 ADN", 34000, "SCO_E_CTR"],
    #     ["PEMOS DCT WIK Y904 ADN", 35000, "SCO_E_CTR"],
    #     ["OSBON DCT WIK Y904 ADN", 35000, "SCO_E_CTR"],
    #     ["NALAN DCT WIK Y904 ADN", 35000, "SCO_E_CTR"],
    #     ["MATIK DCT BESGA DCT WIK Y904 ADN", 35000, "SCO_E_CTR"],
    #     ["RATSU DCT BARKU DCT WIK Y904 ADN", 35000, "SCO_E_CTR"],
    #     ["ATSIX DCT AKIVO DCT WIK Y904 ADN", 35000, "SCO_E_CTR"],
    #     ["ORTAV DCT ODPEX DCT WIK Y904 ADN", 35000, "SCO_E_CTR"],
    # ], withMaster=False)

    # stdArrival(masterCallsign, controllerSock, "EGPE", 540, [  # PE arrivals
    #     ["VALBO DCT AVRAL DCT ADN", 34000, "SCO_E_CTR"],
    #     ["PETIL DCT REKNA DCT ADN", 34000, "SCO_E_CTR"],
    #     ["VAXIT DCT ELSAN DCT ADN", 34000, "SCO_E_CTR"],
    #     ["ALOTI DCT ADN", 34000, "SCO_E_CTR"],
    #     ["PEMOS DCT STN Y906 GARVA", 35000, "SCO_E_CTR"],
    #     ["OSBON DCT STN Y906 GARVA", 35000, "SCO_E_CTR"],
    #     ["NALAN DCT STN Y906 GARVA", 35000, "SCO_E_CTR"],
    #     ["MATIK DCT BESGA DCT STN Y906 GARVA", 35000, "SCO_E_CTR"],
    #     ["RATSU DCT BARKU DCT STN Y906 GARVA", 35000, "SCO_E_CTR"],
    #     ["ATSIX DCT AKIVO DCT STN Y906 GARVA", 35000, "SCO_E_CTR"],
    #     ["ORTAV DCT ODPEX DCT STN Y906 GARVA", 35000, "SCO_E_CTR"],
    # ], withMaster=False)



    # stdDeparture(masterCallsign, controllerSock, "EGPH", 480, [
    #     ["GRICE4D/06 GRICE P600 ASNUD DCT ELSAN DCT VAXIT", "BIKF"],
    #     ["GRICE4D/06 GRICE P600 ASNUD DCT ALOTI", "BIKF"],
    #     ["GRICE4D/06 GRICE P600 ASNUD DCT KLONN", "BIKF"],
    #     ["GRICE4D/06 GRICE P600 ASNUD DCT RIGVU", "BIKF"],
    #     ["GRICE4D/06 GRICE P600 ASNUD DCT BEREP", "BIKF"],
    #     ["GRICE4D/06 GRICE DCT FOYLE N560 ERSON DCT PEMOS", "BIKF"],
    #     ["GRICE4D/06 GRICE DCT FOYLE N560 ERSON DCT OSBON", "BIKF"],
    #     ["GRICE4D/06 GRICE DCT FOYLE N560 ERSON DCT NALAN", "BIKF"],
    #     ["GRICE4D/06 GRICE DCT FOYLE N560 ERSON DCT BESGA DCT MATIK", "BIKF"],
    #     ["GRICE4D/06 GRICE DCT FOYLE N560 ERSON DCT BARKU DCT RATSU", "BIKF"],
    #     ["GRICE4D/06 GRICE DCT FOYLE N560 ERSON DCT ATSIX", "BIKF"],
    #     ["GRICE4D/06 GRICE DCT FOYLE N560 ERSON DCT ORTAV", "BIKF"],
    # ])

    # stdDeparture(masterCallsign, controllerSock, "EGPF", 480, [
    #     ["PTH4B/05 PTH P600 ASNUD DCT ELSAN DCT VAXIT", "BIKF"],
    #     ["PTH4B/05 PTH P600 ASNUD DCT ALOTI", "BIKF"],
    #     ["PTH4B/05 PTH P600 ASNUD DCT KLONN", "BIKF"],
    #     ["PTH4B/05 PTH P600 ASNUD DCT RIGVU", "BIKF"],
    #     ["PTH4B/05 PTH P600 ASNUD DCT BEREP", "BIKF"],
    #     ["FOYLE3B/05 FOYLE N560 LAGAV DCT PEMOS", "BIKF"],
    #     ["FOYLE3B/05 FOYLE N560 LAGAV DCT OSBON", "BIKF"],
    #     ["FOYLE3B/05 FOYLE N560 LAGAV DCT NALAN", "BIKF"],
    #     ["FOYLE3B/05 FOYLE N560 LAGAV DCT BESGA DCT MATIK", "BIKF"],
    #     ["FOYLE3B/05 FOYLE N560 LAGAV DCT BARKU DCT RATSU", "BIKF"],
    #     ["FOYLE3B/05 FOYLE N560 LAGAV DCT ATSIX", "BIKF"],
    #     ["FOYLE3B/05 FOYLE N560 LAGAV DCT ORTAV", "BIKF"],
    # ])

    # stdDeparture(masterCallsign, controllerSock, "EGPD", 480, [
    #     ["ADN P600 BUDON DCT LAMRO DCT ARTEX DCT VAXIT", "BIKF"],
    #     ["ADN P600 BUDON DCT ALOTI", "BIKF"],
    #     ["ADN P600 BUDON DCT KLONN", "BIKF"],
    #     ["ADN P600 BUDON DCT RIGVU", "BIKF"],
    #     ["ADN P600 BUDON DCT BEREP", "BIKF"],
    #     ["ADN Y904 WIK DCT PEMOS", "BIKF"],
    #     ["ADN Y904 WIK DCT OSBON", "BIKF"],
    #     ["ADN Y904 WIK DCT NALAN", "BIKF"],
    #     ["ADN DCT RIMOL DCT BESGA DCT MATIK", "BIKF"],
    #     ["ADN DCT RIMOL DCT BARKU DCT RATSU", "BIKF"],
    #     ["ADN DCT RIMOL DCT ATSIX", "BIKF"],
    #     ["ADN DCT RIMOL DCT ORTAV", "BIKF"],
    # ])

    # stdDeparture(masterCallsign, controllerSock, "EGPE", 480, [
    #     ["ADN DCT ALOTI", "BIKF"],
    #     ["GARVA Y906 STN DCT PEMOS", "BIKF"],
    #     ["GARVA Y906 STN DCT OSBON", "BIKF"],
    #     ["GARVA Y906 STN DCT NALAN", "BIKF"],
    #     ["GARVA Y906 STN DCT BESGA DCT MATIK", "BIKF"],
    #     ["GARVA Y906 STN DCT BARKU DCT RATSU", "BIKF"],
    #     ["GARVA Y906 STN DCT ATSIX", "BIKF"],
    #     ["GARVA Y906 STN DCT ORTAV", "BIKF"],
    # ])


    # AC W

    # stdTransit(masterCallsign, controllerSock, 210, [  # east to west (south)
    #     ["EGLL", "KJFK", 26000, 36000, "OSNUG DCT ADKIK DCT JOMZA DCT LULOX", "LON_W_CTR"],
    #     ["EGLL", "KJFK", 26000, 36000, "OSNUG DCT ADKIK DCT JOMZA DCT GAPLI", "LON_W_CTR"],
    #     ["EGLL", "KJFK", 26000, 36000, "OSNUG DCT ADKIK DCT FONZU DCT LESLU", "LON_W_CTR"],
    #     ["EGLL", "KJFK", 26000, 36000, "OSNUG DCT ADKIK DCT FONZU DCT LEDGO", "LON_W_CTR"],
    #     ["EGLL", "KJFK", 26000, 36000, "OSNUG DCT ADKIK DCT MOPAT", "LON_W_CTR"],
    # ], withMaster=False)
    # stdTransit(masterCallsign, controllerSock, 210, [  # east to west (north)
    #     ["EGLL", "EIDW", 15000, 36000, "CPT DCT DIDZA L9 BUCGO DCT OFSOX DCT BANBA", "LON_W_CTR"],
    #     ["EGLL", "EIDW", 15000, 36000, "CPT DCT DIDZA L9 BUCGO DCT FELCA DCT OFSOX DCT ENJEX", "LON_W_CTR"],
    #     ["EGLL", "EIDW", 15000, 36000, "CPT DCT DIDZA L9 BUCGO DCT FELCA DCT OFSOX DCT SLANY", "LON_W_CTR"],
    #     ["EGLL", "EIDW", 15000, 36000, "CPT DCT DIDZA L9 BUCGO DCT FELCA DCT NICXI DCT BAKUR", "LON_W_CTR"],
    #     ["EGLL", "EIDW", 15000, 36000, "CPT DCT DIDZA N14 OKTAD DCT MEDOG DCT VATRY", "LON_W_CTR"],
    #     ["EGLL", "EIDW", 15000, 36000, "CPT DCT DIDZA N14 OKTAD DCT MEDOG DCT LANON DCT LIPGO", "LON_W_CTR"],
    # ], withMaster=False)
    # stdTransit(masterCallsign, controllerSock, 210, [  # east to west (upper)
    #     ["EHAM", "KJFK", 36000, 36000, "SAWPE DCT OZZIL DCT ZIPWE DCT ADHAV DCT SLANY", "LON_W_CTR"],
    #     ["EHAM", "KJFK", 36000, 36000, "OKSAW DCT FELCA DCT FADZU DCT SLANY", "LON_W_CTR"],
    #     ["EHAM", "KJFK", 36000, 36000, "ADKIK DCT MOPAT", "LON_W_CTR"],
    #     ["EHAM", "KJFK", 36000, 36000, "SAWPE DCT OZZIL DCT ZIPWE DCT ADHAV DCT BANBA", "LON_W_CTR"],
    #     ["EHAM", "KJFK", 36000, 36000, "ENHAQ DCT DCT GAJIT DCT GAPLI", "LON_W_CTR"],
    #     ["EHAM", "KJFK", 36000, 36000, "DIDZA DCT CESQA DCT BIBPE DCT MEDOG DCT LANON DCT LIPGO", "LON_W_CTR"],
    # ], withMaster=False)
    # stdTransit(masterCallsign, controllerSock, 210, [  # south to west (south)
    #     ["EDDM", "EIDW", 36000, 36000, "LIZAD DCT LULOX", "LON_W_CTR"],
    #     ["EDDM", "EIDW", 36000, 36000, "LIZAD DCT ARKIL", "LON_W_CTR"],
    #     ["EDDM", "EIDW", 36000, 36000, "LIZAD DCT BOGMI N160 LEDGO", "LON_W_CTR"],
    #     ["EDDM", "EIDW", 36000, 36000, "LIZAD DCT NAKID DCT UPCAB DCT IJALA DCT EVRIN", "LON_W_CTR"],
    #     ["EDDM", "EIDW", 36000, 36000, "NOZHU DCT BOXHE DCT SHIRI DCT UNFIT DCT PENWU DCT NICXI DCT OFSOX DCT SLANY", "LON_W_CTR"],
    #     ["EDDM", "EIDW", 36000, 36000, "NOZHU DCT BOXHE DCT SHIRI DCT UNFIT DCT PENWU DCT NICXI DCT VATRY", "LON_W_CTR"],
    # ], withMaster=False)
    # stdTransit(masterCallsign, controllerSock, 210, [  # south to north
    #     ["EGJJ", "EIDW", 20000, 36000, "SKESO DCT LIFOX P16 FIMCA N22 BHD N864 TIGWE L9 SLANY", "LON_W_CTR"],
    #     ["EGJJ", "EIDW", 20000, 36000, "SKESO DCT LIFOX P16 FIMCA N22 BHD N864 TIGWE L9 NICXI M17 VATRY", "LON_W_CTR"],
    #     ["EGJJ", "EGCC", 20000, 36000, "SKESO DCT SKERY L22 EMWIP P16 FIMCA DCT TOJAQ DCT EPACE DCT ACCOP DCT MOCQO P16 AXCIS", "LON_W_CTR"],
    # ], withMaster=False)
    

    # stdTransit(masterCallsign, controllerSock, 210, [  # west to east (upper)
    #     ["KJFK", "EHAM", 35000, 35000, "BAKUR DCT GUBJE DCT GISOK DCT TACQI DCT FONZU DCT DAWLY L149 BIGNO", "LON_W_CTR"],
    #     ["KJFK", "EHAM", 35000, 35000, "BAKUR DCT TIKCA DCT BIGNO", "LON_W_CTR"],
    #     ["KJFK", "EHAM", 35000, 35000, "BAKUR DCT TIKCA DCT PEWBI DCT OXLOW M140 SAM Y8 GWC UN859 SITET", "LON_W_CTR"],
    #     ["KJFK", "EHAM", 35000, 35000, "NORLA DCT PEWBI DCT OXLOW M140 SAM L620 MID UM185 KOBBI M197 REDFA", "LON_W_CTR"],
    #     ["KJFK", "EHAM", 35000, 35000, "SAMON DCT SIRIC P2 DVR L18 VABIK", "LON_W_CTR"],
    #     ["KJFK", "EHAM", 35000, 35000, "LEDGO DCT BOGMI DCT ANNET", "LON_W_CTR"],
    #     ["KJFK", "EHAM", 35000, 35000, "LESLU DCT OXLOW M142 ROKKE M140 DVR UL9 KONAN", "LON_W_CTR"],
    #     ["KJFK", "EHAM", 35000, 35000, "LESLU DCT DANWO DCT REDFA", "LON_W_CTR"],
    #     ["KJFK", "EHAM", 35000, 35000, "LESLU DCT BAPHU DCT GAJIT DCT ENHAQ M197 ICTAM Q295 BPK UM185 DIGSU P144 LATMU P48 ROKAN P40 LESLU", "LON_W_CTR"],
    #     ["KJFK", "EHAM", 35000, 35000, "LESLU DCT BAPHU DCT GAJIT DCT ENHAQ M197 BRAIN Q295 PAAVO M604 LARGA DCT PENUN", "LON_W_CTR"],
    #     ["KJFK", "EHAM", 35000, 35000, "GAPLI DCT SIDDI DCT DAWLY DCT GIBSO L620 SAM M140 DVR UL9 KONAN", "LON_W_CTR"],
    #     ["KJFK", "EHAM", 35000, 35000, "GAPLI DCT GAJIT DCT ENHAQ M197 ICTAM Q295 PAAVO M604 LARGA DCT INBOB", "LON_W_CTR"],
    #     ["KJFK", "EHAM", 35000, 35000, "GAPLI DCT GAJIT DCT ENHAQ M197 REDFA", "LON_W_CTR"],
    #     ["KJFK", "EHAM", 35000, 35000, "AMPOP DCT SIDDI DCT DAWLY DCT GIBSO L620 SAM M140 DVR UL9 KONAN", "LON_W_CTR"],
    # ], withMaster=False)
    # stdTransit(masterCallsign, controllerSock, 210, [  # west to east (upper)
    #     ["KJFK", "EGJJ", 35000, 35000, "BAKUR DCT GUBJE DCT GISOK DCT TACQI DCT FONZU DCT DAWLY DCT ABBEW N90 ENHEL N862 SKERY", "LON_W_CTR"],
    #     ["KJFK", "EGJJ", 35000, 35000, "BAKUR DCT GUBJE DCT GISOK DCT TACQI DCT FONZU DCT DAWLY DCT KLAKI L149 BIGNO", "LON_W_CTR"],
    #     ["KJFK", "EGLL", 35000, 35000, "LULOX DCT SIDDI DCT DAWLY DCT ELRIP DCT OTMET", "LON_W_CTR"],
    #     ["KJFK", "EGCC", 35000, 35000, "GAPLI DCT PEWBI DCT INFEC DCT ACCOP DCT MOCQO P16 AXCIS", "LON_W_CTR"],
    #     ["KJFK", "EGBB", 35000, 35000, "GAPLI DCT PEWBI DCT INFEC DCT ICOSA DCT ZIPWE L180 FIGZI", "LON_W_CTR"],
    # ], withMaster=False)

    # stdTransit(masterCallsign, controllerSock, 150, [
    #     ["KJFK", "EGFF", 29000, 35000, "KARNO DCT ALHUP DCT LUCSA N862 WEVBE WEVBE1C", "LON_W_CTR"],
    #     ["KJFK", "EGFF", 30000, 35000, "AMPOP DCT SIDDI DCT TOJAQ TOJAQ1C", "LON_W_CTR"],
    #     ["KJFK", "EGFF", 32000, 32000, "GAPLI DCT SIDDI DCT TOJAQ TOJAQ1C", "LON_W_CTR"],
    #     ["KJFK", "EGFF", 30000, 30000, "ENJEX DCT ADHAV DCT AGCAT Q63 BAJJA BAJJA1C", "LON_W_CTR"],
    #     ["EGLL", "EGFF", 26000, 26000, "LINDY DCT ICTAM ICTAM1C", "LON_W_CTR"],
    # ], withMaster=False)
    # stdTransit(masterCallsign, controllerSock, 150, [
    #     ["KJFK", "EGGD", 29000, 35000, "KARNO DCT ALHUP DCT LUCSA N862 WEVBE WEVBE1B", "LON_W_CTR"],
    #     ["KJFK", "EGGD", 30000, 35000, "AMPOP DCT SIDDI DCT TOJAQ TOJAQ1B", "LON_W_CTR"],
    #     ["KJFK", "EGGD", 32000, 32000, "GAPLI DCT SIDDI DCT TOJAQ TOJAQ1B", "LON_W_CTR"],
    #     ["KJFK", "EGGD", 30000, 30000, "ENJEX DCT ADHAV DCT AGCAT Q63 BAJJA BAJJA1B", "LON_W_CTR"],
    #     ["EGLL", "EGGD", 26000, 26000, "OCK DCT ICTAM ICTAM1B", "LON_W_CTR"],
    # ], withMaster=False)

    # stdDeparture(masterCallsign, controllerSock, "EGFF", 250, [
    #     ["EXMOR1B/12 EXMOR N92 DAWLY DCT JOZMA DCT GAPLI", "KJFK"],
    #     ["BCN1B/12 BCN P4 FELCA DCT NICXI DCT OFSOX DCT ENJEX", "KJFK"],
    #     ["BCN1B/12 BCN P69 DIZIM N864 AVTIC N38 NOKIN P17 POL N601 INPIP", "EGPH"],
    #     ["LEKCI1B/12 LEKCI P4 HAWFA L607 KONAN", "EHAM"]
    # ])
    # stdDeparture(masterCallsign, controllerSock, "EGGD", 250, [
    #     ["EXMOR1Z/09 EXMOR N92 DAWLY DCT JOZMA DCT GAPLI", "KJFK"],
    #     ["BCN1Z/09 BCN P4 FELCA DCT NICXI DCT OFSOX DCT ENJEX", "KJFK"],
    #     ["BCN1Z/09 BCN P69 DIZIM N864 AVTIC N38 NOKIN P17 POL N601 INPIP", "EGPH"],
    #     ["YORQI1Z/09 YORQI L607 BIG L9 KONAN", "EHAM"]
    # ])


    # NT
    # Arrivals
    # stdArrival(masterCallsign, controllerSock, "EGNT", 120, [  # NT arrivals
    #     ["EVSON DCT POL POL1N/07", 26000, "MAN_NE_CTR"],
    #     ["EVSON DCT POL POL1N/07", 26000, "MAN_NE_CTR"],
    #     ["EVSON DCT POL POL1N/07", 26000, "MAN_NE_CTR"],
    #     ["EVSON DCT POL P18 NATEB", 26000, "MAN_NE_CTR"],
    #     ["EVSON DCT POL P18 NATEB", 26000, "MAN_NE_CTR"],
    #     ["NEXUS DCT MADAD P18 NATEB", 20000, "MAN_NE_CTR"],
    #     ["HAVEN DCT IPSAD Y96 NATEB", 20000, "MAN_NE_CTR"],
    # ])
    # stdArrival(masterCallsign, controllerSock, "EGNV", 120, [  # NV arrivals
    #     ["EVSON DCT POL P18 GASKO", 20000, "MAN_NE_CTR"],
    #     ["EVSON DCT POL P18 GASKO", 20000, "MAN_NE_CTR"],
    #     ["NEXUS DCT MADAD P18 NATEB", 19000, "MAN_NE_CTR"],
    #     ["HAVEN DCT IPSAD Y96 NATEB", 19000, "MAN_NE_CTR"],
    # ])

    # # Departures
    # stdDeparture(masterCallsign, controllerSock, "EGNT", 120, [  # NT departures
    #     ["GIRLI1T/07 GIRLI P18 GASKO P16 RIBEL UP16 CROFT DCT KEPAD L151 DISIT", "EGKK"],
    #     ["GIRLI1T/07 GIRLI P18 GASKO P16 RIBEL UP16 CROFT DCT KEPAD L151 DISIT", "EGKK"],
    #     ["GIRLI1T/07 GIRLI P18 GASKO P16 RIBEL UP16 CROFT DCT KEPAD L151 DISIT", "EGKK"],
    #     ["GIRLI1T/07 GIRLI P18 GASKO P16 RIBEL UP16 CROFT DCT KEPAD L151 DISIT", "EGKK"],
    #     ["GIRLI1T/07 GIRLI P18 GASKO P16 RIBEL UP16 CROFT DCT KEPAD L151 DISIT", "EGKK"],
    #     ["SUPIG DCT ERKIT N110 DOLAS", "EHAM"],
    #     ["SUPIG DCT ERLOT P15 GIVEM", "EGAA"],
    #     ["SUPIG DCT NATEB DCT DCS", "EHAM"]
    # ])
    # # # PF every 3 mins
    # stdDeparture(masterCallsign, controllerSock, "EGNV", 120, [  # NV departures
    #     ["NAVEL DCT GASKO P16 RIBEL UP16 CROFT DCT KEPAD L151 DISIT", "EGKK"],
    #     ["NAVEL DCT GASKO P16 RIBEL UP16 CROFT DCT KEPAD L151 DISIT", "EGKK"],
    #     ["NAVEL DCT GASKO P16 RIBEL UP16 CROFT DCT KEPAD L151 DISIT", "EGKK"],
    #     ["NAVEL DCT ERKIT N110 DOLAS", "EHAM"],
    #     ["NAVEL DCT ERLOT P15 GIVEM", "EGAA"],
    #     ["NAVEL DCT NATEB DCT DCS", "EHAM"]
    # ])


    # CLN (WIP)
    # stdTransit(masterCallsign, controllerSock, 180, [  # NOGRO
    #     ["EBBR", "EGSS", 28000, 36000, "NOGRO DCT RINIS RINIS1A", "LON_E_CTR"],
    #     ["EBBR", "EGGW", 28000, 36000, "NOGRO DCT RINIS RINIS1N", "LON_E_CTR"]
    # ], withMaster=False)
    # stdTransit(masterCallsign, controllerSock, 180, [  # GALSO
    #     ["EBBR", "EGLC", 26000, 36000, "GALSO DCT XAMAN XAMAN1C", "LON_E_CTR"],
    #     ["EBBR", "EGKK", 29000, 36000, "GALSO DCT RINIS RINIS1N", "LON_E_CTR"]
    # ], withMaster=False)


    # CC
    # stdArrival(masterCallsign, controllerSock, "EGCC", 75, [
    #     ["TNT DCT QUSHI DCT DAYNE", 7000, "EGCC_S_APP"],
    #     # ["TNT DCT QUSHI DCT DAYNE", 7000, "EGCC_S_APP"],
    #     ["WAL DCT MIRSI", 7000, "EGCC_S_APP"],
    #     # ["WAL DCT MIRSI", 7000, "EGCC_S_APP"],
    #     ["DIZZE DCT ROSUN", 8000, "EGCC_S_APP"],
    #     # ["GOLES DCT POL DCT BURNI DCT ROSUN", 11000, "EGCC_S_APP"],
    # ])
    # stdTransit(masterCallsign, controllerSock, 75, [
    #     ["EGKK", "EGCC", 10000, 36000, "QUSHI DCT DAYNE", "EGCC_S_APP"],
    #     # ["EGKK", "EGCC", 7000, 36000, "TNT DCT QUSHI DCT DAYNE", "EGCC_S_APP"],
    #     ["KJFK", "EGCC", 10000, 36000, "WAL DCT MIRSI", "EGCC_S_APP"],
    #     # ["KJFK", "EGCC", 7000, 36000, "WAL DCT MIRSI", "EGCC_S_APP"],
    #     ["EGPH", "EGCC", 10000, 36000, "DIZZE DCT ROSUN", "EGCC_S_APP"],
    #     # ["EGPH", "EGCC", 11000, 36000, "GOLES DCT POL DCT BURNI DCT ROSUN", "EGCC_S_APP"],
    # ], withMaster=False)
    #     ["EGKK", "EGCC", 11000, 36000, "QUSHI DCT DAYNE", "EGCC_S_APP"],
    #     ["KJFK", "EGCC", 11000, 36000, "WAL DCT MIRSI", "EGCC_S_APP"],
    #     ["EGPH", "EGCC", 11000, 36000, "DIZZE DCT ROSUN", "EGCC_S_APP"],
    # ], withMaster=False)
    # stdTransit(masterCallsign, controllerSock, 75, [
    #     ["EGKK", "EGCC", 20000, 36000, "ELVOS DCT TNT DCT QUSHI DCT DAYNE", "EGCC_S_APP"],
    #     ["EGKK", "EGCC", 20000, 36000, "ELVOS DCT TNT DCT QUSHI DCT DAYNE", "EGCC_S_APP"],
    #     ["EGKK", "EGCC", 20000, 36000, "ELVOS DCT TNT DCT QUSHI DCT DAYNE", "EGCC_S_APP"],
    #     ["EGKK", "EGCC", 20000, 36000, "LESTA DCT TNT DCT QUSHI DCT DAYNE", "EGCC_S_APP"],
    #     ["EGKK", "EGCC", 20000, 36000, "LESTA DCT TNT DCT QUSHI DCT DAYNE", "EGCC_S_APP"],
    #     ["EGKK", "EGCC", 20000, 36000, "LESTA DCT TNT DCT QUSHI DCT DAYNE", "EGCC_S_APP"],
    #     ["KJFK", "EGCC", 17000, 36000, "MALUD DCT WAL DCT MIRSI", "EGCC_S_APP"],
    #     ["KJFK", "EGCC", 27000, 36000, "MAKUX DCT SOSIM DCT GIGTO DCT IBRAR DCT WAL DCT MIRSI", "EGCC_S_APP"],
    #     ["KJFK", "EGCC", 20000, 36000, "AXCIS DCT MONTY DCT REXAM DCT WAL DCT MIRSI", "EGCC_S_APP"],
    #     ["KJFK", "EGCC", 20000, 36000, "AXCIS DCT MONTY DCT REXAM DCT WAL DCT MIRSI", "EGCC_S_APP"],
    #     ["EGPH", "EGCC", 20000, 36000, "LAKEY DCT DIZZE DCT ROSUN", "EGCC_S_APP"],
    #     ["EGPH", "EGCC", 25000, 36000, "TILNI DCT GASKO DCT BEGAM DCT SETEL DCT ROSUN", "EGCC_S_APP"],
    #     ["EGPH", "EGCC", 29000, 36000, "OTBED DCT GOLES DCT POL DCT BURNI DCT ROSUN", "EGCC_S_APP"],
    #     ["EGPH", "EGCC", 29000, 36000, "LISBO DCT FIZED DCT GOLES DCT POL DCT BURNI DCT ROSUN", "EGCC_S_APP"],
    #     ["EGPH", "EGCC", 29000, 36000, "LISBO DCT FIZED DCT GOLES DCT POL DCT BURNI DCT ROSUN", "EGCC_S_APP"]
    # ], withMaster=False)
    # stdDeparture(masterCallsign, controllerSock, "EGCC", 75, [  # NT departures
    #     ["SANBA1R/23R SANBA N859 KIDLI", "EGKK"],
    #     ["EKLAD1R/23R EKLAD Y53 WAL L10 PENIL L28 LELDO M145 BAGSO", "EIDW"],
    #     ["POL5R/23R POL N601 INPIP", "EGPH"],
    #     ["POL5R/23R POL N601 INPIP", "EGPH"],
    #     ["SONEX1R/23R SONEX DCT MAMUL L60 OTBED Y70 SUPEL", "EGSH"],
    #     ["SONEX1R/23R SONEX DCT MAMUL L60 OTBED Y70 SUPEL", "EGSH"],
    # ])

    ## CC TESTING ONLY
    # stdTransit(masterCallsign, controllerSock, 75, [
    #     ["EGKK", "EGCC", 8000, 36000, "TNT DCT DAYNE", "EGCC_S_APP"]
    # ], withMaster=True)
    
    # stdTransit2(masterCallsign, controllerSock, 5, [
    #     ["EGLL", "EHAM", 15000, 35000, "BPK DCT TOTRI DCT BRAIN M197 REDFA", "LTC_E_CTR"],
    # ], withMaster=True)



    with open(f"profiles/ScTMA.json") as f:
        data = json.load(f)

    if "otherControllers" in data.keys():
        OTHER_CONTROLLERS = []
        for controller in data["otherControllers"]:
            OTHER_CONTROLLERS.append(controller)

    if "activeControllers" in data.keys():
        ACTIVE_CONTROLLERS = data["activeControllers"]

    if "activeAirports" in data.keys():
        ACTIVE_RUNWAYS = data["activeAirports"]
            

    if "stdDepartures" in data.keys():
        for stdDep in data["stdDepartures"]:
            stdDeparture(masterCallsign, controllerSock, stdDep["departing"], stdDep["interval"], [
                *list(map(lambda x: [x["route"], x["arriving"]], stdDep["routes"]))
            ])

    if "stdTransits" in data.keys():
        for stdTrn in data["stdTransits"]:
            withMaster = True
            try:
                withMaster = stdTrn["withMaster"]
            except KeyError:
                pass

            stdTransit(masterCallsign, controllerSock, stdTrn["interval"], [
                *list(map(lambda x: [x["departing"], x["arriving"], x["currentLevel"], x["cruiseLevel"], x["route"], x["firstController"]], stdTrn["routes"]))
            ], withMaster=withMaster)

    if "stdArrivals" in data.keys():
        for stdArr in data["stdArrivals"]:
            stdDeparture(masterCallsign, controllerSock, stdArr["departing"], stdArr["interval"], [
                *list(map(lambda x: [x["route"], x["level"], x["firstController"]], stdArr["routes"]))
            ])

    for controller in OTHER_CONTROLLERS:
        otherControllerSocks.append(util.ControllerSocket.StartController(controller[0]))
        otherControllerSocks[-1].setblocking(False)
        

    ## PC W
    # stdTransit(masterCallsign, controllerSock, 90, [
    #     ["EIDW", "EGGP", 27000, 36000, "DUB DCT BOFUM BOFUM1L", "MAN_WI_CTR"],
    #     ["EGAA", "EGGP", 27000, 36000, "PEPOD DCT MAKUX DCT SOSIM L28 PENIL PENIL1L", "MAN_WI_CTR"],
    #     ["EGKK", "EGGP", 10000, 36000, "TNT DCT NANTI DCT KEGUN", "MAN_WL_CTR"],
    #     ["EGFF", "EGGP", 18000, 36000, "BIFCU DCT PEPZE PEPZE1L", "MAN_WL_CTR"]
    # ], withMaster=True)
    
    # stdTransit(masterCallsign, controllerSock, 90, [
    #     ["EIDW", "EGCC", 29000, 36000, "DUB DCT BOFUM Q37 MALUD MALUD1M", "MAN_WI_CTR"],
    #     ["EGAA", "EGCC", 27000, 36000, "PEPOD DCT MAKUX MAKUX1M", "MAN_WI_CTR"],
    #     ["EGFF", "EGCC", 20000, 36000, "MOCQO DCT AXCIS AXCIS1M", "MAN_WL_CTR"]
    # ], withMaster=True)

    # stdTransit(masterCallsign, controllerSock, 200, [
    #     ["EIDW", "EGNM", 29000, 36000, "DUB DCT BOFUM Q37 MALUD UL975 LYNAS L975 WAL DCT POL", "MAN_WI_CTR"],
    #     ["EGAA", "EGNM", 27000, 36000, "PEPOD DCT MAKUX L15 GIGTO UQ4 WAL DCT POL", "MAN_WI_CTR"],
    #     ["EGFF", "EGNM", 20000, 36000, "DIZIM DCT AVTIC N864 REXAM DCT BARTN DCT POL", "MAN_WL_CTR"]
    # ], withMaster=True)
    
    # stdTransit(masterCallsign, controllerSock, 200, [
    #     ["EGSH", "EGNS", 20000, 36000, "MIRSI DCT PENIL L10 KELLY", "MAN_WI_CTR"],
    # ], withMaster=True)

    # stdTransit(masterCallsign, controllerSock, 200, [
    #     ["EGSH", "EIDW", 29000, 36000, "CROFT DCT PENIL L28 LELDO M145 BAGSO", "MAN_WI_CTR"],
    # ], withMaster=True)

    # stdDeparture(masterCallsign, controllerSock, "EGCC", 200, [  # CC deps
    #     ["EKLAD1R/23R EKLAD UY53 WAL L10 PENIL UL28 LELDO M145 BAGSO", "EIDW"],
    #     ["KUXEM1R/23R KUXEM P17 NOKIN N862 WEVBE", "EGFF"]
    # ])

    # stdDeparture(masterCallsign, controllerSock, "EGGP", 200, [  # GP deps
    #     ["POL4T/27 POL P18 NATEB", "EGNT"],
    #     ["WAL2T/27 WAL L10 PENIL UL28 LELDO M145 BAGSO", "EIDW"],
    #     ["REXAM2T/27 REXAM DCT OGTAW N862 WEVBE", "EGFF"]
    # ])

    ## 27 and 28/34

    # overflights

    # stdDeparture(masterCallsign, controllerSock, "EGCC", 120, [  # CC deps
    #     ["POL5R/23R POL N601 INPIP INPIP1E", "EGPH"],
    # ])

    # npts = ["ORIST", "GARMI", "SITET", "XAMAB", "XIDIL", "KUNAV", "ALESO", "XAMAN", "SUMUM", "RINIS", "SOVAT", "IRKUN", "SOVAT", "MOTOX", "LUGIS", "ABNED", "GALSO", "NOGRO", "SOMVA", "REDFA", "GILTI", "SASKI"]
    # arrivalADs = ["EGPH", "EGPF", "EGPK", "EGPD"]

    # combList = []
    # for npt in npts:
    #     for arrivalAD in arrivalADs:
    #         combList.append([npt, arrivalAD])

    # lvl = 360

    # with open("srd.csv") as f:
    #     srd = f.read().split("\n")
    #     for line in srd:
    #         data = line.split("\t")
    #         if len(data) > 5:
    #             if data[2] == "MC":
    #                 continue

    #             if data[0] not in npts or not data[6].startswith("EG"):
    #                 continue

    #             if [data[0], data[6]] in combList:
    #                 combList.remove([data[0], data[6]])
    #                 lvl = 30000 + random.randint(0,5) * 2000

    #                 stdTransit(masterCallsign, controllerSock, 800, [
    #                     ["LFPG", data[6], lvl, lvl, data[0] + " " + data[4], "LON_M_CTR"],
    #                 ], withMaster=False)


    # DEPARTURES
    # util.PausableTimer(1, spawnEveryNSeconds, args=(240, masterCallsign, controllerSock, "DEP", ACTIVE_AERODROME), kwargs={"flightPlan": FlightPlan("I", "B738", 250, ACTIVE_AERODROME, 1130, 1130, 25000, "EHAM", Route("BPK7G/27L BPK Q295 BRAIN M197 REDFA"))})
    # util.PausableTimer(60, spawnEveryNSeconds, args=(240, masterCallsign, controllerSock, "DEP", ACTIVE_AERODROME), kwargs={"flightPlan": FlightPlan("I", "B738", 250, ACTIVE_AERODROME, 1130, 1130, 25000, "EGGD", Route("CPT3G/27L CPT"))})
    # util.PausableTimer(120, spawnEveryNSeconds, args=(240, masterCallsign, controllerSock, "DEP", ACTIVE_AERODROME), kwargs={"flightPlan": FlightPlan("I", "B738", 250, ACTIVE_AERODROME, 1130, 1130, 25000, "EGCC", Route("UMLAT1G/27L UMLAT T418 WELIN T420 ELVOS"))})
    # util.PausableTimer(180, spawnEveryNSeconds, args=(240, masterCallsign, controllerSock, "DEP", ACTIVE_AERODROME), kwargs={"flightPlan": FlightPlan("I", "B738", 250, ACTIVE_AERODROME, 1130, 1130, 25000, "LFPG", Route("MAXIT1G/27L MAXIT Y803 MID UL612 BOGNA HARDY UM605 BIBAX"))})

    # STANNERS

    # util.PausableTimer(random.randint(1, 1), spawnEveryNSeconds, args=(180, masterCallsign, controllerSock, "GPT", "J(1)_Z"), kwargs={"flightPlan": FlightPlan("I", "B738", 250, "EHAM", 1130, 1130, 36000, "EGSS", Route("CLN"))})

    # From acData


    # stdTransit(masterCallsign, controllerSock, 60, [
    #     ["EGKK", "EGCC", 20000, 20000, "PIPIN DCT LESTA DCT TNT DCT QUSHI DCT DAYNE", "MAN_CTR"],
    #     ["EGKK", "EGCC", 20000, 20000, "TIMPO DCT ELVOS DCT TNT DCT QUSHI DCT DAYNE", "MAN_CTR"],
    #     # ["KJFK", "EGCC", 17000, 36000, "MALUD DCT WAL DCT MIRSI", "EGCC_S_APP"],
    #     # ["KJFK", "EGCC", 27000, 36000, "MAKUX DCT SOSIM DCT GIGTO DCT IBRAR DCT WAL DCT MIRSI", "EGCC_S_APP"],
    #     # ["KJFK", "EGCC", 20000, 36000, "AXCIS DCT MONTY DCT REXAM DCT WAL DCT MIRSI", "EGCC_S_APP"],
    #     # ["EGPH", "EGCC", 20000, 36000, "LAKEY DCT DIZZE DCT ROSUN", "EGCC_S_APP"],
    #     # ["EGPH", "EGCC", 25000, 36000, "TILNI DCT GASKO DCT BEGAM DCT SETEL DCT ROSUN", "EGCC_S_APP"],
    #     # ["EGPH", "EGCC", 29000, 36000, "OTBED DCT GOLES DCT POL DCT BURNI DCT ROSUN", "EGCC_S_APP"],
    #     # ["EGPH", "EGCC", 29000, 36000, "LISBO DCT FIZED DCT GOLES DCT POL DCT BURNI DCT ROSUN", "EGCC_S_APP"]
    # ], withMaster=False)
    # stdDeparture(masterCallsign, controllerSock, "EGCC", 80, [  # NT departures
    #     ["SANBA1R/23R SANBA N859 KIDLI", "EGKK"],
    #     ["EKLAD1R/23R EKLAD Y53 WAL L10 PENIL L28 LELDO M145 BAGSO", "EIDW"],
    #     ["POL5R/23R POL N601 INPIP", "EGPH"],
    #     ["POL5R/23R POL N601 INPIP", "EGPH"],
    #     ["SONEX1R/23R SONEX DCT MAMUL L60 OTBED Y70 SUPEL", "EGSH"],
    #     ["SONEX1R/23R SONEX DCT MAMUL L60 OTBED Y70 SUPEL", "EGSH"],
    # ])

    # stdArrival(masterCallsign, controllerSock, "EGPH", 95, [
    #     ["HAVEN DCT TARTN", 10000, "EGPH_APP"],
    #     ["ESKDO DCT TARTN", 12000, "EGPH_APP"],
    #     ["TLA DCT TARTN", 11000, "EGPH_APP"],
    #     ["PTH DCT GRICE DCT STIRA", 11000, "EGPH_APP"],
    # ])

    # Start message monitor
    # util.PausableTimer(RADAR_UPDATE_RATE, messageMonitor, args=[controllerSock])

    # START POSITION LOOP
    # positionLoop(controllerSock)

    # Start keyboard listener
    # keyboardHandlerThread = threading.Thread(target=keyboardHandler)
    # keyboardHandlerThread.daemon = True
    # keyboardHandlerThread.start()

    k = 0
    while True:  # block forver
        positionLoop(controllerSock)

        k += 1
        if (k * RADAR_UPDATE_RATE) % (5 * 60) == 0 or saveNow:
            # shelve planes
            savestateName = "savestates/" + str(datetime.datetime.now()).replace(" ", "_").replace(":", "-")
            with shelve.open(savestateName) as savestate:
                for plane in planes:
                    tmpMasterSocketHandleData = plane.masterSocketHandleData
                    plane.masterSocketHandleData = None
                    savestate[plane.callsign] = plane
                    plane.masterSocketHandleData = tmpMasterSocketHandleData
            print("SAVED STATE AT TIME", str(datetime.datetime.now()))
        time.sleep(RADAR_UPDATE_RATE)


    print("uh oh")

    # CLEANUP ONCE UI IS CLOSED
    for planeSock in planeSocks:
        planeSock.close()

    controllerSock.close()




if __name__ == "__main__":
    main()
