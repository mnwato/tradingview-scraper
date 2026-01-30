import glob
from pathlib import Path

import yaml


def update_configs():
    files = glob.glob("configs/presets/crypto_cex_preset_*.yaml") + glob.glob("configs/crypto_cex_base_*.yaml")

    for f in files:
        path = Path(f)
        with open(path, "r") as stream:
            try:
                config = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(f"Error loading {f}: {exc}")
                continue

        if not config:
            continue

        changed = False

        # 1. Quotes
        target_quotes = ["USDT", "USDC", "USD", "DAI", "BUSD", "FDUSD"]
        if "allowed_spot_quotes" not in config or config["allowed_spot_quotes"] != target_quotes:
            config["allowed_spot_quotes"] = target_quotes
            changed = True

        # 2. Exclusions
        if config.get("exclude_dated_futures") is not True:
            config["exclude_dated_futures"] = True
            changed = True

        # 3. Standardization on Value.Traded for Liquidity
        if config.get("sort_by") != "Value.Traded":
            config["sort_by"] = "Value.Traded"
            changed = True
        if config.get("final_sort_by") != "Value.Traded":
            config["final_sort_by"] = "Value.Traded"
            changed = True
        if config.get("base_universe_sort_by") != "Value.Traded":
            config["base_universe_sort_by"] = "Value.Traded"
            changed = True

        if changed:
            print(f"Updating {f}...")
            with open(path, "w") as out:
                yaml.dump(config, out, default_flow_style=False, sort_keys=False)


if __name__ == "__main__":
    update_configs()
