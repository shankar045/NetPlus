# NetPulse — Intelligent Network Traffic Monitor

A medium-level Network Programming project built with Python, Flask, TCP sockets, SQLite, psutil, and Chart.js.

## Features

- TCP host/port connectivity tests using Python's `socket` module
- Response-time measurement in milliseconds
- SQLite storage for each monitoring result
- Dashboard summary cards and response-time history chart
- Local network-interface byte/packet counters and estimated upload/download rates
- Alerts for unreachable hosts and response times over 250 ms
- Input validation for hostnames, IP addresses, and ports

## Requirements

- Python 3.11 or newer recommended
- Internet connection for the Chart.js CDN and tests of public hosts
- Windows, macOS, or Linux

## Installation

Open a terminal in this project directory.

### Windows (PowerShell)

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

If PowerShell blocks activation, use Command Prompt:

```bat
py -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python app.py
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000 in your browser.

The SQLite database (`netpulse.db`) is created automatically on first run.

## How to use

1. Click a sample target, or enter a host, port, and optional label.
2. Click **Test connection**.
3. View the result, response time, and any alert.
4. Repeat checks to build the history chart and saved results.
5. Observe upload/download rates under Traffic statistics.

Suggested safe demo tests:
- `example.com`, port `443`
- `1.1.1.1`, port `53`
- `127.0.0.1`, port `5000` while NetPulse is running
- `localhost`, port `1` (expected to fail on most computers)

Public-host results depend on your network, firewall, DNS, and the destination's port policy. A failed TCP test does not always mean the entire host is offline.

## API endpoints

- `GET /api/summary` — aggregate check counts and average successful latency
- `GET /api/history?limit=30` — recent results for the chart and table
- `GET /api/alerts` — recent alerts
- `GET /api/traffic` — interface counters and estimated rates
- `POST /api/monitor` — run a TCP test and save its result

Example request:

```json
{
  "name": "Example HTTPS",
  "host": "example.com",
  "port": 443
}
```

## Network programming concepts demonstrated

- TCP sockets and connection timeouts
- DNS resolution through the socket API
- Hostname/IP and port validation
- Measuring elapsed connection time
- HTTP API communication between browser and Flask backend
- SQLite persistence and parameterized SQL queries
- OS network-interface counters

## Limitations

- TCP reachability is not the same as ICMP ping; this project measures TCP connection time.
- Traffic statistics are system-wide counters, not per-application bandwidth.
- Rates are estimated from consecutive browser polls; the first poll establishes a baseline.
- Chart.js is loaded from a CDN, so charts require internet access unless you download and serve Chart.js locally.
- This is a local educational application. Keep it bound to `127.0.0.1`; do not expose the development server to the public internet.
