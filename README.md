# SMA Local Portal

SMA Local Portal is a lightweight local monitoring and integration service for SMA photovoltaic systems.

It collects real-time data directly from the local network, stores historical measurements, and provides both a web dashboard and a REST API. The project was originally developed for an existing SMA installation where local access and independence from cloud services were important.

The REST API also provides a common local data source for other applications, such as EVCC and a PV surplus load controller.

## Features

- Real-time monitoring of SMA PV production and grid power
- SMA inverter data over Modbus TCP
- SMA Energy Meter data over local Speedwire multicast
- Historical measurements stored locally in SQLite
- Web dashboard for current and historical data
- REST API for local integrations
- Optional RESOL temperature monitoring
- Finnish spot electricity price integration
- EVCC status and charging-mode integration
- Interface for an external PV surplus load controller

## Architecture

SMA Local Portal separates energy data collection from the applications that use the data.

The current implementation receives grid measurements from an SMA Energy Meter over Speedwire multicast and reads PV inverter data over Modbus TCP. The collected data is combined into a common local state and exposed through the REST API.

This makes it possible for other local applications to use the same energy data without communicating directly with the SMA devices.

Current integrations include EVCC and an external PV surplus load controller.

## Tested hardware

The project has been developed and tested with the following SMA equipment:

- SMA Energy Meter
- SMA Sunny Tripower STP 5000TL-20
- SMA Sunny Tripower STP 6000TL-20
- SMA Sunny Tripower STP 6.0-3AV-40

The test installation also includes an SMA Home Manager 1.0, but SMA Local Portal does not require it for operation.

Optional temperature monitoring has been tested with a RESOL DL2 data logger connected to a DeltaSol MX system.

## Requirements

- Python 3
- Linux system connected to the same local network as the SMA devices
- Network access to SMA Speedwire multicast traffic
- Modbus TCP enabled on the configured SMA inverters

Python dependencies are listed in `requirements.txt`.

## Installation

Clone the repository and create a Python virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Inverter configuration

Create the local device configuration from the provided example:

```bash
cp devices.example.yaml devices.yaml
```

Edit `devices.yaml` and replace the example addresses with the local IP addresses of your SMA inverters.

The `devices.yaml` file is intentionally excluded from Git because it contains installation-specific network configuration.

### SMA Energy Meter

The SMA Energy Meter does not require an IP address in `devices.yaml`.

SMA Local Portal listens for Speedwire measurement packets on the local network using UDP multicast address `239.12.255.254` and port `9522`.

The host running SMA Local Portal must therefore be able to receive this multicast traffic from the SMA Energy Meter.

### Optional integrations and display settings

SMA Local Portal runs normally without a `settings.yaml` file.

To configure optional integrations and installation-specific display settings, create the local settings file from the example:

```bash
cp settings.example.yaml settings.yaml
```

The `resol` section enables optional RESOL temperature monitoring. Edit the URL and data-field mapping to match your RESOL DL2 installation.

The optional `heater` section can be used to customize the PV surplus load display. The `title` setting changes the name shown in the web interface.

Optional `temperature_limit` and `temperature_resume` values can also be configured for display purposes. These values are informational only: SMA Local Portal displays them but does not enforce temperature control or safety limits.

The `settings.yaml` file is intentionally excluded from Git because it contains installation-specific configuration.

## Running

Start SMA Local Portal from the project directory:

```bash
source venv/bin/activate
python -m app
```

The web interface is available on port `8080`. By default, Flask listens on `0.0.0.0`, making the service reachable through the host computer's network interfaces.

The web port can be changed with the `SMA_PORT` environment variable:

```bash
SMA_PORT=8081 python -m app
```

### Running with systemd

An example systemd service is provided in `services/sma-dashboard.service`.

Before installing it, adjust the `User`, `Group`, `WorkingDirectory`, and `ExecStart` values to match your system.

The example assumes that the project is installed in `/opt/sma-local-portal` and runs under a dedicated `sma` user and group.

## Security

SMA Local Portal is intended for use on a trusted local network. The web interface and REST API do not currently provide authentication.

Do not expose the service directly to the public Internet. If remote access is required, use an appropriate secured network connection or reverse proxy with access control.

## REST API

SMA Local Portal exposes its current and historical data through a local REST API.

| Endpoint | Method | Description |
| --- | --- | --- |
| `/api/status` | GET | Current inverter, grid, PV and integration status |
| `/api/history` | GET | Historical measurement data |
| `/api/energy_stats` | GET | Energy statistics |
| `/api/evcc` | GET | EVCC charging status |
| `/api/evcc/mode` | POST | Change EVCC charging mode |
| `/api/heater/control` | GET / POST | Read or change heater-control settings |
| `/api/heater/status` | POST | Update heater-controller power and status |

## EVCC integration

EVCC integration is optional and is not required for the core SMA monitoring functionality.

The current implementation expects EVCC to be running on the same host at `127.0.0.1:7070` and uses the first configured EVCC loadpoint.

SMA Local Portal can display EVCC charging information and change the loadpoint mode between `pv`, `now`, and `off`.

The EVCC address is currently fixed in `app.py` and may be made configurable in a future version.

## PV surplus load control

SMA Local Portal includes an interface for an external controller that can use surplus PV energy for a controllable load.

The current installation uses the interface for domestic hot water heating. The portal stores control settings such as operating mode, spot-price limit, and maximum power, while the external controller performs the actual power control and reports its status back to the portal.

The load size and hardware implementation are installation-specific. SMA Local Portal does not assume a particular heater power or element configuration.

The external controller software and hardware are intended to be documented as a separate project.

## Safety

SMA Local Portal is monitoring and integration software. It does not replace the electrical or thermal safety systems required by any connected load.

Any external load-control hardware must be designed and installed with appropriate electrical protection, independent temperature limits where applicable, and components rated for the intended load.

Work on mains-voltage equipment must follow applicable electrical regulations and safety requirements.

## Spot electricity prices

The current implementation includes Finnish spot electricity prices using the Pörssisähkö.net API.

Price data is cached locally in `spot_prices.json`. If the external price service is unavailable, the error is reported in the price status while the rest of SMA Local Portal continues to operate.

Spot-price information can also be used as a condition by the external surplus-load controller.

## Project status and future development

SMA Local Portal is a working project developed around a real residential PV installation. The current code reflects the hardware and integrations used in that installation.

A future goal is to separate the grid-meter implementation from the rest of the application more clearly. This would allow alternative local energy meters, such as a Shelly Pro 3EM or a Modbus energy meter, to provide the same measurements without changing the applications that consume the REST API.

Other possible improvements include configurable EVCC connection settings and further separation of optional integrations from the core monitoring service.

## License

This project is licensed under the MIT License. See `LICENSE` for details.
