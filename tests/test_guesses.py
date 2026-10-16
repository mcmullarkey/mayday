from mayday.guesses import MAX_WRONG, WINDOW_SECONDS, GuessLog


def _after_wrong(count: int, who: str = "1.2.3.4", start: float = 0.0) -> GuessLog:
    log = GuessLog()
    for i in range(count):
        log = log.record_wrong(who, now=start + i)
    return log


def test_a_few_typos_are_fine() -> None:
    assert not _after_wrong(MAX_WRONG - 1).locked("1.2.3.4", now=20)


def test_too_many_wrong_codes_locks_that_address() -> None:
    log = _after_wrong(MAX_WRONG)
    assert log.locked("1.2.3.4", now=20)
    assert not log.locked("5.6.7.8", now=20)


def test_lock_lifts_once_old_guesses_leave_the_window() -> None:
    log = _after_wrong(MAX_WRONG, start=0.0)
    assert log.locked("1.2.3.4", now=WINDOW_SECONDS - 1)
    assert not log.locked("1.2.3.4", now=WINDOW_SECONDS + MAX_WRONG)


def test_recording_forgets_guesses_outside_the_window() -> None:
    log = _after_wrong(MAX_WRONG - 1, start=0.0).record_wrong("1.2.3.4", now=WINDOW_SECONDS + 100)
    assert not log.locked("1.2.3.4", now=WINDOW_SECONDS + 100)
