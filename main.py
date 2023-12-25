import random
import select
import threading
import sys
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QTableWidgetItem

from uiTest import MainWindow
from sfparser import loadRunwayData, loadStarAndFixData
from Route import Route
from FlightPlan import FlightPlan
from Plane import Plane
from PlaneMode import PlaneMode
from globalVars import FIXES
from Constants import ACTIVE_CONTROLLER, MASTER_CONTROLLER, MASTER_CONTROLLER_FREQ, ACTIVE_AERODROME, ACTIVE_RUNWAY, TAXI_SPEED, PUSH_SPEED, CLIMB_RATE, DESCENT_RATE
import util
import taxiCoordGen


# COMMAND PARSING


class CommandErrorException(Exception):
    def __init__(self, message):
        self.message = message


def parseCommand():
    # See command spec
    text: str = window.commandEntry.text()

    window.commandEntry.setText("")
    window.errorLabel.setText("")
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

    try:
        match baseCommand:
            case "d":
                if plane.mode in PlaneMode.GROUND_MODES:
                    raise CommandErrorException("Cannot descend while on the ground")
                plane.targetAltitude = int(text.split(" ")[2]) * 100
                plane.vertSpeed = DESCENT_RATE
            case "c":
                if plane.mode in PlaneMode.GROUND_MODES:
                    raise CommandErrorException("Cannot climb while on the ground")
                plane.targetAltitude = int(text.split(" ")[2]) * 100
                plane.vertSpeed = CLIMB_RATE
            case "tl":
                if plane.mode in PlaneMode.GROUND_MODES:
                    raise CommandErrorException("Cannot change heading while on the ground")
                if plane.holdStartTime is not None:  # end holding
                    plane.holdStartTime = None
                plane.mode = PlaneMode.HEADING
                plane.targetHeading = int(text.split(" ")[2]) % 360
                plane.turnDir = "L"
                # plane.heading = int(text.split(" ")[2])
            case "tr":
                if plane.mode in PlaneMode.GROUND_MODES:
                    raise CommandErrorException("Cannot change heading while on the ground")
                if plane.holdStartTime is not None:  # end holding
                    plane.holdStartTime = None
                plane.mode = PlaneMode.HEADING
                plane.targetHeading = int(text.split(" ")[2]) % 360
                plane.turnDir = "R"
                # plane.heading = int(text.split(" ")[2])
            case "sp":
                if plane.mode in PlaneMode.GROUND_MODES:
                    raise CommandErrorException("Ground speed is fixed")
                plane.targetSpeed = int(text.split(" ")[2])
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
            case "sq":
                plane.squawk = int(text.split(" ")[2])
            case "hold":
                if plane.mode in PlaneMode.GROUND_MODES:
                    raise CommandErrorException("Cannot enter hold while on the ground")
                plane.holdFix = text.split(" ")[2]
            case "star":
                if plane.mode in PlaneMode.GROUND_MODES:
                    raise CommandErrorException("Cannot assign STAR while on the ground")
                starData, extraFixes = loadStarAndFixData(text.split(" ")[3])
                FIXES.update(extraFixes)
                plane.flightPlan.route.fixes.extend(starData[text.split(" ")[2]][ACTIVE_RUNWAY].split(" "))
            case "ils":
                if plane.mode in PlaneMode.GROUND_MODES:
                    raise CommandErrorException("Cannot assign ILS approach while on the ground")
                if plane.mode == PlaneMode.FLIGHTPLAN:
                    raise CommandErrorException("Need headings to intercept")

                runwayData = loadRunwayData(ACTIVE_AERODROME)[text.split(" ")[2]]
                plane.clearedILS = runwayData
            case "ho":
                if text.split(" ")[2] == "KKT":  # TODO: choose airport
                    index = planes.index(plane)
                    planes.remove(plane)
                    planeSocks.pop(index).close()
                    window.aircraftTable.removeRow(index)
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
        window.errorLabel.setText(e.message)


# PLANE SPAWNING

def spawnEveryNSeconds(nSeconds, masterCallsign, controllerSock, method, *args, **kwargs):
    global planes, planeSocks, window

    timeWiggle = 0
    if method == "ARR":
        timeWiggle = random.randint(-10, 15)

    util.DaemonTimer(nSeconds + timeWiggle, spawnEveryNSeconds, args=(nSeconds, masterCallsign, controllerSock, method, *args), kwargs=kwargs).start()

    fp: FlightPlan = kwargs["flightPlan"]
    kwargs.pop("flightPlan")

    if method == "ARR":
        plane = Plane.requestFromFix(util.callsignGen(), *args, **kwargs, flightPlan=FlightPlan.duplicate(fp), squawk=util.squawkGen())
    elif method == "DEP":
        plane = Plane.requestDeparture(util.callsignGen(), *args, **kwargs, flightPlan=FlightPlan.duplicate(fp), squawk=util.squawkGen())
        plane.targetAltitude = 4000
        plane.targetSpeed = 250
        plane.vertSpeed = CLIMB_RATE
    elif method == "GPT":
        plane = Plane.requestFromGroundPoint(util.callsignGen(), *args, **kwargs, flightPlan=FlightPlan.duplicate(fp), squawk=util.squawkGen())
    elif method == "STD":
        plane = Plane.requestFromStand(util.callsignGen(), *args, **kwargs, flightPlan=FlightPlan.duplicate(fp), squawk=util.squawkGen())
    kwargs["flightPlan"] = fp
    planes.append(plane)
    sock = util.PlaneSocket.StartPlane(plane, masterCallsign, controllerSock)

    # if method == "ARR":
    #     util.DaemonTimer(11, sock.sendall, args=[b'$CQLON_S_CTR:@94835:SC:' + plane.callsign.encode("UTF-8") + b':' + fp.route.fixes[-1].encode("UTF-8") + b'\r\n'])

    planeSocks.append(sock)

    window.aircraftTable.setRowCount(sum([1 for plane in planes if plane.currentlyWithData is None]))

    dc = 0
    for plane in planes:
        if plane.currentlyWithData is None:
            window.aircraftTable.setItem(dc, 0, QTableWidgetItem(plane.callsign))
            window.aircraftTable.setItem(dc, 1, QTableWidgetItem(util.modeConverter(plane.mode)))
            window.aircraftTable.setItem(dc, 2, QTableWidgetItem(str(plane.squawk)))
            window.aircraftTable.setItem(dc, 3, QTableWidgetItem(str(plane.speed)))
            dc += 1

# MAIN LOOP


def positionLoop(controllerSock: util.ControllerSocket):
    global planes, planeSocks, window
    util.DaemonTimer(5, positionLoop, args=[controllerSock]).start()

    controllerSock.esSend("%" + MASTER_CONTROLLER, MASTER_CONTROLLER_FREQ, "3", "100", "7", "51.14806", "-0.19028", "0")

    dc = 0  # display counter
    for i, plane in enumerate(planes):
        planeSocks[i].sendall(plane.positionUpdateText())  # position update

        if plane.currentlyWithData is None:  # We only know who they are if they are with us
            print(plane.callsign, end=", ")
            window.aircraftTable.setItem(dc, 0, QTableWidgetItem(plane.callsign))
            window.aircraftTable.setItem(dc, 1, QTableWidgetItem(util.modeConverter(plane.mode)))
            window.aircraftTable.setItem(dc, 2, QTableWidgetItem(str(plane.squawk)))
            window.aircraftTable.setItem(dc, 3, QTableWidgetItem(str(plane.speed)))
            dc += 1

    print()


def messageMonitor(controllerSock: util.ControllerSocket) -> None:
    t = threading.Timer(5, messageMonitor, args=[controllerSock])
    t.daemon = True
    t.start()

    socketReady = select.select([controllerSock], [], [], 1)  # 1 second timeout
    if socketReady[0]:
        messages = controllerSock.recv(1024)
        messages = messages.decode("UTF-8").split("\r\n")
        messages.pop()
        for message in messages:
            if message.startswith("$HO"):
                callsign = message.split(":")[2]
                controllerSock.esSend("$CQ" + MASTER_CONTROLLER, "@94835", "HT", callsign, ACTIVE_CONTROLLER)
                for plane in planes:
                    if plane.callsign == callsign:
                        index = planes.index(plane)
                        plane.currentlyWithData = (MASTER_CONTROLLER, None)
                        window.aircraftTable.removeRow(index)
                        break
            elif message.startswith("$HA"):
                callsign = message.split(":")[2]
                for plane in planes:
                    if plane.callsign == callsign:
                        index = planes.index(plane)
                        plane.currentlyWithData = None
                        window.aircraftTable.setRowCount(sum([1 for plane in planes if plane.currentlyWithData is None]))
                        break
            else:
                pass
                # print(message)

        # print()


def cellClicked(row, _col):
    window.commandEntry.setText(window.aircraftTable.item(row, 0).text() + " ")
    window.commandEntry.setFocus()


def main():
    global planes, planeSocks, window, ACTIVE_AERODROME, ACTIVE_RUNWAY, ACTIVE_CONTROLLER
    # SETUP PLANES

    masterCallsign = MASTER_CONTROLLER

    # planes.append(Plane.requestFromStand("EZY45", "2", flightPlan=FlightPlan("I", "B738", 250, "EGSS", 1130, 1130, 37000, "EHAM", Route("CLN P44 RATLO M197 REDFA"))))
    # planes.append(Plane.requestFromStand("DLH20W", "23", flightPlan=FlightPlan("I", "B738", 250, "EGSS", 1130, 1130, 37000, "EHAM", Route("CLN P44 RATLO M197 REDFA"))))
    # planes.append(Plane.requestFromStand("BAW22E", "12", flightPlan=FlightPlan("I", "B738", 250, "EGSS", 1130, 1130, 37000, "EHAM", Route("CLN P44 RATLO M197 REDFA"))))
    # planes.append(Plane.requestFromStand("TRA90P", "14", flightPlan=FlightPlan("I", "B738", 250, "EGSS", 1130, 1130, 37000, "EHAM", Route("CLN P44 RATLO M197 REDFA"))))

    # planes.append(Plane.requestFromGroundPoint("GASNE", "L/L3", flightPlan=FlightPlan("I", "B738", 250, "EHAM", 1130, 1130, 36000, "EGSS", Route("CLN"))))
    # planes.append(Plane.requestFromStand("GETCC", "2", flightPlan=FlightPlan("I", "B738", 250, "EGSS", 1130, 1130, 36000, "EHAM", Route("CLN P44 RATLO M197 REDFA"))))
    # planes.append(Plane.requestFromGroundPoint("GBMIV", "V/V1", flightPlan=FlightPlan("I", "B738", 250, "EGSS", 1130, 1130, 36000, "EHAM", Route("CLN P44 RATLO M197 REDFA"))))

    controllerSock: util.ControllerSocket = util.ControllerSocket.StartController(masterCallsign)
    controllerSock.setblocking(False)

    for plane in planes:
        planeSocks.append(util.PlaneSocket.StartPlane(plane, masterCallsign, controllerSock))

    # SETUP UI

    app = QtWidgets.QApplication(sys.argv)

    window = MainWindow()

    # # GATTERS:
    # # ARRIVALS
    # # 10ph AMDUT1G
    # # 10ph VASUX1G
    # # 5ph SIRIC1G
    # # 10ph TELTU1G
    # # 5ph GWC1G
    # # 0ph KIDLI1G
    # util.DaemonTimer(random.randint(1, 60), spawnEveryNSeconds, args=(3600 // 10, masterCallsign, controllerSock, "ARR", "SFD"), kwargs={"speed": 250, "altitude": 9000, "flightPlan": FlightPlan.arrivalPlan("SFD DCT WILLO"), "currentlyWithData": (masterCallsign, "WILLO")}).start()
    # util.DaemonTimer(random.randint(60, 120), spawnEveryNSeconds, args=(3600 // 10, masterCallsign, controllerSock, "ARR", "TELTU"), kwargs={"speed": 250, "altitude": 9000, "flightPlan": FlightPlan.arrivalPlan("TELTU DCT HOLLY DCT WILLO"), "currentlyWithData": (masterCallsign, "WILLO")}).start()
    # util.DaemonTimer(random.randint(120, 180), spawnEveryNSeconds, args=(3600 // 5, masterCallsign, controllerSock, "ARR", "MID"), kwargs={"speed": 250, "altitude": 9000, "flightPlan": FlightPlan.arrivalPlan("MID DCT HOLLY DCT WILLO"), "currentlyWithData": (masterCallsign, "WILLO")}).start()
    # util.DaemonTimer(random.randint(180, 240), spawnEveryNSeconds, args=(3600 // 10, masterCallsign, controllerSock, "ARR", "TELTU"), kwargs={"speed": 250, "altitude": 9000, "flightPlan": FlightPlan.arrivalPlan("TELTU DCT SFD DCT TIMBA"), "currentlyWithData": (masterCallsign, "TIMBA")}).start()
    # util.DaemonTimer(random.randint(240, 300), spawnEveryNSeconds, args=(3600 // 5, masterCallsign, controllerSock, "ARR", "GWC"), kwargs={"speed": 250, "altitude": 9000, "flightPlan": FlightPlan.arrivalPlan("GWC DCT HOLLY DCT WILLO"), "currentlyWithData": (masterCallsign, "WILLO")}).start()

    # # DEPARTURES
    # util.DaemonTimer(1, spawnEveryNSeconds, args=(540, masterCallsign, controllerSock, "DEP", "EGKK"), kwargs={"flightPlan": FlightPlan("I", "B738", 250, "EGKK", 1130, 1130, 25000, "LFPG", Route("HARDY1X/26L HARDY M605 XIDIL UM605 BIBAX"))}).start()
    # util.DaemonTimer(90, spawnEveryNSeconds, args=(540, masterCallsign, controllerSock, "DEP", "EGKK"), kwargs={"flightPlan": FlightPlan("I", "B738", 250, "EGKK", 1130, 1130, 26000, "EGCC", Route("LAM6M/26L LAM N57 WELIN T420 ELVOS"))}).start()
    # util.DaemonTimer(180, spawnEveryNSeconds, args=(540, masterCallsign, controllerSock, "DEP", "EGKK"), kwargs={"flightPlan": FlightPlan("I", "B738", 250, "EGKK", 1130, 1130, 18000, "EGGD", Route("NOVMA1X/26L NOVMA L620 NIBDA N14 HEKXA Q63 SAWPE"))}).start()
    # util.DaemonTimer(270, spawnEveryNSeconds, args=(540, masterCallsign, controllerSock, "DEP", "EGKK"), kwargs={"flightPlan": FlightPlan("I", "B738", 250, "EGKK", 1130, 1130, 35000, "EDDF", Route("MIMFO1M/26L MIMFO Y312 DVR UL9 KONAN UL607 KOK SPI T180 UNOKO"))}).start()
    # util.DaemonTimer(360, spawnEveryNSeconds, args=(540, masterCallsign, controllerSock, "DEP", "EGKK"), kwargs={"flightPlan": FlightPlan("I", "B738", 250, "EGKK", 1130, 1130, 27000, "LFAB", Route("BOGNA1X/26L BOGNA L612 BENBO UL612 XAMAB"))}).start()
    # util.DaemonTimer(450, spawnEveryNSeconds, args=(540, masterCallsign, controllerSock, "DEP", "EGKK"), kwargs={"flightPlan": FlightPlan("I", "B738", 250, "EGKK", 1130, 1130, 27000, "EHAM", Route("FRANE1M/26L FRANE M604 GASBA M197 REDFA"))}).start()

    # HEATHROW:
    # ARRIVALS
    # 10ph BNN
    # 10ph LAM
    # 10ph OCK
    # 10ph BIG
    util.DaemonTimer(random.randint(1, 72), spawnEveryNSeconds, args=(3600 // 10, masterCallsign, controllerSock, "ARR", "WCO"), kwargs={"speed": 250, "altitude": 7000, "flightPlan": FlightPlan.arrivalPlan("WCO DCT BNN"), "currentlyWithData": (masterCallsign, "BNN")}).start()
    util.DaemonTimer(random.randint(72, 144), spawnEveryNSeconds, args=(3600 // 10, masterCallsign, controllerSock, "ARR", "DET"), kwargs={"speed": 250, "altitude": 7000, "flightPlan": FlightPlan.arrivalPlan("DET DCT LAM"), "currentlyWithData": (masterCallsign, "LAM")}).start()
    util.DaemonTimer(random.randint(144, 216), spawnEveryNSeconds, args=(3600 // 10, masterCallsign, controllerSock, "ARR", "HAZEL"), kwargs={"speed": 250, "altitude": 7000, "flightPlan": FlightPlan.arrivalPlan("HAZEL DCT OCK"), "currentlyWithData": (masterCallsign, "OCK")}).start()
    util.DaemonTimer(random.randint(216, 288), spawnEveryNSeconds, args=(3600 // 10, masterCallsign, controllerSock, "ARR", "MAY"), kwargs={"speed": 250, "altitude": 7000, "flightPlan": FlightPlan.arrivalPlan("MAY DCT BIG"), "currentlyWithData": (masterCallsign, "BIG")}).start()

    # DEPARTURES
    util.DaemonTimer(1, spawnEveryNSeconds, args=(240, masterCallsign, controllerSock, "DEP", ACTIVE_AERODROME), kwargs={"flightPlan": FlightPlan("I", "B738", 250, ACTIVE_AERODROME, 1130, 1130, 25000, "EHAM", Route("BPK7G/27L BPK Q295 BRAIN M197 REDFA"))}).start()
    util.DaemonTimer(60, spawnEveryNSeconds, args=(240, masterCallsign, controllerSock, "DEP", ACTIVE_AERODROME), kwargs={"flightPlan": FlightPlan("I", "B738", 250, ACTIVE_AERODROME, 1130, 1130, 25000, "EGGD", Route("CPT3G/27L CPT"))}).start()
    util.DaemonTimer(120, spawnEveryNSeconds, args=(240, masterCallsign, controllerSock, "DEP", ACTIVE_AERODROME), kwargs={"flightPlan": FlightPlan("I", "B738", 250, ACTIVE_AERODROME, 1130, 1130, 25000, "EGCC", Route("UMLAT1G/27L UMLAT T418 WELIN T420 ELVOS"))}).start()
    util.DaemonTimer(180, spawnEveryNSeconds, args=(240, masterCallsign, controllerSock, "DEP", ACTIVE_AERODROME), kwargs={"flightPlan": FlightPlan("I", "B738", 250, ACTIVE_AERODROME, 1130, 1130, 25000, "LFPG", Route("MAXIT1G/27L MAXIT Y803 MID UL612 BOGNA HARDY UM605 BIBAX"))}).start()

    # STANNERS

    # util.DaemonTimer(random.randint(1, 1), spawnEveryNSeconds, args=(180, masterCallsign, controllerSock, "GPT", "J(1)_Z"), kwargs={"flightPlan": FlightPlan("I", "B738", 250, "EHAM", 1130, 1130, 36000, "EGSS", Route("CLN"))}).start()

    # Start message monitor
    util.DaemonTimer(5, messageMonitor, args=[controllerSock]).start()

    window.aircraftTable.setRowCount(sum([1 for plane in planes if plane.currentlyWithData is None]))

    window.commandEntry.returnPressed.connect(parseCommand)
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
