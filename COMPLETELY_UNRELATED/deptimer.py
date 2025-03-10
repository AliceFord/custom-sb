import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import json
import datetime

# LIVE_ADS = False

# fromDate = "2024-02-01+00%3A00"
# toDate = "2024-02-14+23%3A59"

# if LIVE_ADS:
#     adList = requests.get(f"https://statsim.net/flights/country/?countrycode=GB&period=custom&from={fromDate}&to={toDate}&json=true").json()

#     ads = list(adList.keys())
# else:
#     ads = ['EGAA', 'EGBB', 'EGCC', 'EGGD', 'EGGP', 'EGGW', 'EGKK', 'EGLL', 'EGNX', 'EGPF', 'EGPH', 'EGSS']

# acData = []

# for ad in ads:
#     flightsData = requests.get(f"https://statsim.net/flights/airport/?icao={ad}&period=custom&from={fromDate}&to={toDate}&json=true").json()

#     actimes = []

#     for ac in flightsData["departed"]:
#         actimes.append(ac["departed"] - ac["logontime"])

#     actimeAvg = sum(actimes) / len(actimes)

#     print(f"{ad}: {actimeAvg}")


fromDate = "2025-01-26+11%3A00"
toDate = "2025-01-26+22%3A00"
ad = "EGPH"

flightsData = requests.get(f"https://statsim.net/flights/airport/?icao={ad}&period=custom&from={fromDate}&to={toDate}&json=true").json()
actimes = []

# print(flightsData)
# quit()

for ac in flightsData["departed"]:
    actimes.append(ac["departed"])

for ac in flightsData["arrived"]:
    actimes.append(ac["arrived"])

actimes.sort()
avgs = []
rm = 0
for actime in actimes:
    initTime = actime - 60 * 60
    # Go back 15 mins and look
    c = 0
    for item in actimes:
        if initTime <= item <= actime:
            c += 1
    avgs.append(c)

    if initTime < actimes[0]:
        rm += 1

actimes = actimes[rm:]
actimes = list(map(lambda x: datetime.datetime.fromtimestamp(x - 30 * 60), actimes))
avgs = avgs[rm:]

fig, ax = plt.subplots()

# hourLocator = mdates.HourLocator()
# ax.xaxis.set_major_locator(hourLocator)
hourFormatter = mdates.DateFormatter("%H:00")

ax.xaxis.set_major_formatter(hourFormatter)
ax.set_xlabel("Time")
ax.set_ylabel("Average runway movements / hour")

ax.plot(actimes, avgs)

ax.axvline(x=datetime.datetime(year=2025, month=1, day=26, hour=11, minute=48), color='purple', label="Ben on GMP")
ax.axvline(x=datetime.datetime(year=2025, month=1, day=26, hour=13, minute=41), color='pink', label="Lily on AIR")
ax.axvline(x=datetime.datetime(year=2025, month=1, day=26, hour=14, minute=30), color='red', label="Max+Ben+Alice on GMP")
ax.axvline(x=datetime.datetime(year=2025, month=1, day=26, hour=15, minute=25), color='green', label="Alice on AIR")
ax.axvline(x=datetime.datetime(year=2025, month=1, day=26, hour=17, minute=00), color='blue', label="All of us off")

ax.legend()

plt.show()