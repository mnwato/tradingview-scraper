import json
import logging
import os
import sys
from pathlib import Path

import yaml

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("validate_manifest")


def validate_manifest(manifest_path: Path):
    if not manifest_path.exists():
        logger.error(f"Manifest not found: {manifest_path}")
        return False

    try:
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse manifest: {e}")
        return False

    profiles = manifest.get("profiles", {})
    defaults = manifest.get("defaults", {})
    default_profile = manifest.get("default_profile")
    all_ok = True

    if not defaults:
        logger.error("Manifest missing mandatory 'defaults' block (Strict Defaults policy).")
        all_ok = False

    if default_profile and default_profile not in profiles:
        logger.error(f"Default profile '{default_profile}' not found in profiles.")
        return False

    # 1. Validate Aliases
    for name, data in profiles.items():
        if isinstance(data, str):
            visited = {name}
            target = data
            while isinstance(profiles.get(target), str):
                if target in visited:
                    logger.error(f"Circular alias detected: {' -> '.join(visited)} -> {target}")
                    return False
                visited.add(target)
                target = profiles.get(target)

            if target not in profiles:
                logger.error(f"Alias '{name}' points to missing profile '{target}'")
                return False
            logger.info(f"Alias validation OK: {name} -> {target}")

    # 2. Validate Profile Logic
    for name, data in profiles.items():
        actual_data = data
        while isinstance(actual_data, str):
            actual_data = profiles.get(actual_data)

        if not isinstance(actual_data, dict):
            continue

        # Data Logic (Resolution includes defaults)
        def get_val(key, section=None):
            if section:
                return actual_data.get(section, {}).get(key) or defaults.get(section, {}).get(key)
            return actual_data.get(key) or defaults.get(key)

        lookback = get_val("lookback_days", "data") or 0
        train_window = get_val("train_window", "backtest") or 0
        test_window = get_val("test_window", "backtest") or 0
        min_days = get_val("min_days_floor", "data") or 0

        if train_window > 0 and lookback > 0:
            if train_window >= lookback:
                logger.error(f"Profile '{name}': train_window ({train_window}) must be less than lookback_days ({lookback})")
                all_ok = False

        if min_days > 0 and train_window > 0:
            if min_days < train_window:
                logger.error(f"Profile '{name}': min_days_floor ({min_days}) should be >= train_window ({train_window}) to ensure valid optimization")
                all_ok = False

        # 3. Validate Pipeline Scanner Paths
        discovery = actual_data.get("discovery", {})
        if not discovery:
            # Check defaults
            discovery = defaults.get("discovery", {})

        pipelines = discovery.get("pipelines", {})

        for p_name, p_config in pipelines.items():
            scanners = p_config.get("scanners", [])
            for s_path in scanners:
                # Check if it's a relative path from configs/
                full_path = Path("configs") / s_path
                if not full_path.suffix:
                    full_path = full_path.with_suffix(".yaml")

                if not full_path.exists():
                    logger.error(f"Profile '{name}', Pipeline '{p_name}': Scanner file not found: {full_path}")
                    all_ok = False
                    continue

                # Validate YAML
                try:
                    with open(full_path, "r") as yf:
                        yaml_data = yaml.safe_load(yf)
                    if not isinstance(yaml_data, dict):
                        logger.error(f"Scanner file is not a dictionary: {full_path}")
                        all_ok = False
                except Exception as e:
                    logger.error(f"Failed to parse scanner YAML {full_path}: {e}")
                    all_ok = False

    # 4. Validate Execution Env
    execution_env = manifest.get("execution_env", {})
    mandatory_vars = execution_env.get("mandatory_vars", [])
    for var in mandatory_vars:
        if not os.getenv(var):
            logger.error(f"Mandatory environment variable '{var}' is missing.")
            all_ok = False

    return all_ok


if __name__ == "__main__":
    success = validate_manifest(Path("configs/manifest.json"))
    if not success:
        sys.exit(1)
    logger.info("Manifest validation SUCCESSFUL.")
