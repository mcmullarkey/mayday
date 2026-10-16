"""CLI: `uv run mayday` starts the game server for a party on the home network.

Finds the laptop's LAN address so phones know where to go, prints the TV and phone
URLs, and runs uvicorn on all interfaces.

Does not: contain any game logic or serve anything itself (see server).
"""

import argparse
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
    parser.add_argument("--question-seconds", type=float, default=20.0, help="time limit per question")
    args = parser.parse_args()

    join_url = f"http://{find_lan_ip()}:{args.port}"
    print(f"\n  TV (open on this laptop, fullscreen): http://localhost:{args.port}/host")
    print(f"  Phones join at:                      {join_url}\n")
    uvicorn.run(create_app(join_url=join_url, pace=Pace(question=args.question_seconds)), host="0.0.0.0", port=args.port, log_level="warning")
