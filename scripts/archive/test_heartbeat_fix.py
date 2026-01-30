import logging
from unittest.mock import patch

from tradingview_scraper.symbols.stream.streamer import Streamer

# Setup minimal logging for the test
logging.basicConfig(level=logging.DEBUG)


class MockWS:
    def __init__(self, messages):
        self.messages = messages
        self.sent_messages = []
        self.connected = True

    def recv(self):
        if not self.messages:
            # Simulate a timeout or closure after messages are exhausted
            from websocket import WebSocketConnectionClosedException

            raise WebSocketConnectionClosedException("Mock exhausted")
        return self.messages.pop(0)

    def send(self, msg):
        self.sent_messages.append(msg)


def test_heartbeat_reconnection_trigger():
    print(">>> Testing Heartbeat Reconnection Trigger...")

    # 1. Setup Streamer with mock handler
    with patch("tradingview_scraper.symbols.stream.streamer.StreamHandler") as mock_handler_class:
        streamer = Streamer(idle_packet_limit=3)
        mock_handler = mock_handler_class.return_value

        # Simulate 4 heartbeats. Limit is 3.
        # The 3rd heartbeat should trigger a 'break' in get_data's inner loop.
        messages = ["~m~4~m~~h~1", "~m~4~m~~h~2", "~m~4~m~~h~3", "~m~4~m~~h~4"]
        mock_ws = MockWS(messages)
        mock_handler.ws = mock_ws
        mock_handler.prepend_header = lambda m: f"~m~{len(m)}~m~{m}"

        # We'll run get_data. It will spin.
        # We want to see if it creates a NEW StreamHandler after 3 heartbeats.
        with patch.object(streamer.retry_handler, "get_delay", return_value=0.01):
            gen = streamer.get_data()

            try:
                # This will iterate through get_data.
                # Heartbeats don't yield, they just increment idle_packets and echo.
                # After 3 heartbeats, it breaks inner loop, sleeps, and RE-INITIALIZES self.stream_obj.
                # We can detect this by checking if mock_handler_class was called again.

                # Since get_data is an infinite loop, we wrap it
                import threading
                import time

                def run_gen():
                    try:
                        for _ in gen:
                            pass
                    except Exception as e:
                        print(f"Gen stopped: {e}")

                t = threading.Thread(target=run_gen)
                t.daemon = True
                t.start()

                # Wait for it to process
                time.sleep(1)

                # Check mock calls
                # 1 initial call in Streamer.__init__
                # 1 call after 3 heartbeats triggered 'break'
                print(f"StreamHandler creation calls: {mock_handler_class.call_count}")

                if mock_handler_class.call_count >= 2:
                    print("✅ SUCCESS: Reconnection triggered after heartbeats.")
                else:
                    print("❌ FAILURE: Reconnection NOT triggered.")

                print(f"Sent messages (echoes): {mock_ws.sent_messages}")
                if len(mock_ws.sent_messages) >= 3:
                    print("✅ SUCCESS: Heartbeats were echoed back.")
                else:
                    print("❌ FAILURE: Heartbeats were NOT echoed back.")

            except Exception as e:
                print(f"Test Error: {e}")


if __name__ == "__main__":
    test_heartbeat_reconnection_trigger()
