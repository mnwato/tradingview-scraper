import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, cast

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StrategyAtom:
    """The fundamental unit of alpha."""

    asset: str
    logic: str
    direction: str = "LONG"
    timescale: str = "1d"
    params: Dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return f"{self.asset}_{self.logic}_{self.direction}_{self.timescale}"


def calculate_beta(asset_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """Calculates beta of asset vs benchmark using simple covariance."""
    # Ensure aligned data
    df = pd.concat([asset_returns, benchmark_returns], axis=1).dropna()
    if len(df) < 10:
        return 1.0

    cov_matrix = np.cov(df.iloc[:, 0].values, df.iloc[:, 1].values)
    if cov_matrix.shape != (2, 2):
        return 1.0
    cov = float(cov_matrix[0, 1])
    var = float(cov_matrix[1, 1])
    return float(cov / (var + 1e-12))


def generate_atom_returns(returns: pd.Series, atom: StrategyAtom) -> pd.Series:
    """
    Generates a return stream for a single StrategyAtom.
    Pillar 2: Strategy Synthesis.
    """
    logic = str(atom.logic).lower()
    window = int(atom.params.get("window", 20))

    # Ensure returns is a Series
    s_rets = pd.Series(returns)

    if logic == "momentum":
        # sign of trailing returns shifted to avoid bias
        def roll_prod(x):
            return np.prod(1 + x) - 1

        mom = s_rets.rolling(window=window).apply(roll_prod, raw=True)
        signal = np.sign(mom.shift(1).fillna(0.0).values)
        return s_rets * pd.Series(signal, index=s_rets.index)
    elif logic == "reversion":
        # anti-sign of distance to moving average
        prices = (1 + s_rets).cumprod()
        ma = prices.rolling(window=window).mean()
        signal = -np.sign((prices - ma).shift(1).fillna(0.0).values)
        return s_rets * pd.Series(signal, index=s_rets.index)
    elif logic == "trend":
        # binary trend based on moving average
        ma_rets = s_rets.rolling(window=window).mean()
        # signal is 1 if average return > 0 else 0
        sig_vals = (ma_rets.shift(1).fillna(-1.0).values > 0).astype(float)
        return s_rets * pd.Series(sig_vals, index=s_rets.index)
    else:
        # direct pass (raw asset return)
        return s_rets


class StrategySynthesizer:
    """
    Orchestrates the conversion of a selected universe into synthesized return streams.
    Handles Pillar 2 (Synthesis) of the 3-pillar architecture.
    """

    def __init__(self):
        # Metadata to track physical asset composition
        # Maps StrategyName -> {PhysicalSymbol: CompositionWeight}
        self.composition_map: Dict[str, Dict[str, float]] = {}

    def synthesize(self, returns_df: pd.DataFrame, winners_meta: List[Dict[str, Any]], features: Any) -> pd.DataFrame:
        """
        Synthesizes the strategy matrix from the selected universe.
        Each column in the output is a purified alpha stream (Synthetic Long).
        """
        synth_matrix = pd.DataFrame(index=returns_df.index)
        self.composition_map = {}

        for winner in winners_meta:
            sym = str(winner["symbol"])
            logic = str(winner.get("logic", "momentum"))
            direction = str(winner.get("direction", "LONG"))

            # 1. Create the Atom
            atom = StrategyAtom(asset=sym, logic=logic, direction=direction)
            atom_rets = generate_atom_returns(cast(pd.Series, returns_df[sym]), atom)

            # 2. Synthetic Long Normalization
            # If SHORT, we flip the return stream so 'alpha' is positive for the solver
            if direction == "SHORT":
                atom_rets = -1.0 * atom_rets

            strat_name = atom.id
            self.composition_map[strat_name] = {sym: 1.0 if direction == "LONG" else -1.0}

            synth_matrix[strat_name] = atom_rets

        return synth_matrix

    def flatten_weights(self, strategy_weights: pd.DataFrame) -> pd.DataFrame:
        """
        Execution Layer: Maps strategy weights back to physical assets.
        Expects a DataFrame with 'Symbol' and 'Weight' columns.
        """
        asset_weights: Dict[str, float] = {}

        for _, row in strategy_weights.iterrows():
            strat_name = str(row["Symbol"])
            weight = float(row["Weight"])

            if strat_name in self.composition_map:
                comp = self.composition_map[strat_name]
                for asset, factor in comp.items():
                    asset_weights[asset] = asset_weights.get(asset, 0.0) + (weight * factor)
            else:
                asset_weights[strat_name] = asset_weights.get(strat_name, 0.0) + weight

        flat_rows = [{"Symbol": k, "Weight": abs(v), "Net_Weight": v} for k, v in asset_weights.items()]
        if not flat_rows:
            return pd.DataFrame(columns=pd.Index(["Symbol", "Weight", "Net_Weight"]))

        return pd.DataFrame(flat_rows).sort_values("Weight", ascending=False)
