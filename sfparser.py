import math


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
        fixesPath = r"C:\Users\olive\OneDrive\Documents\GitHub\uksf2\Navaids\FIXES_UK.txt"

        with open(fixesPath, "r") as f:
            lines = f.read().split("\n")

        vorPath = r"C:\Users\olive\OneDrive\Documents\GitHub\uksf2\Navaids\VOR_UK.txt"

        with open(vorPath, "r") as f:
            vorLines = f.read().split("\n")
            for line in vorLines:
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


def loadStarAndFixData(icao) -> (dict[str, dict[str, str]], list[str]):
    with open(rf"C:\Users\olive\OneDrive\Documents\GitHub\uksf2\Airports\{icao}\Stars.txt", "r") as f:
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

    fixes = parseFixes(rf"C:\Users\olive\OneDrive\Documents\GitHub\uksf2\Airports\{icao}\Fixes.txt")

    return starData, fixes

def loadRunwayData(icao) -> dict[str, list[str, tuple[float, float]]]:
    with open(rf"C:\Users\olive\OneDrive\Documents\GitHub\uksf2\Airports\{icao}\Runway.txt", "r") as f:
        lines = f.read().split("\n")

    runwayData = {}

    for line in lines:
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
    

if __name__ == "__main__":
    print(loadRunwayData("EGKK"))
