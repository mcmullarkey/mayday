from mayday.factcheck import missing_quotes

ARTICLE = """The wreck of the British ocean liner RMS Titanic lies at a depth of about
12,500 feet (2,100 fathoms; 3,800 metres), about 325 nautical miles."""


def test_present_quotes_pass_ignoring_case_and_line_breaks() -> None:
    assert missing_quotes(ARTICLE, ["lies at a depth of about 12,500 feet", "RMS TITANIC"]) == []


def test_absent_quotes_are_reported() -> None:
    assert missing_quotes(ARTICLE, ["about 20,000 feet"]) == ["about 20,000 feet"]


def test_curly_quotes_and_dashes_match_straight_ones() -> None:
    assert missing_quotes('known as “the Arch” – deep', ['known as "the Arch" - deep']) == []
