"""
Module providing utility functions for validating exchange symbols and fetching
TradingView indicators and their metadata.

This module contains functions to:
  - Validate one or more exchange symbols.
  - Fetch a list of TradingView indicators based on a search query.
  - Display the fetched indicators and allow the user to select one.
  - Fetch and prepare indicator metadata for further processing.
"""

import logging
import time
import requests


def validate_symbols(exchange_symbol):
    """
    Validate one or more exchange symbols.

    This function checks whether the provided symbol or list of symbols follows
    the expected format ("EXCHANGE:SYMBOL") and validates each symbol by making a
    request to a TradingView validation URL.

    Args:
        exchange_symbol (str or list): A single symbol or a list of symbols in the format "EXCHANGE:SYMBOL".

    Raises:
        ValueError: If exchange_symbol is empty, if a symbol does not follow the "EXCHANGE:SYMBOL" format,
                    or if the symbol fails validation after the allowed number of retries.

    Returns:
        bool: True if all provided symbols are valid.
    """
    validate_url = (
        "https://scanner.tradingview.com/symbol?"
        "symbol={exchange}%3A{symbol}&fields=market&no_404=false"
    )

    if not exchange_symbol:
        raise ValueError("exchange_symbol cannot be empty")

    if isinstance(exchange_symbol, str):
        exchange_symbol = [exchange_symbol]

    for item in exchange_symbol:
        parts = item.split(":")
        if len(parts) != 2:
            raise ValueError(
                f"Invalid symbol format '{item}'. Must be like 'BINANCE:BTCUSDT'"
            )

        exchange, symbol = parts
        retries = 3

        for attempt in range(retries):
            try:
                res = requests.get(
                    validate_url.format(exchange=exchange, symbol=symbol), timeout=5
                )
                res.raise_for_status()
            except requests.RequestException as exc:
                status = getattr(exc.response, "status_code", None)
                if status == 404:
                    raise ValueError(
                        f"Invalid exchange:symbol '{item}' after {retries} attempts"
                    ) from exc

                logging.warning(
                    "Attempt %d failed to validate exchange:symbol '%s': %s",
                    attempt + 1,
                    item,
                    exc,
                )

                if attempt < retries - 1:
                    time.sleep(1)  # Wait briefly before retrying
                else:
                    raise ValueError(
                        f"Invalid exchange:symbol '{item}' after {retries} attempts"
                    ) from exc
            else:
                break  # Successful request; exit retry loop

    return True


def fetch_tradingview_indicators(query: str):
    """
    Fetch TradingView indicators based on a search query.

    This function sends a GET request to the TradingView public endpoint for indicator
    suggestions and filters the results by checking if the search query appears in either
    the script name or the author's username.

    Args:
        query (str): The search term used to filter indicators by script name or author.

    Returns:
        list: A list of dictionaries, each containing details of a matching indicator such as:
              - 'scriptName'
              - 'imageUrl'
              - 'author'
              - 'agreeCount'
              - 'isRecommended'
              - 'scriptIdPart'
              - 'version' (if available)
    """
    url = "https://www.tradingview.com/pubscripts-suggest-json/?search=" + query

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        json_data = response.json()

        results = json_data.get("results", [])
        filtered_results = []

        for indicator in results:
            if (
                query.lower() in indicator["scriptName"].lower()
                or query.lower() in indicator["author"]["username"].lower()
            ):
                filtered_results.append(
                    {
                        "scriptName": indicator["scriptName"],
                        "imageUrl": indicator["imageUrl"],
                        "author": indicator["author"]["username"],
                        "agreeCount": indicator["agreeCount"],
                        "isRecommended": indicator["isRecommended"],
                        "scriptIdPart": indicator["scriptIdPart"],
                        # 'version' may not be available in the API response.
                        "version": indicator.get("version"),
                    }
                )

        return filtered_results

    except requests.RequestException as exc:
        logging.error("Error fetching TradingView indicators: %s", exc)
        return []


def display_and_select_indicator(indicators):
    """
    Display a list of indicators and prompt the user to select one.

    This function prints the available indicators with numbering, waits for the user
    to input the number corresponding to their preferred indicator, and returns the
    selected indicator's scriptId and version.

    Args:
        indicators (list): A list of dictionaries containing indicator details.

    Returns:
        tuple or None: A tuple (scriptId, version) of the selected indicator if the selection
                       is valid; otherwise, None.
    """
    if not indicators:
        print("No indicators found.")
        return None

    print("\n-- Enter the number of your preferred indicator:")
    for idx, item in enumerate(indicators, start=1):
        print(f"{idx}- {item['scriptName']} by {item['author']}")

    try:
        selected_index = int(input("Your choice: ")) - 1
    except ValueError:
        print("Invalid input. Please enter a number.")
        return None

    if 0 <= selected_index < len(indicators):
        selected_indicator = indicators[selected_index]
        print(
            f"You selected: {selected_indicator['scriptName']} by {selected_indicator['author']}"
        )
        return (
            selected_indicator.get("scriptIdPart"),
            selected_indicator.get("version"),
        )
    else:
        print("Invalid selection.")
        return None


def fetch_indicator_metadata(script_id: str, script_version: str, chart_session: str):
    """
    Fetch metadata for a TradingView indicator based on its script ID and version.

    This function constructs a URL using the provided script ID and version, sends a GET
    request to fetch the indicator metadata, and then prepares the metadata for further
    processing using the chart session.

    Args:
        script_id (str): The unique identifier for the indicator script.
        script_version (str): The version of the indicator script.
        chart_session (str): The chart session identifier used in further processing.

    Returns:
        dict: A dictionary containing the prepared indicator metadata if successful;
              an empty dictionary is returned if an error occurs.
    """
    url = f"https://pine-facade.tradingview.com/pine-facade/translate/{script_id}/{script_version}"

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        json_data = response.json()

        metainfo = json_data.get("result", {}).get("metaInfo")
        if metainfo:
            return prepare_indicator_metadata(script_id, metainfo, chart_session)

        return {}

    except requests.RequestException as exc:
        logging.error("Error fetching indicator metadata: %s", exc)
        return {}


def prepare_indicator_metadata(script_id: str, metainfo: dict, chart_session: str):
    """
    Prepare indicator metadata into the required payload structure.

    This function constructs a dictionary payload for creating a study (indicator) session.
    It extracts default input values and metadata from the provided metainfo and combines them
    with the provided script ID and chart session.

    Args:
        script_id (str): The unique identifier for the indicator script.
        metainfo (dict): A dictionary containing metadata information for the indicator.
        chart_session (str): The chart session identifier.

    Returns:
        dict: A dictionary representing the payload required to create a study with the indicator.
    """
    output_data = {
        "m": "create_study",
        "p": [
            chart_session,
            "st9",
            "st1",
            "sds_1",
            "Script@tv-scripting-101!",
            {
                "text": metainfo["inputs"][0]["defval"],
                "pineId": script_id,
                "pineVersion": metainfo.get("pine", {}).get("version", "1.0"),
                "pineFeatures": {
                    "v": "{\"indicator\":1,\"plot\":1,\"ta\":1}",
                    "f": True,
                    "t": "text"
                },
                "__profile": {
                    "v": False,
                    "f": True,
                    "t": "bool"
                }
            }
        ]
    }

    # Collect additional input values that start with 'in_'
    in_x = {}
    for input_item in metainfo.get("inputs", []):
        if input_item["id"].startswith("in_"):
            in_x[input_item["id"]] = {
                "v": input_item["defval"],
                "f": True,
                "t": input_item["type"]
            }

    # Update the dictionary inside output_data with additional inputs
    for item in output_data["p"]:
        if isinstance(item, dict):
            item.update(in_x)

    return output_data
