import json
import msvcrt
import random
import select
import threading
import sys
import time
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QTableWidgetItem
import keyboard
from Route import Route
import re
from pynput.keyboard import Key, Listener
import pyttsx3

from uiTest import MainWindow
from sfparser import loadRunwayData, loadStarAndFixData
from FlightPlan import FlightPlan
from Plane import Plane
from PlaneMode import PlaneMode
from globalVars import FIXES, planes, planeSocks, window, otherControllerSocks, messagesToSpeak, currentSpeakingAC
from Constants import ACTIVE_CONTROLLERS, ACTIVE_RUNWAYS, HIGH_DESCENT_RATE, MASTER_CONTROLLER, MASTER_CONTROLLER_FREQ, OTHER_CONTROLLERS, RADAR_UPDATE_RATE, TAXI_SPEED, PUSH_SPEED, CLIMB_RATE, DESCENT_RATE, TRANSITION_LEVEL
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
    global planes, window, currentSpeakingAC
    # See command spec

    if command is None:
        text: str = window.commandEntry.text()

        window.commandEntry.setText("")
        window.errorLabel.setText("")
    else:
        text = command
    callsign = text.split(" ")[0]

    if callsign == "tm":  # time multiplier
        global timeMultiplier
        timeMultiplier = float(text.split(" ")[1])
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
                if plane.altitude > 10000:
                    plane.vertSpeed = HIGH_DESCENT_RATE
                else:
                    plane.vertSpeed = DESCENT_RATE

                if plane.targetAltitude >= TRANSITION_LEVEL:
                    messagesToSpeak.append(f"Descend flight level {' '.join(list(str(plane.targetAltitude // 100)))}")
                else:
                    messagesToSpeak.append(f"Descend altitude {' '.join(list(str(plane.targetAltitude // 100)))}")
            case "c":
                if plane.mode in PlaneMode.GROUND_MODES:
                    raise CommandErrorException("Cannot climb while on the ground")
                plane.targetAltitude = int(text.split(" ")[2]) * 100
                plane.vertSpeed = CLIMB_RATE

                if plane.targetAltitude >= TRANSITION_LEVEL:
                    messagesToSpeak.append(f"Climb flight level {' '.join(list(str(plane.targetAltitude // 100)))}")
                else:
                    messagesToSpeak.append(f"Climb altitude {' '.join(list(str(plane.targetAltitude // 100)))}")
            case "tl":
                if plane.mode in PlaneMode.GROUND_MODES:
                    raise CommandErrorException("Cannot change heading while on the ground")
                if plane.holdStartTime is not None:  # end holding
                    plane.holdStartTime = None
                plane.mode = PlaneMode.HEADING
                plane.targetHeading = int(text.split(" ")[2]) % 360
                plane.turnDir = "L"
                # plane.heading = int(text.split(" ")[2])

                messagesToSpeak.append(f"Turn left heading {' '.join(list(str(plane.targetHeading).zfill(3)))}")
            case "tr":
                if plane.mode in PlaneMode.GROUND_MODES:
                    raise CommandErrorException("Cannot change heading while on the ground")
                if plane.holdStartTime is not None:  # end holding
                    plane.holdStartTime = None
                plane.mode = PlaneMode.HEADING
                plane.targetHeading = int(text.split(" ")[2]) % 360
                plane.turnDir = "R"

                messagesToSpeak.append(f"Turn right heading {' '.join(list(str(plane.targetHeading).zfill(3)))}")
            case "r":
                if plane.mode in PlaneMode.GROUND_MODES:
                    raise CommandErrorException("Cannot change heading while on the ground")
                if plane.holdStartTime is not None:  # end holding
                    plane.holdStartTime = None
                plane.mode = PlaneMode.HEADING
                plane.targetHeading = plane.heading + int(text.split(" ")[2]) % 360
                plane.targetHeading = plane.targetHeading % 360
                plane.turnDir = "R"

                messagesToSpeak.append(f"Turn right by {int(text.split(' ')[2]) % 360} degrees")
            case "l":
                if plane.mode in PlaneMode.GROUND_MODES:
                    raise CommandErrorException("Cannot change heading while on the ground")
                if plane.holdStartTime is not None:  # end holding
                    plane.holdStartTime = None
                plane.mode = PlaneMode.HEADING
                plane.targetHeading = plane.heading - int(text.split(' ')[2]) % 360
                plane.targetHeading = plane.targetHeading % 360
                plane.turnDir = "L"

                messagesToSpeak.append(f"Turn left by {int(text.split(' ')[2]) % 360} degrees")
            case "sp":
                if plane.mode in PlaneMode.GROUND_MODES:
                    raise CommandErrorException("Ground speed is fixed")
                plane.targetSpeed = int(text.split(" ")[2])

                messagesToSpeak.append(f"Speed {' '.join(list(str(plane.targetSpeed)))}")
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
                plane.flightPlan.route.initial = True

                messagesToSpeak.append(f"Resume own navigation direct {text.split(' ')[2]}")
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

                messagesToSpeak.append(f"Proceed direct {text.split(' ')[2]}")
            case "sq":
                plane.squawk = int(text.split(" ")[2])

                messagesToSpeak.append(f"Squawk {list(' '.join(str(plane.squawk).zfill(4)))}")
            case "hold":
                if plane.mode in PlaneMode.GROUND_MODES:
                    raise CommandErrorException("Cannot enter hold while on the ground")
                plane.holdFix = text.split(" ")[2]

                messagesToSpeak.append(f"Hold at {text.split(' ')[2]}")
            case "star":
                if plane.mode in PlaneMode.GROUND_MODES:
                    raise CommandErrorException("Cannot assign STAR while on the ground")
                starData, extraFixes = loadStarAndFixData(plane.flightPlan.destination)
                FIXES.update(extraFixes)
                plane.flightPlan.route.fixes.extend(starData[text.split(" ")[2]][ACTIVE_RUNWAYS[plane.flightPlan.destination]].split(" "))

                messagesToSpeak.append(f"{text.split(' ')[2]} arrival")
            case "ils":
                if plane.mode in PlaneMode.GROUND_MODES:
                    raise CommandErrorException("Cannot assign ILS approach while on the ground")
                if plane.mode == PlaneMode.FLIGHTPLAN:
                    raise CommandErrorException("Need headings to intercept")
                
                try:

                    runwayData = loadRunwayData(plane.flightPlan.destination)[ACTIVE_RUNWAYS[plane.flightPlan.destination]]
                    plane.clearedILS = runwayData

                    messagesToSpeak.append(f"Cleared ILS runway {ACTIVE_RUNWAYS[plane.flightPlan.destination]}")
                except FileNotFoundError:
                    pass
            case "lvl":
                lvlFix = text.split(" ")[2]
                plane.lvlCoords = FIXES[lvlFix]

                messagesToSpeak.append(f"Be level {lvlFix}")
            case "ho":  # BIN EM
                # if text.split(" ")[2] == "KKT":  # TODO: choose airport
                index = planes.index(plane)
                planes.remove(plane)
                sock = planeSocks.pop(index)
                sock.esSend("#DP" + plane.callsign, "SERVER")
                sock.close()
                # window.aircraftTable.removeRow(index)
            case "hoai":
                plane.mode = PlaneMode.HEADING
                plane.targetAltitude = 2000
                plane.vertSpeed = DESCENT_RATE
                plane.dieOnReaching2K = True
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
        # window.errorLabel.setText(e.message)
        print(e.message)


# PLANE SPAWNING

def spawnRandomEveryNSeconds(nSeconds, data):
    choice = random.choice(data)
    util.PausableTimer(nSeconds, spawnRandomEveryNSeconds, args=(nSeconds, data))
    spawnEveryNSeconds(nSeconds, choice["masterCallsign"], choice["controllerSock"], choice["method"], *choice["args"], callsign=None, spawnOne=True, **choice["kwargs"])


def spawnEveryNSeconds(nSeconds, masterCallsign, controllerSock, method, *args, callsign=None, spawnOne=False, **kwargs):
    global planes, planeSocks

    if callsign is None:
        callsign = util.callsignGen()
    else:
        for plane in planes:
            if plane.callsign == callsign:
                return  # nonono bug

    timeWiggle = 0
    if method == "ARR":
        timeWiggle = random.randint(-15, 15)

    if not spawnOne:
        util.PausableTimer(nSeconds + timeWiggle, spawnEveryNSeconds, args=(nSeconds, masterCallsign, controllerSock, method, *args), kwargs=kwargs)

    fp: FlightPlan = kwargs["flightPlan"]
    kwargs.pop("flightPlan")

    hdg = -1
    if "hdg" in kwargs:
        hdg = kwargs["hdg"]
        kwargs.pop("hdg")

    if method == "ARR":
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

    # if method == "ARR":
    #     util.PausableTimer(11, sock.sendall, args=[b'$CQLON_S_CTR:@94835:SC:' + plane.callsign.encode("UTF-8") + b':' + fp.route.fixes[-1].encode("UTF-8") + b'\r\n'])

    planeSocks.append(sock)

    # window.aircraftTable.setRowCount(sum([1 for plane in planes if plane.currentlyWithData is None]))

    # dc = 0
    # for plane in planes:
    #     if plane.currentlyWithData is None:
    #         window.aircraftTable.setItem(dc, 0, QTableWidgetItem(plane.callsign))
    #         window.aircraftTable.setItem(dc, 1, QTableWidgetItem(util.modeConverter(plane.mode)))
    #         window.aircraftTable.setItem(dc, 2, QTableWidgetItem(str(plane.squawk)))
    #         window.aircraftTable.setItem(dc, 3, QTableWidgetItem(str(plane.speed)))
    #         window.aircraftTable.setItem(dc, 4, QTableWidgetItem(str(plane.currentSector)))
    #         dc += 1

# MAIN LOOP


def positionLoop(controllerSock: util.ControllerSocket):
    global planes
    # util.PausableTimer(RADAR_UPDATE_RATE, positionLoop, args=[controllerSock])

    t0 = time.time()

    controllerSock.esSend("%" + MASTER_CONTROLLER, MASTER_CONTROLLER_FREQ, "3", "100", "7", "51.14806", "-0.19028", "0")

    for i, otherControllerSock in enumerate(otherControllerSocks):  # update controller pos
        otherControllerSock.esSend("%" + OTHER_CONTROLLERS[i][0], OTHER_CONTROLLERS[i][1], "3", "100", "7", "51.14806", "-0.19028", "0")

    dc = 0  # display counter
    for i, plane in enumerate(planes):  # update plane pos
        try:
            planeSocks[i].sendall(plane.positionUpdateText())  # position update
        except OSError:
            pass  # probably means we've just killed them. If not then lol

        # if plane.currentlyWithData is None:  # We only know who they are if they are with us
        #     print(plane.callsign, end=", ")
        #     window.aircraftTable.setItem(dc, 0, QTableWidgetItem(plane.callsign))
        #     window.aircraftTable.setItem(dc, 1, QTableWidgetItem(util.modeConverter(plane.mode)))
        #     window.aircraftTable.setItem(dc, 2, QTableWidgetItem(str(plane.squawk)))
        #     window.aircraftTable.setItem(dc, 3, QTableWidgetItem(str(plane.speed)))
        #     window.aircraftTable.setItem(dc, 4, QTableWidgetItem(str(plane.currentSector)))
        #     dc += 1

    print()

    messageMonitor(controllerSock)

    t1 = time.time()
    print("Position Loop took", str(t1 - t0), "seconds")


def messageMonitor(controllerSock: util.ControllerSocket) -> None:
    global window  # PAUSING WON'T WORK ATM
    # t = threading.Timer(RADAR_UPDATE_RATE, messageMonitor, args=[controllerSock])  # regular timer as should never be paused
    # t.daemon = True
    # t.start()
    
    t0 = time.time()

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
                            if toController.endswith("APP"):  # proceed direct airport, descend to 2k, then kill at airport
                                parseCommand(f"{callsign} hoai")
                            
                            index = planes.index(plane)
                            plane.currentlyWithData = (MASTER_CONTROLLER, None)
                            # window.aircraftTable.removeRow(index)
                            break
                elif message.startswith("$HA"):  # accept handoff
                    callsign = message.split(":")[2]
                    for plane in planes:
                        if plane.callsign == callsign:
                            index = planes.index(plane)
                            plane.currentlyWithData = None
                            # window.aircraftTable.setRowCount(sum([1 for plane in planes if plane.currentlyWithData is None]))
                            break
                elif message.startswith("$AM"):
                    cs = message.split(":")[2]
                    fp = message.split(":")[-1]
                    star = fp.split(" ")[-1]
                    if re.match(r'[A-Z]+\d[A-Z]\/\d+[LRC]*', star):
                        star = star.split("/")[0]
                        
                        parseCommand(f"{cs} star {star}")
                elif (m := re.match(r'^\$CQ' + contr + r':@94835:SC:(.*?):H([0-9]+)$', message)):
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
                    print(message)
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
                else:
                    pass
                    # print(message)

        # print()

    t1 = time.time()
    print("Message Monitor took", str(t1 - t0), "seconds")


def cellClicked(row, _col):
    global window
    window.commandEntry.setText(window.aircraftTable.item(row, 0).text() + " ")
    window.commandEntry.setFocus()


def stdArrival(masterCallsign, controllerSock, ad, delay, planLvlData):
    parsedData = []
    for currentData in planLvlData:
        route, lvl, ctrl = currentData
        parsedData.append({"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": [route.split(" ")[0]], "kwargs": {"speed": (350 if lvl >= 10000 else 250), "altitude": lvl, "flightPlan": FlightPlan.arrivalPlan(ad, route), "currentlyWithData": (masterCallsign, route.split(" ")[2]), "firstController": ctrl}})
    util.PausableTimer(random.randint(5, 40), spawnRandomEveryNSeconds, args=(delay, parsedData))

def stdDeparture(masterCallsign, controllerSock, ad, delay, planLvlData):
    parsedData = []
    for currentData in planLvlData:
        route, arrAd = currentData
        parsedData.append({"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "DEP", "args": [ad], "kwargs": {"flightPlan": FlightPlan("I", "B738", 250, ad, 1130, 1130, 25000, arrAd, Route(route, ad))}})
    util.PausableTimer(random.randint(5, 40), spawnRandomEveryNSeconds, args=(delay, parsedData))


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
    global planes, planeSocks, window, ACTIVE_RUNWAYS, ACTIVE_CONTROLLERS
    # SETUP PLANES

    masterCallsign = MASTER_CONTROLLER

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
    # for alt in range(8000, 12000 + 1000, 1000):
    #     plane = Plane.requestFromFix(util.callsignGen(), "TIMBA", squawk=util.squawkGen(), speed=220, altitude=alt, flightPlan=FlightPlan.arrivalPlan("TIMBA"), currentlyWithData=(masterCallsign, "TIMBA"))
    #     plane.holdFix = "TIMBA"
    #     planes.append(plane)

    # for alt in range(8000, 12000 + 1000, 1000):
    #     plane = Plane.requestFromFix(util.callsignGen(), "WILLO", squawk=util.squawkGen(), speed=220, altitude=alt, flightPlan=FlightPlan.arrivalPlan("WILLO"), currentlyWithData=(masterCallsign, "WILLO"))
    #     plane.holdFix = "WILLO"
    #     planes.append(plane)

    # HEATHROW IN THE HOLD

    # llHoldFixes = ["BIG", "OCK", "BNN", "LAM"]

    # for holdFix in llHoldFixes:
    #     for alt in range(8000, 13000 + 1 * 1000, 1000):
    #         plane = Plane.requestFromFix(util.callsignGen(), holdFix, squawk=util.squawkGen(), speed=220, altitude=alt, flightPlan=FlightPlan.arrivalPlan("EGLL", holdFix), currentlyWithData=(masterCallsign, holdFix))
    #         plane.holdFix = holdFix
    #         planes.append(plane)

    # LC IN THE HOLD

    # llHoldFixes = ["GODLU", "JACKO"]

    # for holdFix in llHoldFixes:
    #     for alt in range(8000, 10000 + 1 * 1000, 1000):
    #         plane = Plane.requestFromFix(util.callsignGen(), holdFix, squawk=util.squawkGen(), speed=210, altitude=alt, flightPlan=FlightPlan.arrivalPlan("EGLC", holdFix), currentlyWithData=(masterCallsign, holdFix))
    #         plane.holdFix = holdFix
    #         planes.append(plane)

    controllerSock: util.ControllerSocket = util.ControllerSocket.StartController(masterCallsign)
    controllerSock.setblocking(False)

    for controller in OTHER_CONTROLLERS:
        otherControllerSocks.append(util.ControllerSocket.StartController(controller[0]))
        otherControllerSocks[-1].setblocking(False)

    for plane in planes:
        planeSocks.append(util.PlaneSocket.StartPlane(plane, masterCallsign, controllerSock))

    # SETUP UI

    # app = QtWidgets.QApplication(sys.argv)

    # window = MainWindow()

    # util.PausableTimer(1, spawnEveryNSeconds, args=(540, masterCallsign, controllerSock, "DEP", "EGGW"), kwargs={"flightPlan": FlightPlan("I", "B738", 250, "EGGW", 1130, 1130, 27000, "EHAM", Route("MATCH Q295 BRAIN P44 DAGGA M85 ITVIP"))})

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

    # HEATHROW INT
    # timeBetween = 90  # s
    # minHoldLevel = 11000
    # util.PausableTimer(random.randint(1, 5), spawnEveryNSeconds, args=(timeBetween * 4, masterCallsign, controllerSock, "ARR", "NOVMA"), kwargs={"speed": 220, "altitude": minHoldLevel, "flightPlan": FlightPlan.arrivalPlan("EGLL", "NOVMA DCT OCK"), "currentlyWithData": (masterCallsign, "OCK")})
    # util.PausableTimer(random.randint(timeBetween - 20, timeBetween + 20), spawnEveryNSeconds, args=(timeBetween * 4, masterCallsign, controllerSock, "ARR", "ODVIK"), kwargs={"speed": 220, "altitude": minHoldLevel, "flightPlan": FlightPlan.arrivalPlan("EGLL", "ODVIK DCT BIG"), "currentlyWithData": (masterCallsign, "BIG")})
    # util.PausableTimer(random.randint(timeBetween * 2 - 20, timeBetween * 2 + 20), spawnEveryNSeconds, args=(timeBetween * 4, masterCallsign, controllerSock, "ARR", "BRAIN"), kwargs={"speed": 220, "altitude": minHoldLevel, "flightPlan": FlightPlan.arrivalPlan("EGLL", "BRAIN DCT LAM"), "currentlyWithData": (masterCallsign, "LAM")})
    # util.PausableTimer(random.randint(timeBetween * 3 - 20, timeBetween * 3 + 20), spawnEveryNSeconds, args=(timeBetween * 4, masterCallsign, controllerSock, "ARR", "COWLY"), kwargs={"speed": 220, "altitude": minHoldLevel, "flightPlan": FlightPlan.arrivalPlan("EGLL", "COWLY DCT BNN"), "currentlyWithData": (masterCallsign, "BNN")})

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
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["HAVEN"], "kwargs": {"speed": 250, "altitude": 8000, "flightPlan": FlightPlan.arrivalPlan("EGPH", "HAVEN DCT TARTN"), "currentlyWithData": (masterCallsign, "TARTN")}},
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["PTH"], "kwargs": {"speed": 250, "altitude": 8000, "flightPlan": FlightPlan.arrivalPlan("EGPH", "PTH DCT GRICE"), "currentlyWithData": (masterCallsign, "GRICE")}}
    # ]))

    # STC

    # Arrivals
    # PH every 2.5 mins
    # util.PausableTimer(5, spawnRandomEveryNSeconds, args=(180, [
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["ABEVI"], "kwargs": {"speed": 350, "altitude": 26000, "flightPlan": FlightPlan.arrivalPlan("EGPH", "ABEVI DCT INPIP"), "currentlyWithData": (masterCallsign, "INPIP")}},  # south
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["ABEVI"], "kwargs": {"speed": 350, "altitude": 26000, "flightPlan": FlightPlan.arrivalPlan("EGPH", "ABEVI DCT INPIP"), "currentlyWithData": (masterCallsign, "INPIP")}},  # south
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["ABEVI"], "kwargs": {"speed": 350, "altitude": 26000, "flightPlan": FlightPlan.arrivalPlan("EGPH", "ABEVI DCT INPIP"), "currentlyWithData": (masterCallsign, "INPIP")}},  # south
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["ABEVI"], "kwargs": {"speed": 350, "altitude": 26000, "flightPlan": FlightPlan.arrivalPlan("EGPH", "ABEVI DCT INPIP"), "currentlyWithData": (masterCallsign, "INPIP")}},  # south
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["DIGBI"], "kwargs": {"speed": 350, "altitude": 26000, "flightPlan": FlightPlan.arrivalPlan("EGPH", "DIGBI DCT AGPED"), "currentlyWithData": (masterCallsign, "AGPED")}},  # east
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["BLACA"], "kwargs": {"speed": 350, "altitude": 17000, "flightPlan": FlightPlan.arrivalPlan("EGPH", "BLACA DCT TUNSO"), "currentlyWithData": (masterCallsign, "TUNSO")}},  # west
    # ]))
    # # PF every 3 mins
    # util.PausableTimer(5, spawnRandomEveryNSeconds, args=(180, [
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["NELSA"], "kwargs": {"speed": 350, "altitude": 26000, "flightPlan": FlightPlan.arrivalPlan("EGPF", "NELSA DCT RIBEL"), "currentlyWithData": (masterCallsign, "RIBEL")}},  # south
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["NELSA"], "kwargs": {"speed": 350, "altitude": 26000, "flightPlan": FlightPlan.arrivalPlan("EGPF", "NELSA DCT RIBEL"), "currentlyWithData": (masterCallsign, "RIBEL")}},  # south
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["NELSA"], "kwargs": {"speed": 350, "altitude": 26000, "flightPlan": FlightPlan.arrivalPlan("EGPF", "NELSA DCT RIBEL"), "currentlyWithData": (masterCallsign, "RIBEL")}},  # south
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["NELSA"], "kwargs": {"speed": 350, "altitude": 26000, "flightPlan": FlightPlan.arrivalPlan("EGPF", "NELSA DCT RIBEL"), "currentlyWithData": (masterCallsign, "RIBEL")}},  # south
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["DIGBI"], "kwargs": {"speed": 350, "altitude": 26000, "flightPlan": FlightPlan.arrivalPlan("EGPF", "DIGBI DCT AGPED"), "currentlyWithData": (masterCallsign, "AGPED")}},  # east
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["BLACA"], "kwargs": {"speed": 350, "altitude": 15000, "flightPlan": FlightPlan.arrivalPlan("EGPF", "BLACA DCT GIRVA"), "currentlyWithData": (masterCallsign, "GIRVA")}},  # west
    # ]))
    # # PK every 3 mins
    # util.PausableTimer(5, spawnRandomEveryNSeconds, args=(180, [
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["NELSA"], "kwargs": {"speed": 350, "altitude": 26000, "flightPlan": FlightPlan.arrivalPlan("EGPK", "NELSA DCT RIBEL"), "currentlyWithData": (masterCallsign, "RIBEL")}},  # south
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["NELSA"], "kwargs": {"speed": 350, "altitude": 26000, "flightPlan": FlightPlan.arrivalPlan("EGPK", "NELSA DCT RIBEL"), "currentlyWithData": (masterCallsign, "RIBEL")}},  # south
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["NELSA"], "kwargs": {"speed": 350, "altitude": 26000, "flightPlan": FlightPlan.arrivalPlan("EGPK", "NELSA DCT RIBEL"), "currentlyWithData": (masterCallsign, "RIBEL")}},  # south
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["NELSA"], "kwargs": {"speed": 350, "altitude": 26000, "flightPlan": FlightPlan.arrivalPlan("EGPK", "NELSA DCT RIBEL"), "currentlyWithData": (masterCallsign, "RIBEL")}},  # south
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["NATEB"], "kwargs": {"speed": 350, "altitude": 26000, "flightPlan": FlightPlan.arrivalPlan("EGPK", "NATEB Y96 TLA DCT TRN"), "currentlyWithData": (masterCallsign, "AGPED")}},  # east
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "ARR", "args": ["IPSET"], "kwargs": {"speed": 250, "altitude": 10000, "flightPlan": FlightPlan.arrivalPlan("EGPK", "IPSET DCT BLACA"), "currentlyWithData": (masterCallsign, "BLACA")}},  # west
    # ]))

    # # Departures
    # # PH every 2 mins
    # util.PausableTimer(5, spawnRandomEveryNSeconds, args=(180, [
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "DEP", "args": ["EGPH"], "kwargs": {"flightPlan": FlightPlan("I", "B738", 250, "EGPH", 1130, 1130, 31000, "EGKK", Route("GOSAM1D/06 GOSAM P600 FENIK L612 HON N859 KIDLI", "EGPH"))}},  # south
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "DEP", "args": ["EGPH"], "kwargs": {"flightPlan": FlightPlan("I", "B738", 250, "EGPH", 1130, 1130, 31000, "EGKK", Route("GOSAM1D/06 GOSAM P600 FENIK L612 HON N859 KIDLI", "EGPH"))}},  # south
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "DEP", "args": ["EGPH"], "kwargs": {"flightPlan": FlightPlan("I", "B738", 250, "EGPH", 1130, 1130, 31000, "EGKK", Route("GOSAM1D/06 GOSAM P600 FENIK L612 HON N859 KIDLI", "EGPH"))}},  # south
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "DEP", "args": ["EGPH"], "kwargs": {"flightPlan": FlightPlan("I", "B738", 250, "EGPH", 1130, 1130, 22000, "EGAA", Route("GOSAM1D/06 GOSAM P600 BLACA DCT BELZU", "EGPH"))}},  # west
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "DEP", "args": ["EGPH"], "kwargs": {"flightPlan": FlightPlan("I", "B738", 250, "EGPH", 1130, 1130, 37000, "EHAM", Route("TLA6D/06 TLA Y96 NATEB N610 LONAM", "EGPH"))}},  # east
    # ]))
    # # PF every 3 mins
    # util.PausableTimer(5, spawnRandomEveryNSeconds, args=(180, [
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "DEP", "args": ["EGPF"], "kwargs": {"flightPlan": FlightPlan("I", "B738", 250, "EGPF", 1130, 1130, 31000, "EGKK", Route("NORBO1J/05 NORBO T256 ROVLA UT256 DCS UN864 SUBUK DCT KEPAD L151 DISIT", "EGPF"))}},  # south
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "DEP", "args": ["EGPF"], "kwargs": {"flightPlan": FlightPlan("I", "B738", 250, "EGPF", 1130, 1130, 31000, "EGKK", Route("NORBO1J/05 NORBO T256 ROVLA UT256 DCS UN864 SUBUK DCT KEPAD L151 DISIT", "EGPF"))}},  # south
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "DEP", "args": ["EGPF"], "kwargs": {"flightPlan": FlightPlan("I", "B738", 250, "EGPF", 1130, 1130, 22000, "EGAA", Route("NORBO1J/05 NORBO L186 TRN P600 BLACA DCT BELZU", "EGPF"))}},  # west
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "DEP", "args": ["EGPF"], "kwargs": {"flightPlan": FlightPlan("I", "B738", 250, "EGPF", 1130, 1130, 37000, "EHAM", Route("NORBO1J/05 NORBO Y96 NATEB N610 LONAM", "EGPF"))}},  # east
    # ]))
    # # PK every 3 mins
    # util.PausableTimer(5, spawnRandomEveryNSeconds, args=(180, [
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "DEP", "args": ["EGPK"], "kwargs": {"flightPlan": FlightPlan("I", "B738", 250, "EGPK", 1130, 1130, 31000, "EGKK", Route("SUDBY1L/12 SUDBY Z249 OSMEG T256 DCS L612 HON N859 KIDLI", "EGPK"))}},  # south
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "DEP", "args": ["EGPK"], "kwargs": {"flightPlan": FlightPlan("I", "B738", 250, "EGPK", 1130, 1130, 31000, "EGKK", Route("SUDBY1L/12 SUDBY Z249 OSMEG T256 DCS L612 HON N859 KIDLI", "EGPK"))}},  # south
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "DEP", "args": ["EGPK"], "kwargs": {"flightPlan": FlightPlan("I", "B738", 250, "EGPK", 1130, 1130, 22000, "EGAA", Route("TRN2L/12 P600 BLACA DCT BELZU", "EGPK"))}},  # west
    #     {"masterCallsign": masterCallsign, "controllerSock": controllerSock, "method": "DEP", "args": ["EGPK"], "kwargs": {"flightPlan": FlightPlan("I", "B738", 250, "EGPK", 1130, 1130, 37000, "EHAM", Route("SUMIN1L/12 SUMIN Z250 HAVEN Y96 NATEB N610 LONAM", "EGPK"))}},  # east
    # ]))

    # LTC-S
    stdArrival(masterCallsign, controllerSock, "EGKK", 90, [  # KK arrivals
        ["KUNAV DCT AMDUT DCT SFD DCT WILLO", 16000, "LTC_SE_CTR"],
        ["TEBRA DCT ABTUM DCT ARNUN DCT LARCK DCT TIMBA", 14000, "LTC_SE_CTR"],
        ["KONAN DCT KONAN DCT ARNUN DCT LARCK DCT TIMBA", 12000, "LTC_SE_CTR"],  # !
        ["AVANT DCT GWC DCT HOLLY DCT WILLO", 13000, "LTC_SW_CTR"],
        ["CAWZE DCT SIRIC DCT NIGIT DCT MID DCT TUFOZ DCT HOLLY DCT WILLO", 14000, "LTC_SW_CTR"],
        ["DISIT DCT KIDLI DCT MID DCT TUFOZ DCT HOLLY DCT WILLO", 15000, "LTC_SW_CTR"]
    ])

    stdArrival(masterCallsign, controllerSock, "EGLL", 75, [  # LL arrivals
        ["ROTNO DCT ETVAX DCT TIGER DCT BIG", 18000, "LTC_SE_CTR"],
        ["ROTNO DCT ETVAX DCT TIGER DCT BIG", 18000, "LTC_SE_CTR"],
        ["BEGTO DCT HAZEL DCT OCK", 13000, "LTC_SW_CTR"],
        ["CAWZE DCT SIRIC DCT NIGIT DCT OCK", 14000, "LTC_SW_CTR"],

        # ["SOPIT DCT WCO DCT BNN", 15000, "LTC_N_CTR"],
        # ["SABER DCT BRASO DCT WESUL DCT LAM", 16000, "LTC_N_CTR"]
    ])

    # stdArrival(masterCallsign, controllerSock, "EGSS", 140, [  # SS arrivals
    #     ["AVANT DCT HAZEL DCT SILVA DCT BOMBO DCT BKY DCT BUSTA DCT LOREL", 13000, "LTC_N_CTR"],
    #     ["ROGBI DCT FINMA DCT BOMBO DCT BKY DCT BUSTA DCT LOREL", 15000, "LTC_N_CTR"],
    #     ["VATON DCT BPK DCT BKY DCT BUSTA DCT LOREL", 16000, "LTC_N_CTR"],
    # ])

    # stdArrival(masterCallsign, controllerSock, "EGGW", 140, [  # GW arrivals
    #     ["AVANT DCT HAZEL DCT SILVA DCT WOBUN DCT EDCOX DCT JUMZI DCT ZAGZO", 13000, "LTC_N_CTR"],
    #     ["ROGBI DCT FINMA DCT WOBUN DCT EDCOX DCT JUMZI DCT ZAGZO", 15000, "LTC_N_CTR"],
    #     ["VATON DCT OZZOT DCT BPK DCT ILLOC DCT OXDUF DCT COCCU DCT JUMZI DCT ZAGZO", 16000, "LTC_N_CTR"],
    #     ["MUCTE DCT OFJES DCT UDDIZ DCT COCCU DCT JUMZI DCT ZAGZO", 14000, "LTC_N_CTR"],
    # ])

    stdDeparture(masterCallsign, controllerSock, "EGKK", 90, [  # KK departures
        ["HARDY1X/26L HARDY M605 XIDIL", "LFPG"],
        ["NOVMA1X/26L NOVMA L620 NIBDA N14 HEKXA Q63 SAWPE", "EGGD"],
        ["NOVMA1X/26L NOVMA L620 GIBSO", "EGTE"],
        ["MIMFO1M/26L MIMFO Y312 DVR L9 KONAN", "EHAM"],
        ["LAM6M/26L LAM UN57 WELIN T420 ELVOS", "EGCC"],
        ["FRANE1M/26L FRANE M604 GASBA M189 CLN DCT BANEM", "EGSH"]
    ])

    stdDeparture(masterCallsign, controllerSock, "EGLL", 90, [  # LL departures
        ["MAXIT1F/27R MAXIT Y803 MID L612 BOGNA DCT HARDY M605 XIDIL", "LFPG"],
        ["CPT3F/27R CPT Q63 SAWPE", "EGGD"],
        ["GOGSI2F/27R GOGSI N621 SAM DCT GIBSO", "EGTE"],
        ["DET2F/27R L6 DVR UL9 KONAN", "EHAM"],

        ["UMLAT1F/27R UMLAT T418 WELIN T420 ELVOS", "EGCC"],
        ["BPK7F/27R BPK Q295 BRAIN M197 REDFA", "EHAM"]
    ])

    # stdDeparture(masterCallsign, controllerSock, "EGSS", 240, [  # SS departures
    #     ["DET2R/22 DET M604 LYD M189 WAFFU UM605 XIDIL", "LFPG"],
    #     ["NUGBO1R/22 NUGBO M183 SILVA P86 SAWPE", "EGGD"]
    # ])

    # stdDeparture(masterCallsign, controllerSock, "EGGW", 180, [  # GW departures
    #     ["DET3Y/25 DET DCT TIMBA", "EGKK"],
    #     ["RODNI1B/25 RODNI N27 ICTAM", "EGGD"],
    # ])

    # SS
    # stdArrival(masterCallsign, controllerSock, "EGSS", 95, [  # SS arrivals
    #     ["BOMBO DCT BKY DCT BUSTA DCT LOREL", 9000],
    #     ["BPK DCT BKY DCT BUSTA DCT LOREL", 9000],
    #     ["LOFFO DCT ABBOT", 9000],
    #     ["CLN DCT ABBOT", 9000],
    #     ["LAPRA DCT ABBOT", 9000]
    # ])

    # stdArrival(masterCallsign, controllerSock, "EGGW", 110, [  # GW arrivals
    #     ["OXDUF DCT COCCU DCT JUMZI DCT ZAGZO", 9000],
    #     ["WOBUN DCT EDCOX DCT JUMZI DCT ZAGZO", 9000],
    #     ["LOFFO DCT ABBOT", 9000],
    #     ["CLN DCT ABBOT", 9000],
    # ])

    # NX
    # stdArrival(masterCallsign, controllerSock, "EGNX", 100, [
    #     ["WELIN DCT PIGOT", 9999],
    #     ["XAPOS DCT ROKUP", 8000]
    # ])

    # stdDeparture(masterCallsign, controllerSock, "EGNX", 100, [
    #     ["DTY4P/09 DTY", "EGKK"],
    #     ["POL2P/09 POL", "EGCC"],
    #     ["TNT3P/09 TNT", "EGCC"]
    # ])

    # LC
    # stdArrival(masterCallsign, controllerSock, "EGLC", 110, [
    #     ["RATLO DCT JACKO", 9000, "THAMES_APP"],
    #     ["ERKEX DCT GODLU", 9999, "THAMES_APP"]
    # ])

    # stdArrival(masterCallsign, controllerSock, "EGMC", 100, [
    #     ["SUMUM DCT LOGAN DCT JACKO DCT GEGMU", 9999, "THAMES_APP"],
    #     ["ABBOT DCT SABER", 4000, "EGMC_APP"]
    # ])


    # stdDeparture(masterCallsign, controllerSock, "EGLC", 120, [
    #     ["BPK1H/09 BPK", "EGCC"],
    #     ["ODUKU1H/09 ODUKU", "EGCC"],
    #     ["SOQQA1H/09 SOQQA", "EGCC"]
    # ])

    
    # DEPARTURES
    # util.PausableTimer(1, spawnEveryNSeconds, args=(240, masterCallsign, controllerSock, "DEP", ACTIVE_AERODROME), kwargs={"flightPlan": FlightPlan("I", "B738", 250, ACTIVE_AERODROME, 1130, 1130, 25000, "EHAM", Route("BPK7G/27L BPK Q295 BRAIN M197 REDFA"))})
    # util.PausableTimer(60, spawnEveryNSeconds, args=(240, masterCallsign, controllerSock, "DEP", ACTIVE_AERODROME), kwargs={"flightPlan": FlightPlan("I", "B738", 250, ACTIVE_AERODROME, 1130, 1130, 25000, "EGGD", Route("CPT3G/27L CPT"))})
    # util.PausableTimer(120, spawnEveryNSeconds, args=(240, masterCallsign, controllerSock, "DEP", ACTIVE_AERODROME), kwargs={"flightPlan": FlightPlan("I", "B738", 250, ACTIVE_AERODROME, 1130, 1130, 25000, "EGCC", Route("UMLAT1G/27L UMLAT T418 WELIN T420 ELVOS"))})
    # util.PausableTimer(180, spawnEveryNSeconds, args=(240, masterCallsign, controllerSock, "DEP", ACTIVE_AERODROME), kwargs={"flightPlan": FlightPlan("I", "B738", 250, ACTIVE_AERODROME, 1130, 1130, 25000, "LFPG", Route("MAXIT1G/27L MAXIT Y803 MID UL612 BOGNA HARDY UM605 BIBAX"))})

    # STANNERS

    # util.PausableTimer(random.randint(1, 1), spawnEveryNSeconds, args=(180, masterCallsign, controllerSock, "GPT", "J(1)_Z"), kwargs={"flightPlan": FlightPlan("I", "B738", 250, "EHAM", 1130, 1130, 36000, "EGSS", Route("CLN"))})

    # From acData

    FROM_ACDATA = False

    if FROM_ACDATA:

        depAdsDelay = {}
        arrAdsDelay = {}

        with open("flightdata/acData2.txt", "r") as f:
            acs = f.read().split("\n")
            # k = 0
            random.shuffle(acs)
            for ac in acs:
                acData = json.loads(ac.replace("'", '"'))
                if (acData[2] in ["EGKK", "EGLL", "EGSS"] and acData[3] in ["EGPH", "EGNX", "EGNM", "EGCC", "EGBB", "EGNR"]) or (acData[2] in ["EGCC", "EGNX", "EGGP", "EGBB", "EGNR"] and (acData[3] in ["EGKK", "EGLL", "EGSS", "EGBB", "EGNX"] or (not acData[3].startswith("EG") and not acData[3].startswith("EI")))):
                    if acData[2] not in depAdsDelay:
                        depAdsDelay[acData[2]] = 180 * random.random()
                    else:
                        depAdsDelay[acData[2]] += 120 + 360 * random.random()
                    
                    util.PausableTimer(depAdsDelay[acData[2]], spawnEveryNSeconds, args=(10000, masterCallsign, controllerSock, "DEP", acData[2]), kwargs={"callsign": acData[0], "flightPlan": FlightPlan("I", acData[1], 250, acData[2], 1130, 1130, acData[4], acData[3], Route(acData[5], acData[2]))})
                # elif (acData[3] in ["EGCC", "EGPH", "EGGP", "EGNR"]) or (acData[3] in ["EGNX", "EGBB"] and (not acData[2].startswith("EG"))):
                #     if acData[3] not in arrAdsDelay:
                #         arrAdsDelay[acData[3]] = 360 * random.random()
                #     else:
                #         arrAdsDelay[acData[3]] += 120 + 720 * random.random()

                #     tmpRoute = Route(acData[5])
                #     if len(tmpRoute.fixes) == 0:
                #         continue

                #     alt = 25000
                #     if acData[4].startswith("FL"):
                #         alt = int(acData[4][2:]) * 100
                #     else:
                #         try:
                #             alt = int(acData[4])
                #         except ValueError:
                #             pass

                #     if alt > 10000:
                #         sp = 350
                #     else:
                #         sp = 250
                #     util.PausableTimer(arrAdsDelay[acData[3]], spawnEveryNSeconds, args=(10000, masterCallsign, controllerSock, "ARR", tmpRoute.fixes[0]), kwargs={"callsign": acData[0], "speed": sp, "altitude": alt, "flightPlan": FlightPlan("I", acData[1], 250, acData[2], 1130, 1130, acData[4], acData[3], Route(acData[5] + " " + acData[3]))})

                # if acData[2] == "EGKK":

                #     util.PausableTimer(1, spawnEveryNSeconds, args=(1000, masterCallsign, controllerSock, "DEP", acData[2]), kwargs={"flightPlan": FlightPlan("I", acData[1], 250, acData[2], 1130, 1130, acData[4], acData[3], Route(acData[5]))})
                #     k += 1
                #     if k == 5:
                #         break

    # Start message monitor
    # util.PausableTimer(RADAR_UPDATE_RATE, messageMonitor, args=[controllerSock])

    # window.aircraftTable.setRowCount(sum([1 for plane in planes if plane.currentlyWithData is None]))

    # window.commandEntry.returnPressed.connect(parseCommand)
    # window.aircraftTable.cellClicked.connect(cellClicked)
    # window.show()

    # START POSITION LOOP
    # positionLoop(controllerSock)

    # START UI
    # app.exec()

    # Start keyboard listener
    # keyboardHandlerThread = threading.Thread(target=keyboardHandler)
    # keyboardHandlerThread.daemon = True
    # keyboardHandlerThread.start()

    while True:  # block forver
        positionLoop(controllerSock)
        time.sleep(RADAR_UPDATE_RATE)


    print("uh oh")

    # CLEANUP ONCE UI IS CLOSED
    for planeSock in planeSocks:
        planeSock.close()

    controllerSock.close()


if __name__ == "__main__":
    main()
