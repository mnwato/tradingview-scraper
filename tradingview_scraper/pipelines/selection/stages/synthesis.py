import logging

from tradingview_scraper.orchestration.registry import StageRegistry
from tradingview_scraper.pipelines.selection.base import BasePipelineStage, SelectionContext
from tradingview_scraper.utils.synthesis import StrategyAtom

logger = logging.getLogger("pipelines.selection.synthesis")


@StageRegistry.register(id="alpha.synthesis", name="Strategy Synthesis", description="Creates Strategy Atoms from winners", category="alpha")
class SynthesisStage(BasePipelineStage):
    """
    Stage 6: Strategy Synthesis.
    Converts recruited winners into Strategy Atoms and generates the composition map.
    Handles 'Synthetic Long Normalization' by flagging SHORT atoms.
    """

    @property
    def name(self) -> str:
        return "Synthesis"

    def execute(self, context: SelectionContext) -> SelectionContext:
        winners = context.winners
        if not winners:
            logger.warning("SynthesisStage: No winners to synthesize.")
            return context

        logger.info(f"Synthesizing {len(winners)} Strategy Atoms...")

        atoms = []
        comp_map = {}

        for w in winners:
            sym = str(w["symbol"])
            logic = str(w.get("logic", "momentum"))  # Default logic if not specified (v3 assumes momentum/trend)
            direction = str(w.get("direction", "LONG"))

            # Create Atom
            atom = StrategyAtom(asset=sym, logic=logic, direction=direction)
            atoms.append(atom)

            # Generate Composition Map (Atom ID -> {Asset: Weight})
            # Weight is 1.0 for LONG, -1.0 for SHORT (Synthetic Long Normalization)
            weight = 1.0 if direction == "LONG" else -1.0
            comp_map[atom.id] = {sym: weight}

        context.strategy_atoms = atoms
        context.composition_map = comp_map

        context.log_event(self.name, "SynthesisComplete", {"n_atoms": len(atoms), "n_shorts": len([a for a in atoms if a.direction == "SHORT"])})

        return context
