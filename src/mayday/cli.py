"""CLI: `uv run mayday` starts the game server, at home or hosted (ADR-0001, ADR-0008).

At home it finds the laptop's LAN address so phones know where to go. Hosted, it takes
the public URL from `--public-url` and the TV's secret from `MAYDAY_HOST_KEY`. Prints
the TV and phone URLs and runs uvicorn on all interfaces.

Does not: contain any game logic or serve anything itself (see server).
"""

import argparse
import os
import socket

import uvicorn

from mayday.server import create_app
from mayday.trivia import Pace


def find_lan_ip() -> str:
    """The address other devices on this WiFi can reach. Sends no packets."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        try:
            probe.connect(("10.255.255.255", 1))
            return probe.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def main() -> None:
    parser = argparse.ArgumentParser(prog="mayday", description="Run the Mayday! party server.")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--question-seconds", type=float, default=30.0, help="time limit per question")
    parser.add_argument("--public-url", help="address phones should open (hosted); default: this laptop on the LAN")
    args = parser.parse_args()

    join_url = (args.public_url or f"http://{find_lan_ip()}:{args.port}").rstrip("/")
    host_key = os.environ.get("MAYDAY_HOST_KEY") or None
    tv_url = f"{join_url if args.public_url else f'http://localhost:{args.port}'}/host"
    print(f"\n  TV (fullscreen on the laptop): {tv_url}{'?key=<MAYDAY_HOST_KEY>' if host_key else ''}")
    print(f"  Phones join at:                {join_url}\n")

    app = create_app(join_url=join_url, pace=Pace(question=args.question_seconds), host_key=host_key)
    uvicorn.run(app, host="0.0.0.0", port=args.port, log_level="warning", proxy_headers=True, forwarded_allow_ips="*")
