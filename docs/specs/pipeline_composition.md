# Specification: Pipeline Composition & Resolution (L0-L4)

## 1. Overview
This document specifies the recursive resolution and composition logic for market scanners. It ensures that complex pipelines can be built from simple, reusable building blocks (Layers).

## 2. Precedence Rules
When layers are composed, properties in higher layers override or merge with properties in lower layers.

**Precedence Order (Highest to Lowest):**
1.  **L4 (Scanner Entry)**: Final overrides and timeframe.
2.  **L3 (Strategy Block)**: Alpha logic (Trend, Momentum).
3.  **L2 (Asset Template)**: Session rules, exchange priorities.
4.  **L1 (Hygiene Layer)**: Global technical/liquidity floors.
5.  **L0 (Foundation)**: Index constituents, base symbol lists.

## 3. Merging Logic
- **Primitive Types** (Strings, Ints, Bools): Higher layer completely replaces lower layer.
- **Dictionaries**: Recursively merged.
- **Lists**: Higher layer completely replaces lower layer (no automatic appending).

## 4. Implementation Details

### Recursive Resolution
The `compose_pipeline.py` script resolves the `base_preset` key recursively.
```python
def resolve_inheritance(current_raw, current_base_dir):
    if "base_preset" in current_raw:
        preset_path = resolve_relative_path(current_raw.pop("base_preset"), current_base_dir)
        base_raw = load_yaml(preset_path)
        return deep_merge(resolve_inheritance(base_raw, preset_path.parent), current_raw)
    return current_raw
```

### Manifest Integration
Pipelines are defined in `manifest.json` under `discovery.pipelines`.
```json
"candidate_discovery": {
  "scanners": [
    "scanners/crypto/vol_breakout",
    "scanners/tradfi/global_macro"
  ],
  "interval": "1d",
  "ingestion_depth": 500
}
```

## 5. Directory Structure
- `configs/base/universes/`: L0 Foundations.
- `configs/base/hygiene/`: L1 Global Filters.
- `configs/base/templates/`: L2 Asset Personality.
- `configs/base/strategies/`: L3 Alpha Logic.
- `configs/scanners/`: L4 Runnable Entry Points.
