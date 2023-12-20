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
        threading.Timer(1, masterSock.sendall, args=[b'$CQ' + plane.currentlyWithData[0].encode("UTF-8") + b':@94835:IT:' + plane.callsign.encode("UTF-8") + b'\r\n']).start()  # Controller takes plane
        threading.Timer(1, masterSock.sendall, args=[b'$CQ' + plane.currentlyWithData[0].encode("UTF-8") + b':@94835:TA:' + plane.callsign.encode("UTF-8") + b':' + str(plane.altitude).encode("UTF-8") + b'\r\n']).start()  # Temp alt
        # masterSock.sendall(b'$CQ' + plane.currentlyWithData[0].encode("UTF-8") + b':@94835:IT:' + plane.callsign.encode("UTF-8") + b'\r\n')
    
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
        plane = Plane.requestFromFix(util.callsignGen(), *args, **kwargs, flightPlan=FlightPlan.duplicate(fp), squawk=util.squawkGen())
    elif method == "DEP":
        plane = Plane.requestDeparture(util.callsignGen(), *args, **kwargs, flightPlan=FlightPlan.duplicate(fp), squawk=util.squawkGen())
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
    
    # planes.append(Plane.requestDeparture("GASNE", "EGKK", flightPlan=FlightPlan("I", "B738", 250, "EGKK", 1130, 1130, 36000, "LFPG", Route("HARDY1X/26L HARDY M605 XIDIL UM605 BIBAX"))))
    
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
    threading.Timer(random.randint(1, 1), spawnEveryNSeconds, args=(3600 // 10, masterCallsign, controllerSock, "FIX", "SFD"), kwargs={"speed": 250, "altitude": 7000, "flightPlan": FlightPlan("I", "B738", 250, "EDDF", 1130, 1130, 36000, "EGKK", Route("SFD DCT WILLO")), "currentlyWithData": (masterCallsign, "WILLO")}).start()
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
