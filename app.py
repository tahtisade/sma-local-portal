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
from sma.elli_control_service import ElliControlService
from sma.charge_meter_service import ChargeMeterService
from sma.discovery import load_devices
from sma.settings import load_settings
from sma.ouman_eh203 import OumanEH203Service

history = HistoryService()

settings = load_settings()
charge_meter_config = settings.get("charge_meter", {})
charge_meter = None

if charge_meter_config.get("enabled", False):
    charge_meter = ChargeMeterService(
        port=charge_meter_config.get(
            "port",
            "/dev/ttyUSB0"
        ),
        device_id=charge_meter_config.get(
            "device_id",
            1
        ),
        baudrate=charge_meter_config.get(
            "baudrate",
            9600
        ),
        bytesize=charge_meter_config.get(
            "bytesize",
            8
        ),
        parity=charge_meter_config.get(
            "parity",
            "E"
        ),
        stopbits=charge_meter_config.get(
            "stopbits",
            1
        ),
        timeout=charge_meter_config.get(
            "timeout",
            2
        ),
    )
resol_config = settings.get("resol", {})
resol = None

if resol_config and resol_config.get("enabled", True):
    resol = ResolService(
        url=resol_config["url"],
        header_index=resol_config.get("header_index", 1),
        field_index=resol_config.get("field_index", 11),
        poll_interval=resol_config.get("poll_interval", 10),
    )

ouman_eh203_config = settings.get("ouman_eh203", {})
ouman_eh203 = None

if ouman_eh203_config.get("enabled", False):
    ouman_eh203 = OumanEH203Service(
        port=ouman_eh203_config["port"],
        poll_interval=ouman_eh203_config.get("poll_interval", 60),
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
elli_control = ElliControlService(
    config_file="elli_control.json",
    default_mode="off",
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

    if ouman_eh203:
        data["ouman_eh203"] = ouman_eh203.get_status()

    return jsonify(data)

from flask import request

# -------------------------
# EVCC helpers
# -------------------------

def get_evcc_mode():

    with urlopen(
        "http://127.0.0.1:7070/api/state",
        timeout=2
    ) as response:

        data = json.load(response)

    loadpoints = data.get(
        "loadpoints",
        []
    )

    if not loadpoints:
        raise RuntimeError(
            "EVCC loadpoint not found"
        )

    return loadpoints[0].get(
        "mode",
        "unknown"
    )


def set_evcc_mode(mode):

    if mode not in {
        "pv",
        "now",
        "off",
    }:
        raise ValueError(
            "Invalid EVCC mode"
        )

    response = requests.post(
        f"http://127.0.0.1:7070/"
        f"api/loadpoints/1/mode/{mode}",
        timeout=5
    )

    response.raise_for_status()


def run_elli_controller_once():

    try:
        control = elli_control.get_status()
        control_mode = control["mode"]

        if control_mode == "price":

            spot_status = (
                spot_price.get_status()
            )

            decision = (
                elli_control.get_price_decision(
                    spot_status.get("current")
                )
            )

            desired_evcc_mode = (
                decision["evcc_mode"]
            )

            reason = (
                decision["reason"]
            )

        elif control_mode in {
            "off",
            "pv",
            "now",
        }:

            desired_evcc_mode = (
                control_mode
            )

            reason = (
                "MANUAL_"
                + control_mode.upper()
            )

        else:

            desired_evcc_mode = "off"
            reason = "MODE_ERROR"

        current_evcc_mode = (
            get_evcc_mode()
        )

        if (
            current_evcc_mode
            != desired_evcc_mode
        ):
            set_evcc_mode(
                desired_evcc_mode
            )

            current_evcc_mode = (
                desired_evcc_mode
            )

        elli_control.update_controller_status(
            current_evcc_mode,
            reason
        )

        return {
            "control_mode": control_mode,
            "evcc_mode": current_evcc_mode,
            "reason": reason,
        }

    except Exception as exc:

        print(
            f"Elli controller error: "
            f"{exc}"
        )

        elli_control.update_controller_status(
            "unknown",
            "ERROR"
        )

        return {
            "control_mode": "unknown",
            "evcc_mode": "unknown",
            "reason": "ERROR",
            "error": str(exc),
        }


def run_elli_controller():

    print("Elli controller started")

    while True:

        run_elli_controller_once()

        time.sleep(5)


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

        meter_data = (
            charge_meter.get()
            if charge_meter
            else {
                "power": 0.0,
                "total_energy": 0.0,
                "daily_energy": 0.0,
                "error": None,
                "timestamp": None,
            }
        )

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
            "site_title": data.get("siteTitle", ""),
            "actual_charge_power": meter_data["power"],
            "actual_charge_total_energy": meter_data["total_energy"],
            "actual_charge_daily_energy": meter_data["daily_energy"],
            "actual_charge_power_error": meter_data["error"],
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

@app.route(
    "/api/evcc/control",
    methods=["GET", "POST"]
)
def evcc_control_api():

    if request.method == "GET":
        return jsonify(
            elli_control.get_status()
        )

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    try:

        result = elli_control.update(
            mode=data.get("mode"),
            spot_price_limit=data.get(
                "spot_price_limit"
            ),
            price_start=data.get(
                "price_start"
            ),
            price_end=data.get(
                "price_end"
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
            price_start=data.get(
                "price_start"
            ),
            price_end=data.get(
                "price_end"
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

    if ouman_eh203:
        ouman_eh203.start()

    spot_price.start()

    if charge_meter:
        threading.Thread(
            target=charge_meter.run,
            daemon=True
        ).start()

    threading.Thread(
        target=run_elli_controller,
        daemon=True
    ).start()

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
