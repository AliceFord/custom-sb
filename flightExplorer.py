import json
import time
import requests
from bs4 import BeautifulSoup
import re

from FlightPlan import FlightPlan
from Plane import Plane
from PlaneMode import PlaneMode
from Route import Route
from globalVars import planes, planeSocks
from Constants import ACTIVE_CONTROLLERS, ACTIVE_RUNWAYS, MASTER_CONTROLLER, MASTER_CONTROLLER_FREQ, RADAR_UPDATE_RATE
import util

def positionLoop(controllerSock: util.ControllerSocket):
    global planes

    controllerSock.esSend("%" + MASTER_CONTROLLER, MASTER_CONTROLLER_FREQ, "3", "100", "7", "51.14806", "-0.19028", "0")

    for i, plane in enumerate(planes):  # update plane pos
        try:
            planeSocks[i].sendall(plane.positionUpdateText(False))  # position update
        except OSError:
            pass  # probably means we've just killed them. If not then lol
        except IndexError:
            pass  # probably means we've just killed them. If not then lol

    print()

def trd(l, i, c, e, d):  # try read default
    try:
        return c(l[i])
    except KeyError:
        return d
    except e:
        return d

def getData(fromCache=False, n=1):
    if n > 6:
        n = 6

    if fromCache:
        with open(f"rwcache/{n}.json") as f:
            data = json.load(f)
    else:
        data = json.loads(requests.get("https://api.adsb.lol/v2/lat/51.0/lon/-0.16/dist/35").text)  # 75

    outData = []
    for ac in data["ac"]:
        if ac["type"] != "adsb_icao":
            print(ac["type"])
            continue  # we don't know what you are!

        try:
            cs = ac["flight"].split(" ")[0]
        except KeyError:
            cs = ac["r"].replace("-", "")
        
        actype = trd(ac, "t", str, KeyError, "A20N")
        alt = trd(ac, "alt_baro", int, ValueError, 0)

        tas = trd(ac, "tas", float, ValueError, 0)
        heading = trd(ac, "mag_heading", int, ValueError, 0)
        altRate = trd(ac, "baro_rate", int, ValueError, 0)
        sq = trd(ac, "squawk", str, KeyError, "1234")
        try:
            lat = float(ac["lat"])
            lon = float(ac["lon"])
        except KeyError:
            continue  # no lat or lon data = no bueno

        mcpAltitude = trd(ac, "nav_altitude_mcp", int, ValueError, None)
        mcpHeading = trd(ac, "nav_heading", float, ValueError, None)
        if mcpHeading is not None: mcpHeading = round(mcpHeading / 5) * 5

        if float(ac["dst"] > 40):
            continue

        outData.append({"cs": cs, "type": actype, "altitude": alt, "tas": tas, "heading": heading, "altRate": altRate, "squawk": sq, "lat": lat, "lon": lon, "mcpHeading": mcpHeading, "mcpAltitude": mcpAltitude})

    return outData

def getFlightplan(plane: Plane):
    return -1
    with open("rwcache/flightplans.json") as f:
        data = json.load(f)

    if plane.callsign in list(data.keys()):
        flightplan = data[plane.callsign]
    else:
        cookies = {"_identity": '154067d597b2a6eb46d1709ff1e930c5415d11c69078354db6ea7675235378eda:2:{i:0;s:9:"_identity";i:1;s:50:"[76338,"kjwa9i1n8JBtZhINeEuRR7VdrRrye0gH",2592000]";}', "PHPSESSID": "7071umcdcgn2ltqm6as4ieblte"}

        try:
            html = requests.get(f"https://edi-gla.co.uk/flightplan/search?Flightplan%5Bcallsign%5D={plane.callsign}&Flightplan%5Baircraft_icao%5D=&Flightplan%5Bdep%5D=&Flightplan%5Bdest%5D=&Flightplan%5Bsearch_flight_time%5D=&Flightplan%5Bsearch_contributor_username%5D=&Flightplan%5Bremarks%5D=&Flightplan%5Bsearch_date_from%5D=&Flightplan%5Bsearch_date_to%5D=&Flightplan%5Bairac_cycle_validated%5D=&Flightplan%5Bsearch_sort_field%5D=callsign&Flightplan%5Bsearch_sort_order%5D=4", cookies=cookies).text
            parsed = BeautifulSoup(html, features="html.parser")
            id = parsed.body.find('div', attrs={'id':'w0'}).find('tbody').find('tr')['data-key']

            html2 = requests.get(f"https://edi-gla.co.uk/flightplan/{id}?operation=view-source", cookies=cookies).text
            parsed2 = BeautifulSoup(html2, features="html.parser")
            print(id)

            html2 = html2.replace("\n", " ").replace("\r", " ")  # cos pain

            departing = re.findall(r"<label>Departure</label> *([A-Z]{4})", html2)[0]
            arriving = re.findall(r"<label>Destination</label> *([A-Z]{4})", html2)[0]
            route = re.findall(r"<label>Route</label> *(.*?)<", html2)[0]
            # fpl = parsed2.body.find('div', attrs={'class': 'fpl-source'}).find_all('p')[1].text
            # fplLines = fpl.split("\r\n")
            # departing = fplLines[2][1:5]
            # route = fplLines[3][1:]
            # while fplLines[4][0] != "-":
            #     route += " " + fplLines[4]
            #     fplLines.pop(4)
            # arriving = fplLines[4][1:5]
        except:  # eek
            return -1

        flightplan = {"departing": departing, "route": route, "arriving": arriving}

        with open("rwcache/flightplans.json", "w") as f:
            data[plane.callsign] = flightplan
            json.dump(data, f)

    plane.flightPlan = FlightPlan(plane.flightPlan.flightRules, plane.flightPlan.aircraftType, plane.flightPlan.enrouteSpeed, flightplan["departing"], plane.flightPlan.offBlockTime, plane.flightPlan.enrouteSpeed, plane.flightPlan.cruiseAltitude, flightplan["arriving"], Route(flightplan["route"], flightplan["departing"], flightplan["arriving"]))
        
    return 0

def getStartEnd(plane: Plane):
    data = json.loads(requests.get(f"https://api.adsbdb.com/v0/callsign/{plane.callsign}").text)["response"]
    try:
        plane.flightPlan = FlightPlan(plane.flightPlan.flightRules, plane.flightPlan.aircraftType, plane.flightPlan.enrouteSpeed, data["flightroute"]["origin"]["icao_code"], plane.flightPlan.offBlockTime, plane.flightPlan.enrouteSpeed, plane.flightPlan.cruiseAltitude, data["flightroute"]["destination"]["icao_code"], Route("SPI", data["flightroute"]["origin"]["icao_code"], data["flightroute"]["destination"]["icao_code"]))
    except KeyError:
        print("NO IDEA FOR:", plane.callsign)
    except TypeError:
        print("NO IDEA FOR:", plane.callsign)
    
    return plane

def main():
    global planes, planeSocks, ACTIVE_RUNWAYS, ACTIVE_CONTROLLERS
    # SETUP PLANES

    masterCallsign = MASTER_CONTROLLER

    controllerSock: util.ControllerSocket = util.ControllerSocket.StartController(masterCallsign)
    controllerSock.setblocking(False)

    n = 1
    while True:  # block forver
        # load planes

        data = getData(fromCache=False, n=n)
        print("UPDATED!")
        n += 1
        for planeData in data:
            cs = planeData["cs"]
            if cs not in list(map(lambda plen: plen.callsign, planes)):  # callsign not in current planes
                plane = Plane(cs, planeData["squawk"], planeData["altitude"], planeData["heading"], planeData["tas"], planeData["lat"], planeData["lon"], planeData["altRate"], PlaneMode.HEADING, FlightPlan.arrivalPlan("IDEK", "IDEEEEEEEK", planeData["type"]), None)

                status = getFlightplan(plane)
                print(status, plane.callsign)
                if status == -1:
                    plane = getStartEnd(plane)

                planes.append(plane)
                sock = util.PlaneSocket.StartPlane(plane, masterCallsign, controllerSock)

                planeSocks.append(sock)
            else:  # we gotta find the plane!
                i = list(map(lambda plen: plen.callsign, planes)).index(cs)
                planes[i] = Plane(cs, planeData["squawk"], planeData["altitude"], planeData["heading"], planeData["tas"], planeData["lat"], planeData["lon"], planeData["altRate"], PlaneMode.HEADING, FlightPlan.arrivalPlan("IDEK", "IDEEEEEEEK", planeData["type"]), None)

                sock = planeSocks[i]

            if planeData["mcpAltitude"] is not None:
                sock.esSend(f"$CQ{MASTER_CONTROLLER}:@94835:TA:{cs}:{planeData["mcpAltitude"]}")
            if planeData["mcpHeading"] is not None:
                sock.esSend(f"$CQ{MASTER_CONTROLLER}:@94835:SC:{cs}:H{planeData["mcpHeading"]}")

        positionLoop(controllerSock)
        time.sleep(RADAR_UPDATE_RATE)


if __name__ == "__main__":
    # plane = Plane.requestDeparture("DAL1", "EGKK")
    # print(getFlightplan(plane))
    # print(plane.flightPlan.route)
    # print(plane.flightPlan.departure)
    # quit()
    main()
