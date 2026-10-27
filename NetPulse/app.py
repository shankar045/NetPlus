from flask import Flask, jsonify, render_template, request
import ipaddress
import re
import socket
import time
from datetime import datetime, timezone

import psutil

from database import init_db, save_result, get_history, get_summary, get_recent_alerts

app = Flask(__name__)
init_db()

DEFAULT_TARGETS = [
    {"name": "Google DNS", "host": "8.8.8.8", "port": 53},
    {"name": "Cloudflare DNS", "host": "1.1.1.1", "port": 53},
    {"name": "HTTPS website", "host": "example.com", "port": 443},
]

_previous_traffic = None
_previous_traffic_time = None


def valid_host(host):
    """Allow an IP address or a conventional DNS hostname."""
    host = host.strip()
    if not host or len(host) > 253 or any(ch.isspace() for ch in host):
        return False
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        pass

    # DNS labels: letters/numbers/hyphens, not starting or ending with a hyphen.
    hostname_pattern = re.compile(
        r"^(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)(?:\."
        r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*\.?$"
    )
    return bool(hostname_pattern.fullmatch(host))


def tcp_check(host, port, timeout=2.0):
    """Try a TCP connection and return reachability and elapsed time."""
    started = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        return {
            "status": "UP",
            "latency_ms": elapsed_ms,
            "message": f"TCP connection to port {port} succeeded",
        }
    except (socket.timeout, TimeoutError):
        return {"status": "DOWN", "latency_ms": None, "message": "Connection timed out"}
    except socket.gaierror:
        return {"status": "DOWN", "latency_ms": None, "message": "Hostname could not be resolved"}
    except OSError as exc:
        return {"status": "DOWN", "latency_ms": None, "message": f"Connection failed: {exc.strerror or 'network error'}"}


@app.route("/")
def index():
    return render_template("index.html", targets=DEFAULT_TARGETS)


@app.get("/api/summary")
def api_summary():
    return jsonify(get_summary())


@app.get("/api/history")
def api_history():
    try:
        limit = min(max(int(request.args.get("limit", 30)), 1), 200)
    except ValueError:
        limit = 30
    return jsonify(get_history(limit))


@app.get("/api/alerts")
def api_alerts():
    return jsonify(get_recent_alerts(10))


@app.get("/api/traffic")
def api_traffic():
    """Return OS network-interface byte counters and approximate rates between polls."""
    global _previous_traffic, _previous_traffic_time

    counters = psutil.net_io_counters()
    now = time.monotonic()
    current = {
        "bytes_sent": counters.bytes_sent,
        "bytes_recv": counters.bytes_recv,
        "packets_sent": counters.packets_sent,
        "packets_recv": counters.packets_recv,
    }

    upload_rate = 0.0
    download_rate = 0.0
    if _previous_traffic is not None and _previous_traffic_time is not None:
        elapsed = now - _previous_traffic_time
        if elapsed > 0:
            upload_rate = max(0, current["bytes_sent"] - _previous_traffic["bytes_sent"]) / elapsed
            download_rate = max(0, current["bytes_recv"] - _previous_traffic["bytes_recv"]) / elapsed

    _previous_traffic = current
    _previous_traffic_time = now

    return jsonify({
        **current,
        "upload_bytes_per_sec": round(upload_rate, 2),
        "download_bytes_per_sec": round(download_rate, 2),
        "sampled_at": datetime.now(timezone.utc).isoformat(),
    })


@app.post("/api/monitor")
def api_monitor():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "Custom host")).strip()[:60]
    host = str(data.get("host", "")).strip()
    try:
        port = int(data.get("port", 443))
    except (TypeError, ValueError):
        return jsonify({"error": "Port must be a number between 1 and 65535."}), 400

    if not valid_host(host):
        return jsonify({"error": "Enter a valid IP address or DNS hostname."}), 400
    if not 1 <= port <= 65535:
        return jsonify({"error": "Port must be between 1 and 65535."}), 400

    result = tcp_check(host, port)
    result.update({
        "name": name or host,
        "host": host,
        "port": port,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    })
    if result["status"] == "UP" and result["latency_ms"] is not None and result["latency_ms"] > 250:
        result["alert"] = "High latency: response time exceeded 250 ms."
    elif result["status"] == "DOWN":
        result["alert"] = "Host is unreachable on the selected TCP port."
    else:
        result["alert"] = None

    save_result(result)
    return jsonify(result)


@app.errorhandler(404)
def not_found(_error):
    return jsonify({"error": "Endpoint not found."}), 404


if __name__ == "__main__":
    # Debug mode is for local development only. Do not expose this server publicly.
    app.run(host="127.0.0.1", port=5000, debug=True)
