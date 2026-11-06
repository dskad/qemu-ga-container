import os
import socket
import platform
import json
import subprocess
import time
from http.server import BaseHTTPRequestHandler, HTTPServer


def read_proc_lines(path):
    """Safely read a file in /proc, returning [] on any error."""
    try:
        with open(path, "r") as f:
            return f.read(4096).splitlines()
    except Exception:
        return []


def get_memory():
    """Parse /proc/meminfo into a compact dict."""
    mem = {
        "total_mb": 0,
        "used_mb": 0,
        "free_mb": 0,
        "available_mb": 0,
        "percent_used": 0.0,
    }
    info = {}
    for line in read_proc_lines("/proc/meminfo"):
        if ":" in line:
            key, value = line.split(":", 1)
            try:
                info[key.strip()] = int(value.strip().split()[0])  # kB
            except (ValueError, IndexError):
                pass

    total = info.get("MemTotal", 0)
    available = info.get("MemAvailable", info.get("MemFree", 0))
    free = info.get("MemFree", 0)
    if total > 0:
        used = total - available
        mem = {
            "total_mb": round(total / 1024),
            "used_mb": round(used / 1024),
            "free_mb": round(free / 1024),
            "available_mb": round(available / 1024),
            "percent_used": round(used / total * 100, 1),
        }
    return mem


def get_disk_stats():
    """Usage of the filesystem containing / (the container root)."""
    disk = {"total_gb": 0, "used_gb": 0, "free_gb": 0, "percent_used": 0.0}
    try:
        st = os.statvfs("/")
        total = st.f_blocks * st.f_frsize
        free = st.f_bavail * st.f_frsize
        used = total - free
        if total > 0:
            disk = {
                "total_gb": round(total / 1024**3, 1),
                "used_gb": round(used / 1024**3, 1),
                "free_gb": round(free / 1024**3, 1),
                "percent_used": round(used / total * 100, 1),
            }
    except Exception:
        pass
    return disk


def get_cpu_count():
    return os.cpu_count() or 0


def get_loadavg():
    """1/5/15 min load average."""
    try:
        load1, load5, load15 = os.getloadavg()
        return {"1min": round(load1, 2), "5min": round(load5, 2), "15min": round(load15, 2)}
    except Exception:
        return {"1min": 0.0, "5min": 0.0, "15min": 0.0}


def get_uptime_seconds():
    try:
        with open("/proc/uptime", "r") as f:
            return round(float(f.read().split()[0]))
    except Exception:
        return 0


def format_uptime(seconds):
    if seconds <= 0:
        return "unknown"
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def usage_class(percent):
    """CSS class for usage bars: ok / warn / crit."""
    if percent >= 90:
        return "crit"
    if percent >= 75:
        return "warn"
    return ""


def get_agent_info():
    """qemu-ga process status: running (with pid) or mock mode."""
    info = {"running": False, "pid": None, "mock_mode": True}
    try:
        for pid in [p for p in os.listdir("/proc") if p.isdigit()]:
            try:
                with open(f"/proc/{pid}/comm", "r") as f:
                    if f.read().strip() == "qemu-ga":
                        info = {"running": True, "pid": int(pid), "mock_mode": False}
                        break
            except Exception:
                continue
    except Exception:
        pass
    return info


def get_stats():
    uptime_seconds = get_uptime_seconds()
    stats = {
        "hostname": socket.gethostname(),
        "os": platform.system(),
        "os_release": "",
        "ips": [],
        "cpu_count": get_cpu_count(),
        "loadavg": get_loadavg(),
        "uptime_seconds": uptime_seconds,
        "uptime": format_uptime(uptime_seconds),
        "memory": get_memory(),
        "disk": get_disk_stats(),
        "agent": get_agent_info(),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    # Get OS Release info
    try:
        with open("/etc/os-release", "r") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    stats["os_release"] = line.split("=")[1].strip().strip('"')
                    break
    except Exception:
        pass

    # Get IP addresses
    try:
        # Using hostname -I as a simple way to get IPs in Alpine/Linux
        ips_output = subprocess.check_output(["hostname", "-I"], text=True).strip()
        if ips_output:
            stats["ips"] = ips_output.split()
    except Exception:
        pass

    return stats


class StatsHandler(BaseHTTPRequestHandler):
    def send_body(self, code, content_type, body):
        self.send_response(code)
        self.send_header("Content-type", content_type)
        self.end_headers()
        self.wfile.write(body.encode())

    def do_GET(self):
        if self.path == "/api/stats":
            stats = get_stats()
            self.send_body(200, "application/json", json.dumps(stats, indent=2))

        elif self.path == "/api/health":
            self.send_body(200, "application/json", json.dumps({"status": "ok"}))

        elif self.path == "/":
            stats = get_stats()
            mem_class = usage_class(stats["memory"]["percent_used"])
            disk_class = usage_class(stats["disk"]["percent_used"])
            agent = stats["agent"]
            agent_status = f"running (pid {agent['pid']})" if agent["running"] else "mock mode (no VirtIO device)"
            html = f"""
            <html>
            <head>
                <title>QEMU Guest Agent Stats</title>
                <meta http-equiv="refresh" content="10">
                <style>
                    :root {{
                        color-scheme: light dark;
                    }}
                    body {{
                        font-family: system-ui, -apple-system, sans-serif;
                        max-width: 640px;
                        margin: 40px auto;
                        padding: 0 16px;
                        line-height: 1.6;
                    }}
                    h1 {{ font-size: 1.4rem; }}
                    table {{
                        border-collapse: collapse;
                        width: 100%;
                    }}
                    td, th {{
                        text-align: left;
                        padding: 6px 10px;
                        border-bottom: 1px solid color-mix(in srgb, currentColor 20%, transparent);
                    }}
                    td.value {{ text-align: right; font-variant-numeric: tabular-nums; }}
                    .meters {{ display: flex; flex-direction: column; gap: 8px; }}
                    .meter {{
                        display: flex;
                        align-items: center;
                        gap: 10px;
                    }}
                    .meter .label {{ width: 60px; }}
                    .bar {{
                        flex: 1;
                        height: 10px;
                        background: color-mix(in srgb, currentColor 12%, transparent);
                        border-radius: 5px;
                        overflow: hidden;
                    }}
                    .bar > div {{
                        height: 100%;
                        background: #2da44e;
                        border-radius: 5px;
                    }}
                    .bar > div.warn {{ background: #d29922; }}
                    .bar > div.crit {{ background: #cf222e; }}
                    .muted {{ opacity: 0.7; font-size: 0.85rem; }}
                    footer {{ margin-top: 24px; }}
                </style>
            </head>
            <body>
                <h1>QEMU Guest Agent Stats</h1>
                <p class="muted">
                    {stats["timestamp"]} &middot;
                    auto-refresh 10s &middot;
                    <a href="/api/stats">View JSON</a>
                </p>
                <table>
                    <tr><th>Hostname</th><td class="value">{stats["hostname"]}</td></tr>
                    <tr><th>OS</th><td class="value">{stats["os"]} ({stats["os_release"]})</td></tr>
                    <tr><th>Uptime</th><td class="value">{stats["uptime"]}</td></tr>
                    <tr><th>IP Addresses</th><td class="value">{", ".join(stats["ips"])}</td></tr>
                    <tr><th>Guest Agent</th><td class="value">{agent_status}</td></tr>
                </table>

                <h2>Load</h2>
                <p>
                    {stats["loadavg"]["1min"]} / {stats["loadavg"]["5min"]} / {stats["loadavg"]["15min"]}
                    <span class="muted">on {stats["cpu_count"]} CPUs</span>
                </p>

                <h2>Memory</h2>
                <div class="meters">
                    <div class="meter">
                        <span class="label">{stats["memory"]["percent_used"]}%</span>
                        <div class="bar"><div class="{mem_class}" style="width: {stats["memory"]["percent_used"]}%"></div></div>
                        <span class="muted">{stats["memory"]["used_mb"]} / {stats["memory"]["total_mb"]} MB</span>
                    </div>
                </div>

                <h2>Disk (/)</h2>
                <div class="meters">
                    <div class="meter">
                        <span class="label">{stats["disk"]["percent_used"]}%</span>
                        <div class="bar"><div class="{disk_class}" style="width: {stats["disk"]["percent_used"]}%"></div></div>
                        <span class="muted">{stats["disk"]["used_gb"]} / {stats["disk"]["total_gb"]} GB</span>
                    </div>
                </div>

                <footer>
                    <p class="muted">Provided by the QEMU Guest Agent container.</p>
                </footer>
            </body>
            </html>
            """
            self.send_body(200, "text/html", html)
        else:
            self.send_error(404, "File Not Found")


def run(server_class=HTTPServer, handler_class=StatsHandler, port=None):
    if port is None:
        port = int(os.environ.get("STATS_PORT", 8080))
    server_address = ("", port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting stats server on port {port}...")
    httpd.serve_forever()


if __name__ == "__main__":
    run()
