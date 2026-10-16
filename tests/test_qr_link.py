from mayday.qr import join_link, qr_svg


def test_join_link_prefills_the_code() -> None:
    assert join_link("https://mayday.example", "MXQT") == "https://mayday.example/?code=MXQT"


def test_qr_svg_is_titled_with_its_link() -> None:
    svg = qr_svg("https://mayday.example/?code=MXQT")
    assert svg.startswith("<svg") and "<title>https://mayday.example/?code=MXQT</title>" in svg
