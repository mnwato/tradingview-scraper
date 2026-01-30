from __future__ import annotations

import hashlib
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def get_df_hash(df: pd.DataFrame | pd.Series) -> str:
    """
    Computes a stable, deterministic SHA-256 hash of a DataFrame or Series.
    Ignores memory addresses and non-essential metadata.
    Forces indices to naive UTC string representations for cross-environment parity.
    """
    if df.empty:
        return hashlib.sha256(b"empty").hexdigest()

    try:
        obj = df.copy()

        idx = obj.index
        if isinstance(idx, pd.DatetimeIndex) and idx.tz is not None:
            obj.index = idx.tz_convert(None)

        if isinstance(obj, pd.DataFrame):
            try:
                obj = obj.sort_index().sort_index(axis=1)
            except Exception:
                obj = obj.reindex(sorted(obj.index, key=str)).reindex(columns=sorted(obj.columns, key=str))
        else:
            try:
                obj = obj.sort_index()
            except Exception:
                obj = obj.reindex(sorted(obj.index, key=str))

        # 1. Standardize Index
        idx = obj.index
        if isinstance(idx, pd.DatetimeIndex):
            # Use ISO format for maximum string stability
            idx_list = idx.strftime("%Y-%m-%dT%H:%M:%S").tolist()
        else:
            idx_list = [str(x) for x in idx]

        idx_str = "|".join(idx_list)

        # 2. Standardize Columns (if DataFrame)
        cols_str = ""
        if isinstance(obj, pd.DataFrame):
            cols_str = "|".join([str(c) for c in obj.columns])

        # 3. Standardize Data
        # We use a high-precision rounded string representation for floats to avoid
        # float64 byte variations across different architectures/OS.
        # 8 decimals is enough for financial returns.
        data_flat = obj.to_numpy().flatten()
        data_list = []
        for x in data_flat:
            try:
                # If it looks like a number, format it specifically
                if pd.api.types.is_number(x) and not isinstance(x, bool):
                    # Use a very robust way to get a float string
                    try:
                        val = float(str(x))
                        data_list.append(f"{val:.8f}")
                    except (ValueError, TypeError):
                        data_list.append(str(x))
                else:
                    data_list.append(str(x))
            except Exception:
                data_list.append(str(x))
        data_str = "|".join(data_list)

        # 4. Final Fingerprint
        combined = f"idx:{idx_str};cols:{cols_str};data:{data_str}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()
    except Exception as e:
        logger.warning(f"Fallback hashing for object type {type(df)}: {e}")
        return hashlib.sha256(str(df.shape).encode()).hexdigest()


def get_env_hash() -> str:
    """Generates a hash of the current environment state (uv.lock, pyproject.toml)."""
    env_str = ""
    for filename in ["uv.lock", "pyproject.toml"]:
        p = Path(filename)
        if p.exists():
            env_str += p.read_text()

    # Add python version
    env_str += sys.version
    return hashlib.sha256(env_str.encode()).hexdigest()


class AuditLedger:
    """
    Append-only, cryptographically chained decision ledger.
    Implements the WAL (Write-Ahead Logging) principle.
    """

    def __init__(self, run_dir: Path):
        self.path = run_dir / "audit.jsonl"
        self.last_hash: Optional[str] = None
        self._initialize_chain()

    def _initialize_chain(self):
        """Discovers the last hash if the file already exists (for resumed runs)."""
        if not self.path.exists():
            return

        try:
            with open(self.path, "r") as f:
                lines = f.readlines()
                if lines:
                    last_line = json.loads(lines[-1])
                    self.last_hash = last_line.get("hash")
        except Exception as e:
            logger.error(f"Failed to recover audit chain: {e}")

    def _append(self, record: Dict[str, Any]):
        """Calculates hash, chains to previous, and appends to disk."""
        # Refresh last_hash from disk to support nested/concurrent processes
        self._initialize_chain()

        ts = datetime.now().isoformat()
        record["ts"] = ts
        record["prev_hash"] = self.last_hash or "0" * 64

        # Calculate signature of this record
        # We sort keys for determinism
        record_json = json.dumps(record, sort_keys=True)
        current_hash = hashlib.sha256(record_json.encode()).hexdigest()
        record["hash"] = current_hash

        with open(self.path, "a") as f:
            f.write(json.dumps(record) + "\n")

        self.last_hash = current_hash

    def record_genesis(self, run_id: str, profile: str, manifest_hash: str, config: Optional[Dict[str, Any]] = None):
        """Creates the Genesis Block for a new run."""
        git_hash = "unknown"
        try:
            import subprocess

            git_hash = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("ascii").strip()
        except Exception:
            pass

        record = {
            "type": "genesis",
            "run_id": run_id,
            "profile": profile,
            "env": {
                "python": sys.version,
                "manifest_hash": manifest_hash,
                "env_hash": get_env_hash(),
                "git_hash": git_hash,
            },
        }
        if config:
            record["config"] = config
        self._append(record)

    def record_intent(
        self,
        step: str,
        params: Dict[str, Any],
        input_hashes: Dict[str, str],
        data: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Logs an intent to perform a pipeline action."""
        record = {
            "type": "action",
            "status": "intent",
            "step": step,
            "intent": {
                "params": params,
                "input_hashes": input_hashes,
            },
        }
        if data:
            record["data"] = data
        if context:
            record["context"] = context
        self._append(record)

    def record_outcome(
        self,
        step: str,
        status: str,
        output_hashes: Dict[str, str],
        metrics: Dict[str, Any],
        data: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Logs the outcome of a pipeline action."""
        record = {
            "type": "action",
            "status": status,
            "step": step,
            "outcome": {
                "output_hashes": output_hashes,
                "metrics": metrics,
            },
        }
        if data:
            record["data"] = data
        if context:
            record["context"] = context
        self._append(record)
