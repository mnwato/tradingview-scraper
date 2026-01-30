# Design Plan: Manifest-Driven Selection Ranking (2026-01-16)

## 1. Objective
Decouple the selection ranking logic from hardcoded code in `policy.py` and move it to the **Manifest Schema**. This allows each profile to self-contain its ranking preferences (e.g., `ascending` for Shorts, `descending` for Longs) without requiring code changes.

## 2. Schema Updates

### 2.1 Manifest (`configs/manifest.json`)
Extend the `selection` object within each profile to support a `ranking` configuration.

**New Schema**:
```json
"selection": {
  "top_n": 15,
  "threshold": 0.45,
  "ranking": {
    "method": "alpha_score",  // Default: alpha_score
    "direction": "ascending"  // Options: ascending, descending (Default: descending)
  }
}
```

### 2.2 Profile Updates
- **Long Profiles**: Set `"direction": "descending"` (Default).
- **Short Profiles**: Set `"direction": "ascending"` (Explicit).

## 3. Code Modifications

### 3.1 Settings Model (`tradingview_scraper/settings.py`)
Update `SelectionConfig` Pydantic model to include the `ranking` nested object.

### 3.2 Selection Policy (`tradingview_scraper/pipelines/selection/stages/policy.py`)
Update `_select_top_n` to read `config.ranking.direction`:
```python
is_ascending = config.ranking.direction == "ascending"
sorted_candidates = sorted(candidates, key=_get_score, reverse=not is_ascending)
```

## 4. Documentation
Update `universe_selection_v3.md` and `workflow_manifests.md` to reflect the new schema capability.
