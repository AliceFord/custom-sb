import math
import os
import json
import re


def sfCoordsToNormalCoords(lat: str, lon: str):
    outLat = 0
    outLon = 0

    latSections = lat.split(".")
    outLat = float(latSections[0][1:])
    outLat += float(latSections[1]) / 60
    outLat += float(latSections[2]) / 3600
    outLat += float(latSections[3]) / 3600000
    if latSections[0][0] == "S": outLat *= -1

    lonSections = lon.split(".")
    outLon = float(lonSections[0][1:])
    outLon += float(lonSections[1]) / 60
    outLon += float(lonSections[2]) / 3600
    outLon += float(lonSections[3]) / 3600000
    if lonSections[0][0] == "W": outLon *= -1

    return (round(outLat, 5), round(outLon, 5))

    

def parseFixes(path=None):
    if path is None:
        fixesPath = r"data\Navaids\FIXES_UK.txt"

        with open(fixesPath, "r") as f:
            lines = f.read().split("\n")

        ciczPath = r"data\Navaids\FIXES_CICZ.txt"

        with open(ciczPath, "r") as f:
            ciczPath = f.read().split("\n")
            for line in ciczPath:
                try:
                    lines.append(line)
                except IndexError:
                    pass

        vorPath = r"data\Navaids\VOR_UK.txt"

        with open(vorPath, "r") as f:
            vorLines = f.read().split("\n")
            for line in vorLines:
                try:
                    lines.append(" ".join([line.split(" ")[0], line.split(" ")[2], line.split(" ")[3]]))
                except IndexError:
                    pass

        ndbPath = r"data\Navaids\NDB_All.txt"

        with open(ndbPath, "r") as f:
            ndbPath = f.read().split("\n")
            for line in ndbPath:
                if line.startswith(";") or line == "":
                    continue

                line = line.replace("  ", " ")
                try:
                    lines.append(" ".join([line.split(" ")[0], line.split(" ")[2], line.split(" ")[3]]))
                except IndexError:
                    pass
    else:
        with open(path, "r") as f:
            lines = f.read().split("\n")

    fixes = {}
    for line in lines:
        line = line.strip()
        if line.startswith(";") or line == "":
            continue
        line = line.split(" ")
        fixes[line[0]] = sfCoordsToNormalCoords(line[1], line[2])

    return fixes


def parseADs():
    # get all foklders in Airports

    ads = {}

    for ad in os.listdir(r"data\Airports"):
        adPath = rf"data\Airports\{ad}\Basic.txt"

        with open(adPath, "r") as f:
            lines = f.read().split("\n")
            coordLine = lines[1].split(" ")

            ads[ad] = sfCoordsToNormalCoords(coordLine[0], coordLine[1])

    return ads


def parseATS():
    with open("data/ATS Routes/ats.json") as f:
        raw = f.read().replace("'", '"')
        data = json.loads(raw)

    outData = {}

    for route, routeData in data.items():
        outData[route] = []
        for wpt in routeData["waypoints"]:
            outData[route].append(wpt["name"])

    return outData



def loadStarAndFixData(icao) -> tuple[dict[str, dict[str, str]], list[str]]:
    with open(rf"data\Airports\{icao}\Stars.txt", "r") as f:
        lines = f.read().split("\n")

    starData = {}
    for line in lines:
        if line.startswith("STAR"):
            currentStarData = line.split(":")
            runway = currentStarData[2]
            starName = currentStarData[3]
            try:
                starData[starName][runway] = currentStarData[4]
            except KeyError:
                starData[starName] = {runway: currentStarData[4]}

    fixes = parseFixes(rf"data\Airports\{icao}\Fixes.txt")

    return starData, fixes

def loadSidAndFixData(icao) -> tuple[dict[str, dict[str, str]], list[str]]:
    with open(rf"data\Airports\{icao}\Sids.txt", "r") as f:
        lines = f.read().split("\n")

    starData = {}
    for line in lines:
        if line.startswith("SID"):
            currentStarData = line.split(":")
            runway = currentStarData[2]
            starName = currentStarData[3]
            try:
                starData[starName][runway] = currentStarData[4]
            except KeyError:
                starData[starName] = {runway: currentStarData[4]}

    fixes = parseFixes(rf"data\Airports\{icao}\Fixes.txt")

    return starData, fixes


def loadRunwayData(icao) -> dict[str, list[str, tuple[float, float]]]:
    with open(rf"data\Airports\{icao}\Runway.txt", "r") as f:
        lines = f.read().split("\n")

    runwayData = {}

    for line in lines:
        if line == "":
            continue
        runwayAIdentifier = line[:3].strip()
        runwayBIdentifier = line[4:7].strip()
        runwayAHeading = int(line[8:11])
        runwayBHeading = int(line[12:15])
        runwayALat = line[16:30]
        runwayALon = line[31:45]
        runwayBLat = line[46:60]
        runwayBLon = line[61:75]
        runwayACoords = sfCoordsToNormalCoords(runwayALat, runwayALon)
        runwayBCoords = sfCoordsToNormalCoords(runwayBLat, runwayBLon)

        runwayData[runwayAIdentifier] = [runwayAHeading, runwayACoords]
        runwayData[runwayBIdentifier] = [runwayBHeading, runwayBCoords]

    return runwayData


SECTOR_NAME_MAP = {
    "AC West": "LON_W_CTR",
    "Clacton": "LON_E_CTR",
    "Daventry": "LON_M_CTR",
    "Dover": "LON_D_CTR",
    "Lakes": "LON_NW_CTR",
    "North Sea": "LON_NE_CTR",
    "Worthing": "LON_S_CTR",

    "East": "LTC_E_CTR",
    "Midlands": "LTC_M_CTR",
    "North East": "LTC_NE_CTR",
    "North West": "LTC_NW_CTR",
    "South East": "LTC_SE_CTR",
    "South West": "LTC_SW_CTR",

    "PC NE": "MAN_NE_CTR",
    "PC SE": "MAN_SE_CTR",
    "PC W": "MAN_W_CTR",

    "Deancross": "SCO_D_CTR",
    "North": "SCO_N_CTR",
    "Rathlin": "SCO_R_CTR",
    "South": "SCO_S_CTR",
    "West": "SCO_W_CTR",

    "Antrim": "STC_A_CTR",
    "Galloway": "STC_W_CTR",
    "Talla": "STC_E_CTR"
}

IGNORE_SECTORS = ["Berry Head", "Brecon", "LUS", "Sector 23", "Maastricht UAC Delta", "Maastricht UAC Jever", "East"]


def loadSectorData():
    folders = ["LON", "LTC", "MPC", "SCO", "STC"]

    sectorData = {}

    for folder in folders:
        files = os.listdir(f"data/Static/{folder}")
        for file in files:
            if file.replace(".txt", "") in IGNORE_SECTORS:
                continue
            currentSectorData = []
            with open(f"data/Static/{folder}/{file}", "r") as f:
                data = f.read().split("\n")

                prevCoords = None

                for i, line in enumerate(data):
                    if i == 0:
                        continue
                        
                    coordData = re.match(r"^[ \t]*(N.*? [EW].*?) (N.*? [EW]\d{3}\.\d{2}\.\d{2}\.\d{3})", line)
                    if coordData is not None:
                        if prevCoords != coordData.group(1) and prevCoords is not None:  # smaller sector
                            currentSectorData.append(sfCoordsToNormalCoords(*prevCoords.split(" ")))
                            break
                        currentSectorData.append(sfCoordsToNormalCoords(*coordData.group(1).split(" ")))
                        prevCoords = coordData.group(2)
            
            sectorData[SECTOR_NAME_MAP[file.replace(".txt", "")]] = currentSectorData
    
    return sectorData


if __name__ == "__main__":
    print(parseFixes())
