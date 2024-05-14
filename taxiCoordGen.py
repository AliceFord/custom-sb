import sfparser
import util


def getAllGroundCoords() -> dict[str, tuple[float, float]]:
    with open("SSGroundData.txt", "r") as f:
        lines = f.read().split("\n")

    points: dict[str, list] = {}
    for line in lines:
        if line[0] == ";":
            continue
        line = line.split(":")
        points[line[0]] = sfparser.sfCoordsToNormalCoords(line[1], line[2])

    return points


def getTaxiRoute(start: str, rawRoute: str, end: str):
    with open("SSGroundLayout.txt", "r") as f:
        lines = f.read().split("\n")

    taxiways: dict[str, list] = {}
    for line in lines:
        line = line.split(":")
        taxiways[line[0]] = line[1:]

    route: list[str] = rawRoute.split(" ")
    outRoute = []
    currentPos: str = start

    if start.replace("(1)", "").replace("(2)", "") == end.replace("(1)", "").replace("(2)", ""):
        return [getAllGroundCoords()[start]]

    for i in range(len(route)):
        twy = route[i]
        if i != len(route) - 1:
            currentEnd = route[i + 1]
        currentData = taxiways[twy]

        try:
            currentPosInData = currentData.index(currentPos)
        except ValueError:
            currentPosInData = currentData.index(currentPos.replace("_", "(1)_"))

        if i == len(route) - 1:
            try:
                currentEndInData = currentData.index(end)
            except ValueError:
                currentEndInData = currentData.index(end.replace("_", "(1)_"))
        else:
            try:
                currentEndInData = currentData.index(twy + "_" + currentEnd)
            except ValueError:
                currentEndInData = currentData.index(twy + "(1)_" + currentEnd)

        if currentPosInData < currentEndInData:
            outRoute.append(currentData[currentPosInData:currentEndInData + 1])
        else:
            outRoute.append(currentData[currentEndInData:currentPosInData + 1][::-1])

        if i != len(route) - 1:
            currentPos = currentEnd + "_" + twy

    # Cut out extra points (lazy!)
    for route in outRoute:
        try:
            # start
            if "(1)" in route[0]:
                a, b = route[0].split("(1)_")
                if route[1] == f"{a}(2)_{b}":
                    route.pop(0)
            elif "(2)" in route[0]:
                a, b = route[0].split("(2)_")
                if route[1] == f"{a}(1)_{b}":
                    route.pop(0)
        except IndexError:
            pass

        try:
            # end
            if "(1)" in route[-1]:
                a, b = route[-1].split("(1)_")
                if route[-2] == f"{a}(2)_{b}":
                    route.pop(-1)
            elif "(2)" in route[-1]:
                a, b = route[-1].split("(2)_")
                if route[-2] == f"{a}(1)_{b}":
                    route.pop(-1)
        except IndexError:
            pass

    # flatten
    data = getAllGroundCoords()
    outRoute = [data[item] for sublist in outRoute for item in sublist]

    return outRoute


def closestPoint(lat, lon):
    data = getAllGroundCoords()
    closest = None
    minDist = 10000

    for point, coords in data.items():
        dist = util.haversine(lat, lon, coords[0], coords[1])
        if dist < minDist:
            minDist = dist
            closest = point

    return closest


def standDataParser():
    with open("SSStandData.txt", "r") as f:
        lines = f.read().split("\n")

    out = {}
    for line in lines:
        if line == "" or line[0] == ";":
            continue
        line = line.split(":")
        out[line[0]] = (line[1], [sfparser.sfCoordsToNormalCoords(*coord.split("#")) for coord in line[2:]])

    return out


def getStandRoute(start, route, stand):
    standData = standDataParser()[stand]
    print(standData[0])
    route = getTaxiRoute(start, route, standData[0])
    route.append(standData[1][1])
    route.append(standData[1][0])

    return route


def getPushRoute(stand):
    standData = standDataParser()[stand]
    route = standData[1]

    return route


def nameOfPoint(point):
    data = getAllGroundCoords()
    for name, coords in data.items():
        if coords == point:
            return name

    return None


if __name__ == "__main__":
    # print(standDataParser())
    print(getTaxiRoute("Z_J", "Z J P H", "H(1)_B"))
