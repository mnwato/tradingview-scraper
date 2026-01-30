from tradingview_scraper.symbols.stream.retry import RetryHandler


def test_retry_handler_initial_delay():
    handler = RetryHandler(initial_delay=1.0)
    assert handler.get_delay(0) == 1.0


def test_retry_handler_exponential_backoff():
    handler = RetryHandler(initial_delay=1.0, backoff_factor=2.0)
    assert handler.get_delay(0) == 1.0
    assert handler.get_delay(1) == 2.0
    assert handler.get_delay(2) == 4.0


def test_retry_handler_max_delay():
    handler = RetryHandler(initial_delay=1.0, max_delay=5.0, backoff_factor=2.0)
    assert handler.get_delay(0) == 1.0
    assert handler.get_delay(1) == 2.0
    assert handler.get_delay(2) == 4.0
    assert handler.get_delay(3) == 5.0
    assert handler.get_delay(4) == 5.0


def test_retry_handler_iteration():
    handler = RetryHandler(max_retries=3, initial_delay=1.0, backoff_factor=2.0)
    delays = list(handler)
    assert delays == [1.0, 2.0, 4.0]
