"""Slice 9: the TV shows a QR code that opens the phone join page with the room code
already filled in. Hosted, only the keyed TV can fetch it (it carries the code)."""

import re

import httpx
from websockets.sync.client import connect

from conftest import receive_view, running_server

JOIN_URL = "http://192.168.0.10:8000"


def _code(address: str, key: str = "") -> str:
    with connect(f"ws://{address}/ws/host{'?key=' + key if key else ''}") as tv:
        return receive_view(tv)["code"]


def test_tv_qr_code_links_to_join_page_with_code() -> None:
    with running_server() as address:
        code = _code(address)
        response = httpx.get(f"http://{address}/qr.svg")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/svg+xml")
        title = re.search(r"<title>(.*?)</title>", response.text)
        assert title is not None and title.group(1) == f"{JOIN_URL}/?code={code}"
        assert "<path" in response.text


def test_qr_code_needs_host_key_when_hosted() -> None:
    with running_server(host_key="lighthouse") as address:
        assert httpx.get(f"http://{address}/qr.svg").status_code == 401
        code = _code(address, "lighthouse")
        keyed = httpx.get(f"http://{address}/qr.svg", params={"key": "lighthouse"})
        assert keyed.status_code == 200
        assert f"code={code}" in keyed.text
