import requests

LIVE_ADS = True

fromDate = "2024-02-09+00%3A00"
toDate = "2024-02-16+23%3A59"

if LIVE_ADS:
    adList = requests.get(f"https://statsim.net/flights/country/?countrycode=GB&period=custom&from={fromDate}&to={toDate}&json=true").json()

    ads = list(adList.keys()) + ["EIDW"]
else:
    ads = ['EGAA', 'EGAC', 'EGBB', 'EGBF', 'EGCC', 'EGCJ', 'EGEC', 'EGFF', 'EGGD', 'EGGP', 'EGGW', 'EGHF', 'EGHI', 'EGHQ', 'EGHU', 'EGKA', 'EGKK', 'EGLC', 'EGLF', 'EGLL', 'EGMC', 'EGNM', 'EGNT', 'EGNV', 'EGNX', 'EGPA', 'EGPC', 'EGPD', 'EGPE', 'EGPF', 'EGPG', 'EGPH', 'EGPK', 'EGPL', 'EGPN', 'EGSC', 'EGSH', 'EGSQ', 'EGSS', 'EGSX', 'EGTB', 'EGTE', 'EGTF', 'EGTK', 'EGTR', 'EGWU', 'EGYD', 'EGCN', 'EGFC', 'EGKB', 'EGMD', 'EGNH', 'EGNJ', 'EGPB', 'EGPI', 'EGSG', 'EGXW', 'EGYJ', 'EIDW']

acData = []

for ad in ads:
    print(f"ON: {ad}")
    flightsData = requests.get(f"https://statsim.net/flights/airport/?icao={ad}&period=custom&from={fromDate}&to={toDate}&json=true").json()

    for ac in flightsData["departed"]:
        acData.append([ac["callsign"], ac["aircraft"], ac["dep"], ac["arr"], ac["altitude"], ac["route"], ac["departed"]])

    for ac in flightsData["arrived"]:
        acData.append([ac["callsign"], ac["aircraft"], ac["dep"], ac["arr"], ac["altitude"], ac["route"], ac["arrived"]])

with open("flightdata/acData2.txt", "w") as f:
    for ac in acData:
        f.write(str(ac) + "\n")
