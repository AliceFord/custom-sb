import requests

LIVE_ADS = False

fromDate = "2024-02-01+00%3A00"
toDate = "2024-02-14+23%3A59"

if LIVE_ADS:
    adList = requests.get(f"https://statsim.net/flights/country/?countrycode=GB&period=custom&from={fromDate}&to={toDate}&json=true").json()

    ads = list(adList.keys())
else:
    ads = ['EGAA', 'EGBB', 'EGCC', 'EGGD', 'EGGP', 'EGGW', 'EGKK', 'EGLL', 'EGNX', 'EGPF', 'EGPH', 'EGSS']

acData = []

for ad in ads:
    flightsData = requests.get(f"https://statsim.net/flights/airport/?icao={ad}&period=custom&from={fromDate}&to={toDate}&json=true").json()

    actimes = []

    for ac in flightsData["departed"]:
        actimes.append(ac["departed"] - ac["logontime"])

    actimeAvg = sum(actimes) / len(actimes)

    print(f"{ad}: {actimeAvg}")
