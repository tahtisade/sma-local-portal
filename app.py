from flask import Flask, jsonify, render_template
from flask import request
from sma.resol_service import ResolService
import requests
import threading
import time
import json
import os
from urllib.request import urlopen
from urllib.error import URLError

from sma.inverter_service import InverterService
from sma.energymeter import EnergyMeter
from sma.state import state
from sma.save_service import SaveService
from sma.history_service import HistoryService
from sma.spot_price_service import SpotPriceService
from sma.heater_control_service import HeaterControlService
from sma.discovery import load_devices
from sma.settings import load_settings

history = HistoryService()

settings = load_settings()
resol_config = settings.get("resol")
resol = None

if resol_config:
    resol = ResolService(
        url=resol_config["url"],
        header_index=resol_config.get("header_index", 1),
        field_index=resol_config.get("field_index", 11),
        poll_interval=resol_config.get("poll_interval", 10),
    )

spot_price = SpotPriceService(
    cache_file="spot_prices.json",
    fetch_hour=17,
    retry_interval=900,
)

heater_control = HeaterControlService(
    config_file="heater_control.json",
    default_mode="pv_price",
    default_spot_price_limit=10.0,
)

app = Flask(__name__)


# -------------------------
# Invertterit
# -------------------------

def start_inverters():

    devices = [
        device
        for device in load_devices()
        if device.type == "inverter"
    ]


    for device in devices:

        service = InverterService(
            device.id,
            device.ip
        )


        t = threading.Thread(
            target=service.run,
            daemon=True
        )

        t.start()



# -------------------------
# Energy Meter
# -------------------------

def start_energy_meter():

    meter = EnergyMeter()

    meter.start()



# -------------------------
# Web
# -------------------------

@app.route("/")
def index():

    heater_config = settings.get("heater", {})

    heater_title = heater_config.get(
        "title",
        "PV Surplus Load",
    )

    return render_template(
        "index.html",
        heater_title=heater_title,
        heater_temperature_limit=heater_config.get(
            "temperature_limit"
        ),
        heater_temperature_resume=heater_config.get(
            "temperature_resume"
        ),
        resol_enabled=resol is not None,
    )

@app.route("/api/status")
def status():
    data = state.get()
    data["resol"] = (
        resol.get_status()
        if resol
        else {"enabled": False}
    )
    data["spot_price"] = spot_price.get_status()
    data["heater_control"] = heater_control.get_status()

    return jsonify(data)

from flask import request

@app.route("/api/evcc")
def evcc_status():

    try:
        with urlopen(
            "http://127.0.0.1:7070/api/state",
            timeout=2
        ) as response:

            data = json.load(response)

        # EVCC:n ensimmäinen loadpoint
        loadpoint = data.get("loadpoints", [{}])[0]

        return jsonify({
            "connected": loadpoint.get("connected", False),
            "charging": loadpoint.get("charging", False),
            "enabled": loadpoint.get("enabled", False),
            "mode": loadpoint.get("mode", "unknown"),
            "charge_power": loadpoint.get("chargePower", 0),
            "charged_energy": loadpoint.get("chargedEnergy", 0),
            "solar_percentage": loadpoint.get("sessionSolarPercentage", 0),
            "title": loadpoint.get("title", "EVCC"),
            "vehicle": loadpoint.get("vehicleTitle", ""),
            "pv_power": data.get("pvPower", 0),
            "site_title": data.get("siteTitle", "")
        })

    except (URLError, TimeoutError, OSError) as e:

        return jsonify({
            "connected": False,
            "error": str(e)
        }), 503

@app.route("/api/evcc/mode", methods=["POST"])
def evcc_mode():

    data = request.get_json(silent=True) or {}
    mode = data.get("mode")

    allowed_modes = ["pv", "now", "off"]

    if mode not in allowed_modes:
        return jsonify({
            "error": "Invalid mode"
        }), 400

    try:

        response = requests.post(
            f"http://127.0.0.1:7070/api/loadpoints/1/mode/{mode}",
            timeout=5
        )

        if not response.ok:
            return jsonify({
                "error": "EVCC API error",
                "status": response.status_code
            }), 502

        return jsonify({
            "mode": mode
        })

    except requests.RequestException as error:

        return jsonify({
            "error": str(error)
        }), 502

@app.route("/api/heater/control",methods=["GET", "POST"])
def heater_control_api():

    if request.method == "GET":
        return jsonify(
            heater_control.get_status()
        )

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    try:
        result = heater_control.update(
            mode=data.get("mode"),
            spot_price_limit=data.get(
                "spot_price_limit"
            ),
            max_power=data.get(
                "max_power"
            ),
        )

        return jsonify(
            result
        )

    except (
        ValueError,
        TypeError
    ) as exc:

        return jsonify({
            "error": str(exc)
        }), 400


@app.route("/api/heater/status",methods=["POST"])
def heater_status_api():

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    power = data.get(
        "power"
    )

    reason = data.get(
        "reason"
    )

    if (
        power is None
        or reason is None
    ):
        return jsonify({
            "error": "power and reason required"
        }), 400

    try:
        result = (
            heater_control.update_controller_status(
                power,
                reason,
            )
        )

        return jsonify(
            result
        )

    except (
        ValueError,
        TypeError
    ) as exc:

        return jsonify({
            "error": str(exc)
        }), 400


@app.route("/api/history")
def history_api():

    range_name = request.args.get(
        "range",
        default="15m"
    )

    limits = {
        "15m": 180,
        "30m": 360,
        "1h": 720,
        "2h": 1440,
        "3h": 2160,
        "6h": 4320,
        "12h": 8640,
        "24h": 17280,
        "48h": 34560,
        "7d": 120960,
    }

    limit = limits.get(range_name, 180)

    return jsonify(
        history.get_history(limit)
    )

@app.route("/api/energy_stats")
def energy_stats():

    return jsonify(
        history.get_today_energy()
    )

# -------------------------
# Start
# -------------------------

if __name__ == "__main__":


    print("Starting SMA Local Portal")

    if resol:
        resol.start()

    spot_price.start()

    threading.Thread(

        target=start_inverters,

        daemon=True

    ).start()



    threading.Thread(

        target=start_energy_meter,

        daemon=True

    ).start()

    threading.Thread(
        target=SaveService().run,
        daemon=True

    ).start()

    threading.Thread(
        target=history.start,
        daemon=True
    ).start()


    time.sleep(2)


    app.run(

        host="0.0.0.0",

        port=int(os.environ.get("SMA_PORT", "8080"))

    )
