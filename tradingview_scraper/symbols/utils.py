import os
import json
import pandas as pd
from datetime import datetime

def ensure_export_directory(path='/export'):
    """Check if the export directory exists, and create it if it does not."""
    if not os.path.exists(path):
        try:
            os.makedirs(path)
            print(f"Directory {path} created.")
        except Exception as e:
            print(f"Error creating directory {path}: {e}")

def generate_export_filepath(symbol, file_extension):
    """Generate the export file path with the current timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    symbol_lower = symbol.lower()
    root_path = os.getcwd()
    path = os.path.join(root_path, "export", f"{symbol_lower}_{timestamp}{file_extension}")
    return path

def save_json_file(data, symbol):
    output_path = generate_export_filepath(symbol, '.json')
    ensure_export_directory(os.path.dirname(output_path))  # Ensure the directory exists
    try:
        with open(output_path, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"JSON file saved at: {output_path}")
    except FileNotFoundError:
        print(f"Error: The directory for {output_path} does not exist.")
    except PermissionError:
        print(f"Error: Permission denied when trying to write to {output_path}.")
    except TypeError as e:
        print(f"Error: The data provided is not serializable. {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def save_csv_file(data, symbol):
    output_path = generate_export_filepath(symbol, '.csv')
    ensure_export_directory(os.path.dirname(output_path))  # Ensure the directory exists
    try:
        df = pd.DataFrame.from_dict(data)
        df.to_csv(output_path, index=False)
        print(f"CSV file saved at: {output_path}")
    except ValueError as e:
        print(f"Error: The data provided is not in a suitable format for a DataFrame. {e}")
    except FileNotFoundError:
        print(f"Error: The directory for {output_path} does not exist.")
    except PermissionError:
        print(f"Error: Permission denied when trying to write to {output_path}.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
