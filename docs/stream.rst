tradingview_scraper.symbols.stream
===========================================

Usage patterns
--------------
- ``Streamer``: bounded historical slices plus optional indicators; set ``export_result=True`` to return ``{"ohlc": [...], "indicator": {...}}`` and write files to ``export/``.
- ``Streamer`` live continuation: call once with ``export_result=True`` for a warm start, then a second time with ``export_result=False`` to keep streaming packets and merge on timestamps.
- ``RealTimeData``: live quote/1m stream with quote fields (no export or indicators).

Submodules
----------

tradingview_scraper.symbols.stream.price module
------------------------------------------------

.. automodule:: tradingview_scraper.symbols.stream.price
   :members:
   :undoc-members:
   :show-inheritance:

tradingview_scraper.symbols.stream.stream\_handler module
----------------------------------------------------------

.. automodule:: tradingview_scraper.symbols.stream.stream_handler
   :members:
   :undoc-members:
   :show-inheritance:

tradingview_scraper.symbols.stream.streamer module
---------------------------------------------------

.. automodule:: tradingview_scraper.symbols.stream.streamer
   :members:
   :undoc-members:
   :show-inheritance:

tradingview_scraper.symbols.stream.utils module
------------------------------------------------

.. automodule:: tradingview_scraper.symbols.stream.utils
   :members:
   :undoc-members:
   :show-inheritance:

Module contents
---------------

.. automodule:: tradingview_scraper.symbols.stream
   :members:
   :undoc-members:
   :show-inheritance: