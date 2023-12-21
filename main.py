import random
import select
import socket
import threading
import sys
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QTableWidgetItem

from uiTest import MainWindow
from sfparser import loadRunwayData, loadStarAndFixData, parseFixes
from Route import Route
from FlightPlan import FlightPlan
from Plane import Plane
from globals import *
import util


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
    s.sendall(plane.positionUpdateText(calculatePosition=False))
    s.sendall(b'$FP' + plane.callsign.encode("UTF-8") + str(plane.flightPlan).encode("UTF-8") + b'\r\n') #TODO
    
    masterSock.sendall(b'$CQ' + masterCallsign + b':SERVER:FP:' + plane.callsign.encode("UTF-8") + b'\r\n')
    masterSock.sendall(b'$CQ' + masterCallsign + b':@94835:WH:' + plane.callsign.encode("UTF-8") + b'\r\n')
    masterSock.sendall(b'$CQ' + masterCallsign + b':' + plane.callsign.encode("UTF-8") + b':CAPS\r\n')

    if plane.currentlyWithData is not None:
        util.DaemonTimer(1, masterSock.sendall, args=[b'$CQ' + plane.currentlyWithData[0].encode("UTF-8") + b':@94835:IT:' + plane.callsign.encode("UTF-8") + b'\r\n']).start()  # Controller takes plane
        util.DaemonTimer(1, masterSock.sendall, args=[b'$CQ' + plane.currentlyWithData[0].encode("UTF-8") + b':@94835:TA:' + plane.callsign.encode("UTF-8") + b':' + str(plane.altitude).encode("UTF-8") + b'\r\n']).start()  # Temp alt for arrivals
        # masterSock.sendall(b'$CQ' + plane.currentlyWithData[0].encode("UTF-8") + b':@94835:IT:' + plane.callsign.encode("UTF-8") + b'\r\n')
    
    util.DaemonTimer(6, masterSock.sendall, args=[b'$CQ' + masterCallsign + b':@94835:BC:' + plane.callsign.encode("UTF-8") + b':' + str(plane.squawk).encode("UTF-8") + b'\r\n']).start()  # Assign squawk

    return s

# COMMAND PARSING

class _MatchException(Exception): pass

def parseCommand():
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
                plane.flightPlan.route.fixes.extend(starData[text.split(" ")[2]][ACTIVE_RUNWAY].split(" "))
            case "ils":
                if plane.mode == "FPL":
                    errorText = "Need headings to intercept"
                    raise _MatchException()
                
                runwayData = loadRunwayData(ACTIVE_AERODROME)[text.split(" ")[2]]
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
        plane.vertSpeed = 2000
    kwargs["flightPlan"] = fp
    planes.append(plane)
    sock = startPlane(plane, masterCallsign, controllerSock)

    # if method == "ARR":
    #     util.DaemonTimer(11, sock.sendall, args=[b'$CQLON_S_CTR:@94835:SC:' + plane.callsign.encode("UTF-8") + b':' + fp.route.fixes[-1].encode("UTF-8") + b'\r\n'])

    planeSocks.append(sock)

    
    window.aircraftTable.setRowCount(sum([1 for plane in planes if plane.currentlyWithData is None]))

    dc = 0
    for i, plane in enumerate(planes):
        if plane.currentlyWithData is None:
            window.aircraftTable.setItem(dc, 0, QTableWidgetItem(plane.callsign))
            window.aircraftTable.setItem(dc, 1, QTableWidgetItem(str(plane.squawk)))
            window.aircraftTable.setItem(dc, 2, QTableWidgetItem(str(plane.altitude)))
            window.aircraftTable.setItem(dc, 3, QTableWidgetItem(str(int(round(plane.heading, 0)))))
            window.aircraftTable.setItem(dc, 4, QTableWidgetItem(str(plane.speed)))
            window.aircraftTable.setItem(dc, 5, QTableWidgetItem(str(plane.vertSpeed)))
            window.aircraftTable.setItem(dc, 6, QTableWidgetItem(str(plane.lat)))
            window.aircraftTable.setItem(dc, 7, QTableWidgetItem(str(plane.lon)))
            window.aircraftTable.setItem(dc, 8, QTableWidgetItem(plane.flightPlan.route.fixes[0]))
            dc += 1

# MAIN LOOP

def positionLoop(controllerSock):
    global planes, planeSocks, window
    util.DaemonTimer(5, positionLoop, args=[controllerSock]).start()

    controllerSock.sendall(b'%' + b'LON_S_CTR' + b':29430:3:100:7:51.14806:-0.19028:0\r\n')  # TODO: choose correct controller

    dc = 0  # display counter
    for i, plane in enumerate(planes):
        planeSocks[i].sendall(plane.positionUpdateText())  # position update

        if plane.currentlyWithData is None:  # We only know who they are if they are with us
            print(plane.callsign, end=", ")
            window.aircraftTable.setItem(dc, 0, QTableWidgetItem(plane.callsign))
            window.aircraftTable.setItem(dc, 1, QTableWidgetItem(str(plane.squawk)))
            window.aircraftTable.setItem(dc, 2, QTableWidgetItem(str(plane.altitude)))
            window.aircraftTable.setItem(dc, 3, QTableWidgetItem(str(int(round(plane.heading, 0)))))
            window.aircraftTable.setItem(dc, 4, QTableWidgetItem(str(plane.speed)))
            window.aircraftTable.setItem(dc, 5, QTableWidgetItem(str(plane.vertSpeed)))
            window.aircraftTable.setItem(dc, 6, QTableWidgetItem(str(plane.lat)))
            window.aircraftTable.setItem(dc, 7, QTableWidgetItem(str(plane.lon)))
            window.aircraftTable.setItem(dc, 8, QTableWidgetItem(plane.flightPlan.route.fixes[0]))
            dc += 1
        
    print()


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
                controllerSock.sendall(b'$CQLON_S_CTR:@94835:HT:' + callsign.encode("UTF-8") + b':' + ACTIVE_CONTROLLER.encode("UTF-8") + b'\r\n')
                for plane in planes:
                    if plane.callsign == callsign:
                        index = planes.index(plane)
                        plane.currentlyWithData = ("LON_S_CTR", None)
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

    masterCallsign = "LON_S_CTR"
    
    # planes.append(Plane.requestFromFix("GASNE", "BIG", speed=250, altitude=7000, flightPlan=FlightPlan("I", "B738", 250, "LFPG", 1130, 1130, 36000, "EGLL", Route("BIG DCT LAM"))))
    
    controllerSock: socket.socket = startController(masterCallsign)
    controllerSock.setblocking(False)

    for i, plane in enumerate(planes):
        planeSocks.append(startPlane(plane, masterCallsign, controllerSock))
    
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
    # util.DaemonTimer(random.randint(1, 60), spawnEveryNSeconds, args=(3600 // 10, masterCallsign, controllerSock, "FIX", "SFD"), kwargs={"speed": 250, "altitude": 7000, "flightPlan": FlightPlan("I", "B738", 250, "EDDF", 1130, 1130, 36000, "EGKK", Route("SFD DCT WILLO")), "currentlyWithData": (masterCallsign, "WILLO")}).start()
    # util.DaemonTimer(random.randint(60, 120), spawnEveryNSeconds, args=(3600 // 10, masterCallsign, controllerSock, "FIX", "TELTU"), kwargs={"speed": 250, "altitude": 8000, "flightPlan": FlightPlan("I", "B738", 250, "EDDF", 1130, 1130, 36000, "EGKK", Route("TELTU DCT HOLLY DCT WILLO")), "currentlyWithData": (masterCallsign, "HOLLY")}).start()
    # util.DaemonTimer(random.randint(120, 180), spawnEveryNSeconds, args=(3600 // 5, masterCallsign, controllerSock, "FIX", "MID"), kwargs={"speed": 250, "altitude": 7000, "flightPlan": FlightPlan("I", "B738", 250, "EDDF", 1130, 1130, 36000, "EGKK", Route("MID DCT HOLLY DCT WILLO")), "currentlyWithData": (masterCallsign, "HOLLY")}).start()
    # util.DaemonTimer(random.randint(180, 240), spawnEveryNSeconds, args=(3600 // 10, masterCallsign, controllerSock, "FIX", "TELTU"), kwargs={"speed": 250, "altitude": 9000, "flightPlan": FlightPlan("I", "B738", 250, "EDDF", 1130, 1130, 36000, "EGKK", Route("TELTU DCT SFD DCT TIMBA")), "currentlyWithData": (masterCallsign, "SFD")}).start()
    # util.DaemonTimer(random.randint(240, 300), spawnEveryNSeconds, args=(3600 // 5, masterCallsign, controllerSock, "FIX", "GWC"), kwargs={"speed": 250, "altitude": 7000, "flightPlan": FlightPlan("I", "B738", 250, "EDDF", 1130, 1130, 36000, "EGKK", Route("GWC DCT HOLLY DCT WILLO")), "currentlyWithData": (masterCallsign, "HOLLY")}).start()

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

    # Start message monitor
    util.DaemonTimer(5, messageMonitor, args=[controllerSock]).start()

    
    window.aircraftTable.setRowCount(sum([1 for plane in planes if plane.currentlyWithData is None]))
    # for i, plane in enumerate(planes):
    #     window.aircraftTable.setItem(i, 0, QTableWidgetItem(plane.callsign))
    #     window.aircraftTable.setItem(i, 1, QTableWidgetItem(str(plane.squawk)))
    #     window.aircraftTable.setItem(i, 2, QTableWidgetItem(str(plane.altitude)))
    #     window.aircraftTable.setItem(i, 3, QTableWidgetItem(str(int(round(plane.heading, 0)))))
    #     window.aircraftTable.setItem(i, 4, QTableWidgetItem(str(plane.speed)))
    #     window.aircraftTable.setItem(i, 5, QTableWidgetItem(str(plane.vertSpeed)))
    #     window.aircraftTable.setItem(i, 6, QTableWidgetItem(str(plane.lat)))
    #     window.aircraftTable.setItem(i, 7, QTableWidgetItem(str(plane.lon)))
    #     window.aircraftTable.setItem(i, 8, QTableWidgetItem(plane.flightPlan.route.fixes[0]))

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
