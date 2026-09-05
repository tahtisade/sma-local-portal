import json
import os
import time


FILE = "sma_data.json"


def save(data):

    data["timestamp"] = time.time()

DEBUG = False

if DEBUG:
    print("Saving to:", os.path.abspath(FILE))

    with open(FILE, "w") as f:

        json.dump(data, f, indent=2)



def load():

    print("Loading from:", os.path.abspath(FILE))

    if not os.path.exists(FILE):

        return {
            "inverters": {},
            "energy_meter": {},
            "summary": {}
        }


    with open(FILE) as f:

        text = f.read()

    return json.loads(text)
