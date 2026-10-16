"""QR: the code on the TV that opens the phone join page with the room code filled in.

Builds the join link and renders it as an inline SVG (dark modules on a light ground,
so phones scan it off a dark TV). The SVG's <title> carries the link.

Does not: decide who may see it (the server checks the host key) or serve it.
"""

import io
from urllib.parse import quote

import segno


def join_link(join_url: str, code: str) -> str:
    return f"{join_url.rstrip('/')}/?code={quote(code)}"


def qr_svg(link: str) -> str:
    out = io.BytesIO()
    segno.make(link, error="m").save(
        out, kind="svg", scale=10, border=2, dark="#07162a", light="#f3eee2",
        title=link, xmldecl=False, svgns=True, omitsize=True,
    )
    return out.getvalue().decode()
