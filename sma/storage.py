import json
import os
import time


FILE = "sma_data.json"


def empty_state():
    return {
        "inverters": {},
        "energy_meter": {},
        "summary": {}
    }


def save(data):

    data["timestamp"] = time.time()

    DEBUG = False

    if DEBUG:
        print("Saving to:", os.path.abspath(FILE))

    tmp_file = FILE + ".tmp"

    with open(tmp_file, "w") as f:
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())

    os.replace(tmp_file, FILE)


def load():

    print("Loading from:", os.path.abspath(FILE))

    if not os.path.exists(FILE):
        return empty_state()

    try:
        with open(FILE) as f:
            return json.load(f)

    except (json.JSONDecodeError, OSError) as e:
        print(f"WARNING: Could not load {FILE}: {e}")
        return empty_state()
