import os
import json
import random
from datetime import datetime
from typing import List

import pandas as pd


def ensure_export_directory(path='/export'):
    """Check if the export directory exists, and create it if it does not.

    Parameters
    ----------
    path : str, optional
        The path to the export directory. Defaults to '/export'.

    Raises
    ------
    Exception
        If there is an error creating the directory.
    """
    if not os.path.exists(path):
        try:
            os.makedirs(path)
            print(f"[INFO] Directory {path} created.")
        except Exception as e:
            print(f"[ERROR] Error creating directory {path}: {e}")

def generate_export_filepath(symbol, data_category, timeframe, file_extension):
    """Generate a file path for exporting data, including the current timestamp.

    This function constructs a file path based on the provided symbol, data category,
    and file extension. The generated path will include a timestamp to ensure uniqueness.

    Parameters
    ----------
    symbol : str
        The symbol to include in the file name, formatted in lowercase.
    data_category : str
        The category of data being exported, which will be prefixed in the file name.
    file_extension : str
        The file extension for the export file (e.g., '.json', '.csv').
    timeframe: str
        Timeframe of report like (e.g., '1M', '1W').

    Returns
    -------
    str
        The generated file path, structured as:
        "<current_directory>/export/<data_category>_<symbol>_<timestamp><file_extension>".
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    symbol_lower = f'{symbol.lower()}_' if symbol else ''
    timeframe = f'{timeframe}_' if timeframe else ''
    root_path = os.getcwd()
    path = os.path.join(root_path, "export", f"{data_category}_{symbol_lower}{timeframe}{timestamp}{file_extension}")
    return path

def save_json_file(data, **kwargs):
    """
    Save the provided data to a JSON file with a generated file path.

    This function creates a JSON file using the specified symbol and data category
    to generate a unique file name. The file is saved in the 'export' directory.

    Parameters
    ----------
    data : dict
        The data to be saved in the JSON file. Must be serializable to JSON format.
    **kwargs : dict
        Additional parameters for file naming:
        - symbol (str): The symbol to include in the file name, formatted to lowercase.
        - data_category (str): The category of the data, used to distinguish between different datasets.
        - timeframe (str, optional): The timeframe for the data, which can be included in the file name. Defaults to an empty string.

    Raises
    ------
    FileNotFoundError
        If the directory for the output path does not exist.
    PermissionError
        If permission is denied when trying to write to the file.
    TypeError
        If the data provided is not serializable to JSON.
    Exception
        For any unexpected errors that may occur during file writing.
    """
    symbol = kwargs.get('symbol')
    data_category = kwargs.get('data_category')
    timeframe = kwargs.get('timeframe', '')
    
    output_path = generate_export_filepath(symbol, data_category, timeframe, '.json')
    ensure_export_directory(os.path.dirname(output_path))  # Ensure the directory exists
    try:
        with open(output_path, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[INFO] JSON file saved at: {output_path}")
    except FileNotFoundError:
        print(f"[ERROR] Error: The directory for {output_path} does not exist.")
    except PermissionError:
        print(f"[ERROR] Error: Permission denied when trying to write to {output_path}.")
    except TypeError as e:
        print(f"[ERROR] Error: The data provided is not serializable. {e}")
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {e}")

def save_csv_file(data, **kwargs):
    """
    Save the provided data to a CSV file with a generated file path.

    This function creates a CSV file using the specified symbol and data category
    to generate a unique file name. The file is saved in the 'export' directory.

    Parameters
    ----------
    data : dict
        The data to be saved in the CSV file. Must be in a suitable format for a DataFrame.
    **kwargs : dict
        Additional parameters for file naming:
        - symbol (str): The symbol to include in the file name, formatted to lowercase.
        - data_category (str): The category of the data, used to distinguish between different datasets.
        - timeframe (str, optional): The timeframe for the data, which can be included in the file name. Defaults to an empty string.

    Raises
    ------
    ValueError
        If the data provided is not in a suitable format for a DataFrame.
    FileNotFoundError
        If the directory for the output path does not exist.
    PermissionError
        If permission is denied when trying to write to the file.
    Exception
        For any unexpected errors that may occur during file writing.
    """
    symbol = kwargs.get('symbol')
    data_category = kwargs.get('data_category')
    timeframe = kwargs.get('timeframe', '')

    output_path = generate_export_filepath(symbol, data_category, timeframe, '.csv')
    ensure_export_directory(os.path.dirname(output_path))  # Ensure the directory exists
    try:
        df = pd.DataFrame.from_dict(data)
        df.to_csv(output_path, index=False)
        print(f"[INFO] CSV file saved at: {output_path}")
    except ValueError as e:
        print(f"[ERROR] Error: The data provided is not in a suitable format for a DataFrame. {e}")
    except FileNotFoundError:
        print(f"[ERROR] Error: The directory for {output_path} does not exist.")
    except PermissionError:
        print(f"[ERROR] Error: Permission denied when trying to write to {output_path}.")
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {e}")

def generate_user_agent():
    """
    Generates a random user agent string from a predefined list of Google bot user agents.

    Returns
    -------
    str
        A random Google bot user agent string.
    """
    user_agents = [
        "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        "Mozilla/5.0 (compatible; Googlebot-Image/1.0; +http://www.google.com/bot.html)",
        "Mozilla/5.0 (compatible; Googlebot-News; +http://www.google.com/bot.html)",
        "Mozilla/5.0 (compatible; Googlebot-Video/1.0; +http://www.google.com/bot.html)",
        "Mozilla/5.0 (compatible; Googlebot-AdsBot/1.0; +http://www.google.com/bot.html)",
        "Mozilla/5.0 (compatible; Google-Site-Verification/1.0; +http://www.google.com/bot.html)"
    ]
    
    return random.choice(user_agents)

def validate_string_array(data: List[str], valid_values: List[str]) -> bool:
    """
    Validates a list of strings against a list of valid values.

    This function checks if each item in the provided list of strings is present in the list of valid values.

    Parameters
    ----------
    data : list[str]
        The list of strings to validate.

    valid_values : list[str]
        The list of valid values to check against.

    Returns
    -------
    bool
        True if all items in the data list are valid, False otherwise.
    """
    
    if not data:
        return False

    for item in data:
        if item not in valid_values:
            return False
    
    return True
