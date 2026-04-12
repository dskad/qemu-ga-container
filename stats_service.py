import os
import socket
import platform
import json
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer


def get_stats():
    stats = {
        "hostname": socket.gethostname(),
        "os": platform.system(),
        "os_release": "",
        "ips": [],
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
    def do_GET(self):
        if self.path == "/api/stats":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            stats = get_stats()
            self.wfile.write(json.dumps(stats).encode())

        elif self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            stats = get_stats()

            html = f"""
            <html>
            <head><title>QEMU Guest Agent Stats</title></head>
            <body>
                <h1>QEMU Guest Agent Stats</h1>
                <ul>
                    <li><strong>Hostname:</strong> {stats["hostname"]}</li>
                    <li><strong>OS:</strong> {stats["os"]} ({stats["os_release"]})</li>
                    <li><strong>IP Addresses:</strong> {", ".join(stats["ips"])}</li>
                </ul>
                <p><a href="/api/stats">View JSON</a></p>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
        else:
            self.send_error(404, "File Not Found")


def run(server_class=HTTPServer, handler_class=StatsHandler, port=8080):
    server_address = ("", port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting stats server on port {port}...")
    httpd.serve_forever()


if __name__ == "__main__":
    run()
