import json

def loadProfile(profile):
    with open(f"profiles/{profile}.json") as f:
        data = json.load(f)

    