from trader.cron_tick import build_event_message


def test_build_event_message_returns_none_when_no_important_event():
    before = {"filled_orders": 0, "trades": 0, "rejected": 3}
    after = {"filled_orders": 0, "trades": 0, "rejected": 6}

    assert build_event_message(before, after) is None


def test_build_event_message_reports_filled_order():
    before = {"filled_orders": 0, "trades": 0, "rejected": 0}
    after = {"filled_orders": 1, "trades": 0, "rejected": 2}

    message = build_event_message(before, after)

    assert message is not None
    assert "Paper trading event" in message
    assert "New filled paper orders: 1" in message


def test_build_event_message_reports_closed_trade():
    before = {"filled_orders": 1, "trades": 0, "rejected": 0}
    after = {"filled_orders": 1, "trades": 1, "rejected": 0}

    message = build_event_message(before, after)

    assert message is not None
    assert "New closed paper trades: 1" in message
